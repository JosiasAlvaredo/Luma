"""Interfaz de Luma: la criaturita en pantalla, su burbuja de diálogo y la ventana de charla."""
import html
import json
import logging
import math
import os
import random
import threading
import time
import urllib.request

from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QFontMetrics, QGuiApplication, QIcon, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QMenu, QMessageBox, QPushButton, QSystemTrayIcon, QTextBrowser, QVBoxLayout, QWidget)

import sistema
import sprites
from config import BASE, DATOS
from llm import LLMError

log = logging.getLogger("luma")
act = logging.getLogger("luma.actividad")

EMO_ESTADO = {"alegre": "happy", "emocionada": "happy", "triste": "sad",
              "pensando": "think", "timida": "shy", "sueno": "sit"}
FLAGS_FLOTANTE = (Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint |
                  Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)


class Puente(QObject):
    """Señales para pasar resultados de hilos de trabajo a la interfaz."""
    texto = Signal(str)
    evento = Signal(str)
    terminado = Signal(str, str)
    error = Signal(str)
    espontaneo = Signal(str, str, str)
    confirmar = Signal(str, object)
    aviso = Signal(str)


# ======================================================================
class Burbuja(QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__(None, FLAGS_FLOTANTE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fuente = QFont("Segoe UI", 10)
        self.texto, self.abajo, self.caja = "", False, QRect(0, 0, 10, 10)
        self.reloj = QTimer(self)
        self.reloj.setSingleShot(True)
        self.reloj.timeout.connect(self.hide)

    def mostrar(self, texto, segs=None):
        self.texto = texto
        r = QFontMetrics(self.fuente).boundingRect(QRect(0, 0, 250, 3000), Qt.TextFlag.TextWordWrap, texto)
        self.caja = QRect(0, 0, r.width() + 26, r.height() + 18)
        self.resize(self.caja.width() + 2, self.caja.height() + 14)
        self.reloj.start(int(1000 * (segs or min(20, 3 + len(texto) * 0.06))))
        self.show()
        self.update()

    def colocar(self, pet, pantalla):
        x = min(max(pet.center().x() - self.width() // 2, pantalla.left() + 4), pantalla.right() - self.width() - 4)
        y = pet.top() + 14 - self.height()
        abajo = y < pantalla.top()
        if abajo:
            y = pet.bottom() - 10
        if abajo != self.abajo:
            self.abajo = abajo
            self.update()
        self.move(x, y)
        self._cx = pet.center().x() - x

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        oy = 12 if self.abajo else 0
        cuerpo = QRect(1, 1 + oy, self.caja.width(), self.caja.height())
        p.setPen(QPen(QColor(90, 70, 130), 2))
        p.setBrush(QColor(252, 250, 255))
        p.drawRoundedRect(cuerpo, 12, 12)
        cx = min(max(getattr(self, "_cx", cuerpo.width() // 2), 24), cuerpo.width() - 24)
        if self.abajo:
            tri = [QPoint(cx - 7, oy + 1), QPoint(cx + 7, oy + 1), QPoint(cx, 1)]
        else:
            tri = [QPoint(cx - 7, cuerpo.bottom()), QPoint(cx + 7, cuerpo.bottom()), QPoint(cx, cuerpo.bottom() + 11)]
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(tri)
        p.setPen(QColor(50, 40, 80))
        p.setFont(self.fuente)
        p.drawText(cuerpo.adjusted(13, 9, -13, -9), Qt.TextFlag.TextWordWrap, self.texto)

    def mousePressEvent(self, _):
        self.hide()
        self.clicked.emit()


# ======================================================================
def formatear(texto):
    partes, out = texto.split("```"), []
    for i, pt in enumerate(partes):
        if i % 2:
            primera, _, resto = pt.partition("\n")
            if resto and len(primera.strip()) < 15 and " " not in primera.strip():
                pt = resto
            out.append("<pre style='background:#2b2540;color:#eee;padding:6px;'>" + html.escape(pt.strip("\n")) + "</pre>")
        else:
            out.append(html.escape(pt).replace("\n", "<br>"))
    return "".join(out)


class VentanaChat(QWidget):
    enviar = Signal(str)

    def __init__(self, nombre):
        super().__init__()
        self.nombre, self.items, self.stream = nombre, [], None
        self.setWindowTitle(f"Charla con {nombre}")
        self.resize(440, 560)
        self.setStyleSheet("QWidget{background:#1f1b2e;color:#eee;font-size:13px;}"
                           "QTextBrowser{background:#272238;border:1px solid #3a3358;border-radius:8px;padding:6px;}"
                           "QLineEdit{background:#2d2745;border:1px solid #4a4175;border-radius:8px;padding:7px;}"
                           "QPushButton{background:#7b5cff;border:none;border-radius:8px;padding:7px 14px;color:white;}"
                           "QPushButton:disabled{background:#4a4175;}")
        self.vista = QTextBrowser()
        self.vista.setOpenExternalLinks(True)
        self.estado = QLabel("")
        self.estado.setStyleSheet("color:#a99be0;font-style:italic;")
        self.entrada = QLineEdit()
        self.entrada.setPlaceholderText("Escribile algo…")
        self.boton = QPushButton("Enviar")
        fila = QHBoxLayout()
        fila.addWidget(self.entrada)
        fila.addWidget(self.boton)
        col = QVBoxLayout(self)
        col.addWidget(self.vista)
        col.addWidget(self.estado)
        col.addLayout(fila)
        self.entrada.returnPressed.connect(self._enviar)
        self.boton.clicked.connect(self._enviar)

    def _enviar(self):
        t = self.entrada.text().strip()
        if t and self.boton.isEnabled():
            self.entrada.clear()
            self.agregar("tu", t)
            self.enviar.emit(t)

    def cargar(self, mensajes):
        self.items = [("tu" if m["role"] == "user" else "luma", m["content"]) for m in mensajes]
        self.dibujar()

    def agregar(self, quien, texto):
        self.items.append((quien, texto))
        self.dibujar()

    def comenzar(self):
        self.stream = ""
        self.boton.setEnabled(False)
        self.estado.setText(f"{self.nombre} está pensando…")
        self.dibujar()

    def parcial(self, texto):
        self.stream = texto
        self.dibujar()

    def evento(self, texto):
        self.estado.setText(texto)

    def terminar(self, texto=None):
        if texto:
            self.items.append(("luma", texto))
        self.stream = None
        self.boton.setEnabled(True)
        self.estado.setText("")
        self.dibujar()
        self.entrada.setFocus()

    def dibujar(self):
        filas = [(q, t) for q, t in self.items] + ([("luma", self.stream)] if self.stream else [])
        h = ""
        for q, t in filas:
            nombre, color = ("Vos", "#8fd3ff") if q == "tu" else (self.nombre, "#c7b3ff")
            h += f"<p><b style='color:{color}'>{nombre}:</b> {formatear(t)}</p>"
        self.vista.setHtml(h)
        self.vista.verticalScrollBar().setValue(self.vista.verticalScrollBar().maximum())

    def closeEvent(self, e):
        e.ignore()
        self.hide()


class DialogoMemoria(QDialog):
    def __init__(self, memoria, nombre):
        super().__init__()
        self.mem = memoria
        self.setWindowTitle(f"Lo que {nombre} recuerda de vos")
        self.resize(480, 360)
        self.lista = QListWidget()
        self.lista.setWordWrap(True)
        b = QPushButton("Que olvide el recuerdo seleccionado")
        b.clicked.connect(self.olvidar)
        lay = QVBoxLayout(self)
        lay.addWidget(self.lista)
        lay.addWidget(b)
        self.recargar()

    def recargar(self):
        self.lista.clear()
        self.ids = []
        for id_, t in self.mem.recuerdos():
            self.lista.addItem(t)
            self.ids.append(id_)
        if not self.ids:
            self.lista.addItem("(todavía no recuerda nada: charlen un rato)")

    def olvidar(self):
        i = self.lista.currentRow()
        if 0 <= i < len(self.ids):
            self.mem.olvidar(self.ids[i])
            self.recargar()


# ======================================================================
class Mascota(QWidget):
    def __init__(self, cfg, vida, agente, memoria, herramientas, llm):
        super().__init__(None, FLAGS_FLOTANTE)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.cfg, self.vida, self.agente, self.mem, self.tools, self.llm = cfg, vida, agente, memoria, herramientas, llm
        self.escala = int(cfg["escala_sprite"])
        self.resize(sprites.SIZE * self.escala, sprites.SIZE * self.escala)

        self.puente = Puente()
        self.puente.texto.connect(self._on_texto)
        self.puente.evento.connect(lambda t: self.chat.evento(t))
        self.puente.terminado.connect(self._on_terminado)
        self.puente.error.connect(self._on_error)
        self.puente.espontaneo.connect(self._on_espontaneo)
        self.puente.confirmar.connect(self._mostrar_confirmacion)
        self.puente.aviso.connect(lambda t: self.decir(t, "triste", 14))
        self.tools.confirmar = self._pedir_confirmacion

        self.burbuja = Burbuja()
        self.burbuja.clicked.connect(self.abrir_chat)
        self.chat = VentanaChat(cfg["nombre"])
        self.chat.cargar(self.mem.recientes(30))
        self.chat.enviar.connect(self.enviar_chat)

        # estado del cuerpo
        pant = QGuiApplication.primaryScreen().availableGeometry()
        self.pos_x = pant.center().x() - self.width() / 2
        self.pos_y = float(pant.top())
        self.vy, self.facing = 0.0, 1
        self.modo, self.modo_hasta, self.target_x, self.luego = "idle", 0.0, None, None
        self.emote, self.emote_hasta, self.habla_hasta = "idle", 0.0, 0.0
        self.arrastrando, self.ocupada = False, False
        self.prox_salto, self.clave, self.pm = 0.0, None, None
        self.t_prev = time.time()
        self.inactivo, self.t_inactivo = 0.0, 0.0
        # iniciativa propia
        self.prox_espontaneo = time.time() + 3 * 60
        self.llm_pausa, self.ultimo_titulo, self.turnos, self.prox_chequeo = 0.0, "", 0, 0.0

        self._crear_tray()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)
        self.show()
        QTimer.singleShot(2500, self.saludar)
        threading.Thread(target=self._chequear_ollama, daemon=True).start()

    # ---------------------------------------------------------------- utilidades
    def pantalla(self):
        c = QPoint(int(self.pos_x + self.width() / 2), int(self.pos_y + self.height() / 2))
        return (QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()).availableGeometry()

    def decir(self, texto, emocion=None, segs=None):
        self.habla_hasta = max(self.habla_hasta, time.time() + min(4, len(texto) * 0.04))
        if emocion:
            self.emocionar(emocion)
        if not self.chat.isVisible():
            self.burbuja.mostrar(texto, segs)

    def emocionar(self, emocion, segs=3.0):
        est = EMO_ESTADO.get(emocion)
        if est:
            self.emote, self.emote_hasta = est, time.time() + segs
            if est == "happy" and self.vy == 0:
                self.vy = -420

    def saludar(self):
        h = time.localtime().tm_hour
        s = "¡Buen día" if 5 <= h < 13 else "¡Buenas tardes" if h < 20 else "¡Buenas noches"
        self.decir(f"{s}! Ya estoy por acá. Doble clic en mí y charlamos.", "alegre", 7)

    def _chequear_ollama(self):
        try:
            with urllib.request.urlopen(self.cfg["ollama_url"].rstrip("/") + "/api/tags", timeout=4) as r:
                nombres = [m["name"] for m in json.loads(r.read()).get("models", [])]
            base = self.cfg["modelo"].split(":")[0]
            if not any(n.split(":")[0] == base for n in nombres):
                self.puente.aviso.emit(f"Todavía no tengo cerebro: falta bajar el modelo. Corré en una terminal: ollama pull {self.cfg['modelo']}")
        except Exception:
            self.puente.aviso.emit("No encuentro Ollama (mi cerebro). Abrí la app de Ollama y reiniciame. Mientras tanto puedo pasear igual 🙂")

    # ---------------------------------------------------------------- bucle principal
    def tick(self):
        ahora = time.time()
        dt = min(ahora - self.t_prev, 0.1)
        self.t_prev = ahora
        self.vida.tick(dt)
        if ahora - self.t_inactivo > 1:
            self.inactivo, self.t_inactivo = sistema.segundos_inactivo(), ahora
        ausente = self.inactivo > self.cfg["minutos_para_dormir_ausente"] * 60
        sc = self.pantalla()

        if not self.arrastrando and ahora >= self.modo_hasta:
            self.siguiente_accion(ahora, ausente, sc)
        estado = self.estado_visual(ahora)

        if not self.arrastrando:
            suelo = sc.bottom() + 1 - self.height()
            if estado == "walk" and self.target_x is not None:
                d, paso = self.target_x - self.pos_x, self.cfg["velocidad"] * dt
                if abs(d) <= paso:
                    self.pos_x, self.target_x = self.target_x, None
                    if self.luego == "curious":
                        self.modo, self.modo_hasta = "curious", ahora + random.uniform(4, 7)
                    else:
                        self.modo, self.modo_hasta = "idle", ahora + random.uniform(1, 3)
                    self.luego = None
                else:
                    self.pos_x += paso if d > 0 else -paso
                    self.facing = 1 if d > 0 else -1
            if estado == "play" and self.pos_y >= suelo - 0.5 and self.vy == 0 and ahora >= self.prox_salto:
                self.vy, self.prox_salto = -620.0, ahora + 0.6
            if self.pos_y < suelo - 0.5 or self.vy < 0:
                self.vy += 2200 * dt
                self.pos_y += self.vy * dt
                if self.pos_y >= suelo:
                    self.pos_y, self.vy = float(suelo), 0.0
            else:
                self.pos_y = float(suelo)
            self.pos_x = min(max(self.pos_x, sc.left()), sc.right() + 1 - self.width())

        # mirada hacia el cursor
        cur = QCursor.pos()
        dx = cur.x() - (self.pos_x + self.width() / 2)
        dy = cur.y() - (self.pos_y + self.height() * 0.4)
        mira, arriba = 0, False
        if estado not in ("sleep", "drag") and math.hypot(dx, dy) < 700:
            mira = 0 if abs(dx) < 60 else (1 if dx > 0 else -1)
            arriba = dy < -140
        if estado == "curious":
            self.facing = 1 if dx >= 0 else -1

        pose = sprites.make_pose(estado, ahora, mira * self.facing, arriba, ahora < self.habla_hasta)
        clave = (tuple(pose.values()), self.facing)
        if clave != self.clave:
            self.clave, self.pm = clave, sprites.pixmap(pose, self.facing, self.escala)
            self.update()
        nx, ny = int(self.pos_x), int(self.pos_y)
        if (nx, ny) != (self.x(), self.y()):
            self.move(nx, ny)
        if self.burbuja.isVisible():
            self.burbuja.colocar(QRect(nx, ny, self.width(), self.height()), sc)
        if ahora >= self.prox_chequeo:
            self.prox_chequeo = ahora + 3
            self.quizas_espontaneo(ahora, ausente)

    def estado_visual(self, ahora):
        if self.arrastrando:
            return "drag"
        if ahora < self.emote_hasta:
            return self.emote
        if self.ocupada:
            return "idle" if ahora < self.habla_hasta else "think"
        return self.modo

    def siguiente_accion(self, ahora, ausente, sc):
        cur = QCursor.pos()
        en_pantalla = sc.contains(cur)
        a = self.vida.decidir(ahora, dict(away=ausente, cursor_x=cur.x() if en_pantalla else None,
                                          min_x=sc.left() + 10, max_x=sc.right() - self.width() - 10, ancho=self.width()))
        self.modo, self.modo_hasta = a["estado"], ahora + a["dur"]
        self.target_x, self.luego = a.get("target_x"), a.get("luego")
        if a.get("decir"):
            self.decir(a["decir"])

    def paintEvent(self, _):
        if self.pm:
            p = QPainter(self)
            p.drawPixmap(0, 0, self.pm)

    # ---------------------------------------------------------------- mouse
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.press = e.globalPosition().toPoint()
            self.off = self.press - QPoint(int(self.pos_x), int(self.pos_y))

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            g = e.globalPosition().toPoint()
            if not self.arrastrando and (g - self.press).manhattanLength() > 6:
                self.arrastrando, self.vy, self.target_x = True, 0.0, None
            if self.arrastrando:
                self.pos_x, self.pos_y = g.x() - self.off.x(), g.y() - self.off.y()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.arrastrando:
                self.arrastrando, self.modo, self.modo_hasta = False, "idle", time.time() + 1.5
                self.vida.interactuar("caricia")
            else:
                self.acariciar()

    def mouseDoubleClickEvent(self, e):
        self.abrir_chat()

    def acariciar(self):
        ahora = time.time()
        dormida = self.vida.durmiendo
        self.vida.interactuar("caricia")
        if dormida:
            self.modo_hasta = 0
            return
        self.emocionar("alegre", 2.2)
        self.decir(self.vida.frase("caricia", ahora))

    # ---------------------------------------------------------------- menú
    def contextMenuEvent(self, e):
        n = self.cfg["nombre"]
        m = QMenu()
        m.addAction(f"💬 Hablar con {n}", self.abrir_chat)
        m.addAction("😴 Mandarla a dormir", self._dormir)
        silencio = QAction("🤫 Modo silencio (no habla sola)", m, checkable=True, checked=self.cfg["silencio"])
        silencio.toggled.connect(self._silencio)
        m.addAction(silencio)
        m.addSeparator()
        m.addAction("📂 Permitir que lea una carpeta…", lambda: self._permiso("carpetas_lectura", "lectura"))
        m.addAction("✍️ Permitir que proponga archivos en una carpeta…", lambda: self._permiso("carpetas_escritura", "escritura"))
        m.addAction("🧠 Ver / borrar lo que recuerda", lambda: DialogoMemoria(self.mem, n).exec())
        m.addAction("📝 Editar su personalidad", lambda: self._abrir(BASE / "personalidad.md"))
        m.addAction("📜 Ver registro de actividad", lambda: self._abrir(DATOS / "actividad.log"))
        m.addSeparator()
        m.addAction("❌ Salir", QApplication.instance().quit)
        m.exec(e.globalPos())

    def _abrir(self, ruta):
        try:
            os.startfile(str(ruta))
        except Exception:
            self.decir(f"Abrilo vos a mano: {ruta}")

    def _dormir(self):
        self.vida.durmiendo, self.vida.motivo_sueno, self.vida.energia = True, "cansada", min(self.vida.energia, 40)
        self.modo, self.modo_hasta = "sleep", time.time() + 4
        self.decir(self.vida.frase("dormir", time.time()))

    def _silencio(self, v):
        self.cfg["silencio"] = v
        self.cfg.guardar()
        self.decir("Ok, me quedo calladita." if v else "¡Vuelvo a hablar sola!")

    def _permiso(self, clave, tipo):
        d = QFileDialog.getExistingDirectory(None, f"Carpeta con permiso de {tipo} para {self.cfg['nombre']}")
        if not d:
            return
        aviso = ("Podrá LEER (nunca modificar ni borrar) archivos de:\n\n" if tipo == "lectura" else
                 "Podrá PROPONER crear/modificar archivos en:\n\n") + d + \
                ("\n\nSe le seguirán negando archivos sensibles (.env, claves, contraseñas)." if tipo == "lectura" else
                 "\n\nCada cambio te pedirá confirmación y se guarda copia del archivo anterior.")
        if QMessageBox.question(None, "Confirmar permiso", aviso) == QMessageBox.StandardButton.Yes:
            self.cfg[clave].append(d)
            self.cfg.guardar()
            act.info("PERMISO %s concedido: %s", tipo, d)
            self.decir(f"¡Gracias! Ya puedo {'mirar' if tipo == 'lectura' else 'proponerte archivos en'} esa carpeta.", "alegre")

    def _crear_tray(self):
        icono = QIcon(sprites.pixmap(sprites.make_pose("idle", 0), 1, 2))
        self.tray = QSystemTrayIcon(icono, self)
        self.menu_tray = QMenu()
        self.menu_tray.addAction(f"💬 Hablar con {self.cfg['nombre']}", self.abrir_chat)
        self.menu_tray.addAction("👀 Mostrar / ocultar", lambda: self.setVisible(not self.isVisible()))
        self.menu_tray.addAction("❌ Salir", QApplication.instance().quit)
        self.tray.setContextMenu(self.menu_tray)
        self.tray.setToolTip(self.cfg["nombre"])
        self.tray.show()

    # ---------------------------------------------------------------- charla
    def abrir_chat(self):
        self.burbuja.hide()
        self.chat.show()
        self.chat.raise_()
        self.chat.activateWindow()
        self.chat.entrada.setFocus()

    def enviar_chat(self, texto):
        self.vida.interactuar("charla")
        self.ocupada = True
        self.chat.comenzar()
        threading.Thread(target=self._trabajo_chat, args=(texto,), daemon=True).start()

    def _trabajo_chat(self, texto):
        try:
            final, emo = self.agente.responder(texto, self.puente.texto.emit, self.puente.evento.emit)
            self.puente.terminado.emit(final, emo)
        except LLMError as e:
            self.puente.error.emit(str(e))
        except Exception as e:
            log.exception("Fallo en la charla")
            self.puente.error.emit(f"Uy, algo salió mal: {e}")

    def _on_texto(self, texto):
        self.habla_hasta = time.time() + 0.5
        self.chat.parcial(texto)

    def _on_terminado(self, texto, emo):
        self.ocupada = False
        self.chat.terminar(texto)
        self.emocionar(emo, 3.5)
        if not self.chat.isVisible():
            self.decir(texto if len(texto) < 400 else texto[:400] + "…")
        self.turnos += 1
        if self.turnos % 6 == 0:
            threading.Thread(target=self._extraer, daemon=True).start()

    def _extraer(self):
        try:
            self.agente.extraer_recuerdos()
        except Exception as e:
            log.info("No pude extraer recuerdos: %s", e)

    def _on_error(self, texto):
        self.ocupada = False
        self.chat.terminar(texto)
        self.emocionar("triste", 4)

    # ---------------------------------------------------------------- iniciativa propia
    def quizas_espontaneo(self, ahora, ausente):
        if (self.cfg["silencio"] or ahora < self.prox_espontaneo or ausente or self.chat.isVisible()
                or self.ocupada or self.vida.durmiendo or ahora < self.llm_pausa):
            return
        titulo = sistema.titulo_ventana_activa() if self.cfg["curiosear_ventanas"] else ""
        if self.cfg["nombre"].lower() in titulo.lower() or "charla con" in titulo.lower():
            titulo = ""
        opciones = [("comentario", 3), ("pregunta", 2)]
        if titulo and titulo != self.ultimo_titulo:
            opciones.append(("ventana", 5))
        tipo = random.choices([o for o, _ in opciones], [w for _, w in opciones])[0]
        if tipo == "ventana":
            self.ultimo_titulo = titulo
        self.prox_espontaneo = ahora + self.cfg["minutos_entre_comentarios"] * 60 * random.uniform(0.8, 1.4)
        threading.Thread(target=self._trabajo_espontaneo, args=(tipo, titulo), daemon=True).start()

    def _trabajo_espontaneo(self, tipo, info):
        try:
            r = self.agente.espontaneo(tipo, info)
            if r:
                self.puente.espontaneo.emit(tipo, r[0], r[1])
        except LLMError as e:
            log.info("Sin cerebro por ahora: %s", e)
            self.llm_pausa = time.time() + 600
        except Exception:
            log.exception("Fallo en comentario espontáneo")

    def _on_espontaneo(self, tipo, texto, emo):
        act.info("ESPONTÁNEO (%s): %s", tipo, texto)
        self.chat.agregar("luma", texto)
        self.decir(texto, emo, min(25, 6 + len(texto) * 0.07))
        self.vida.aburrimiento = max(0, self.vida.aburrimiento - 30)

    # ---------------------------------------------------------------- confirmaciones
    def _pedir_confirmacion(self, texto):
        """Llamada desde un hilo de trabajo: espera a que el usuario acepte o rechace."""
        evento, res = threading.Event(), {"ok": False}
        self.puente.confirmar.emit(texto, (evento, res))
        evento.wait(180)
        return res["ok"]

    def _mostrar_confirmacion(self, texto, caja):
        evento, res = caja
        m = QMessageBox(QMessageBox.Icon.Question, f"{self.cfg['nombre']} pide permiso", texto,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        m.setDefaultButton(QMessageBox.StandardButton.No)
        m.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        res["ok"] = m.exec() == QMessageBox.StandardButton.Yes
        evento.set()
