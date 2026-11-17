"""Herramientas de Luma.

REGLA DE ORO: el modelo solo PIDE acciones; este código decide si se permiten.
- No existe ninguna herramienta para borrar archivos ni para ejecutar comandos.
- Lectura: solo su espacio propio + carpetas que vos autorices (menú clic derecho).
- Escritura: libre en su espacio propio; en tus carpetas solo con tu confirmación
  (y guardando copia de seguridad del archivo anterior).
- Todo queda registrado en datos/actividad.log
"""
import html
import ipaddress
import logging
import re
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

from config import DATOS

act = logging.getLogger("luma.actividad")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Luma/1.0"
CARPETAS_IGNORADAS = {"node_modules", ".git", "__pycache__", ".venv", "venv", ".idea", ".vscode"}


def _es_sensible(p: Path):
    n = p.name.lower()
    partes = {x.lower() for x in p.parts}
    return (n.startswith(".env") or n in ("id_rsa", "id_ed25519", "known_hosts")
            or p.suffix.lower() in (".pem", ".key", ".kdbx", ".pfx", ".p12")
            or bool(partes & {".ssh", ".aws", ".gnupg"})
            or any(w in n for w in ("password", "contraseña", "credential", "secret")))


def _texto_plano(h):
    h = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


class Herramientas:
    def __init__(self, cfg, memoria):
        self.cfg = cfg
        self.mem = memoria
        self.espacio = (DATOS / "espacio_de_luma").resolve()
        (self.espacio / "notas").mkdir(parents=True, exist_ok=True)
        (self.espacio / "backups").mkdir(parents=True, exist_ok=True)
        self.confirmar = lambda texto: False   # lo reemplaza la interfaz
        self.tabla = {
            "buscar_web": self.buscar_web, "leer_pagina": self.leer_pagina,
            "leer_archivo": self.leer_archivo, "listar_carpeta": self.listar_carpeta,
            "escribir_nota": self.escribir_nota, "proponer_archivo": self.proponer_archivo,
            "recordar": self.recordar,
        }

    # ---------- descripción para el prompt ----------
    def descripcion(self):
        lectura = [str(Path(d)) for d in self.cfg["carpetas_lectura"]]
        escritura = [str(Path(d)) for d in self.cfg["carpetas_escritura"]]
        t = ("- [[buscar_web|consulta]] busca en internet\n"
             "- [[leer_pagina|url]] lee el texto de una página web\n"
             "- [[leer_archivo|ruta]] lee un archivo de texto/código\n"
             "- [[listar_carpeta|ruta]] lista el contenido de una carpeta\n"
             "- [[escribir_nota|nombre|contenido]] guarda una nota en tu espacio propio\n"
             "- [[proponer_archivo|ruta|contenido]] propone crear/modificar un archivo (el usuario debe aceptar)\n"
             "- [[recordar|dato]] guarda algo importante sobre el usuario en tu memoria\n")
        t += ("Carpetas que podés leer además de tu espacio: " + (", ".join(lectura) or "ninguna todavía") + "\n")
        t += ("Carpetas donde podés proponer archivos: " + (", ".join(escritura) or "ninguna todavía") + "\n")
        t += f"Tu espacio propio (rutas relativas caen acá): {self.espacio}"
        return t

    def describir_llamada(self, nombre, arg):
        arg = (arg or "").split("|")[0].strip()[:60]
        return {"buscar_web": "🔎 buscando en la web: ", "leer_pagina": "🌐 leyendo página: ",
                "leer_archivo": "📄 leyendo: ", "listar_carpeta": "📁 mirando carpeta: ",
                "escribir_nota": "📝 escribiendo nota: ", "proponer_archivo": "✍️ proponiendo archivo: ",
                "recordar": "🧠 anotando en mi memoria"}.get(nombre, "🔧 ") + (arg if nombre != "recordar" else "")

    # ---------- ejecución ----------
    def ejecutar(self, nombre, arg):
        f = self.tabla.get(nombre)
        if not f:
            return f"ERROR: la herramienta '{nombre}' no existe."
        act.info("HERRAMIENTA %s | %s", nombre, (arg or "")[:200].replace("\n", " "))
        try:
            return f(arg or "")
        except PermissionError as e:
            act.info("DENEGADO %s: %s", nombre, e)
            return f"DENEGADO: {e}"
        except Exception as e:
            act.info("FALLO %s: %s", nombre, e)
            return f"ERROR: {e}"

    # ---------- rutas seguras ----------
    def _resolver(self, ruta, escritura=False):
        ruta = ruta.strip().strip('"\'')
        if not ruta:
            raise PermissionError("falta la ruta")
        p = Path(ruta).expanduser()
        if not p.is_absolute():
            p = self.espacio / p
        p = p.resolve()
        if _es_sensible(p):
            raise PermissionError("ese archivo parece sensible (claves/contraseñas) y no lo toco.")
        lect = [Path(d).resolve() for d in self.cfg["carpetas_lectura"]]
        escr = [Path(d).resolve() for d in self.cfg["carpetas_escritura"]]
        raices = [self.espacio] + (escr if escritura else lect + escr)
        for r in raices:
            if p == r or r in p.parents:
                return p, (r != self.espacio)
        if escritura:
            raise PermissionError("no tengo permiso de escritura ahí. El usuario puede dármelo con clic derecho > permisos.")
        raise PermissionError("no tengo permiso de lectura ahí. El usuario puede dármelo con clic derecho > permisos.")

    def leer_archivo(self, ruta):
        p, _ = self._resolver(ruta)
        if not p.is_file():
            return "ERROR: no existe ese archivo."
        data = p.read_bytes()[:15000]
        if b"\0" in data:
            return "ERROR: parece un archivo binario."
        return data.decode("utf-8", errors="replace")

    def listar_carpeta(self, ruta):
        p, _ = self._resolver(ruta or str(self.espacio))
        if not p.is_dir():
            return "ERROR: no es una carpeta."
        items = []
        for x in sorted(p.iterdir(), key=lambda a: (a.is_file(), a.name.lower())):
            if x.name in CARPETAS_IGNORADAS or x.name.startswith("."):
                continue
            items.append(("📁 " if x.is_dir() else "📄 ") + x.name)
            if len(items) >= 80:
                items.append("… (hay más)")
                break
        return "\n".join(items) or "(vacía)"

    def escribir_nota(self, arg):
        nombre, _, contenido = arg.partition("|")
        nombre = re.sub(r"[^\w\-. ]", "_", nombre.strip())[:60] or "nota"
        if "." not in nombre:
            nombre += ".md"
        (self.espacio / "notas" / nombre).write_text(contenido.strip()[:50000], encoding="utf-8")
        return f"Nota guardada en notas/{nombre}"

    def proponer_archivo(self, arg):
        ruta, _, contenido = arg.partition("|")
        p, afuera = self._resolver(ruta, escritura=True)
        contenido = contenido.strip("\n")[:200000]
        if afuera:
            existe = p.exists()
            vista = contenido[:700] + ("…" if len(contenido) > 700 else "")
            texto = (f"{self.cfg['nombre']} quiere {'REEMPLAZAR' if existe else 'crear'} este archivo:\n\n{p}\n\n"
                     f"Contenido propuesto:\n{vista}\n\n¿Aceptás?" + ("\n(Se guardará copia del anterior.)" if existe else ""))
            if not self.confirmar(texto):
                act.info("RECHAZADO por el usuario: %s", p)
                return "El usuario NO aceptó el cambio."
            if existe:
                (self.espacio / "backups" / f"{time.strftime('%Y%m%d_%H%M%S')}_{p.name}").write_bytes(p.read_bytes())
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contenido, encoding="utf-8")
        act.info("ESCRIBIÓ %s", p)
        return f"Archivo guardado: {p}"

    def recordar(self, dato):
        return "Anotado." if self.mem.agregar_recuerdo(dato, "luma") else "Ya lo sabía (o era muy corto)."

    # ---------- web ----------
    def _get(self, url, max_bytes=400000):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es,en;q=0.8"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read(max_bytes).decode("utf-8", errors="replace")

    def buscar_web(self, consulta):
        pagina = self._get("https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": consulta.strip()}))
        out = []
        for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>(.*?)(?=class="result__a"|$)', pagina, re.S):
            href, titulo, resto = m.groups()
            if "uddg=" in href:
                href = urllib.parse.parse_qs(urllib.parse.urlparse("https:" + href if href.startswith("//") else href).query).get("uddg", [href])[0]
            sn = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', resto, re.S)
            out.append(f"{len(out) + 1}. {_texto_plano(titulo)} — {_texto_plano(sn.group(1)) if sn else ''} ({href})")
            if len(out) >= 5:
                break
        return "\n".join(out) or "No encontré resultados (o el buscador no respondió)."

    def leer_pagina(self, url):
        url = url.strip()
        u = urllib.parse.urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            raise PermissionError("solo URLs http/https.")
        ip = ipaddress.ip_address(socket.gethostbyname(u.hostname))
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise PermissionError("no entro a direcciones de la red local.")
        return _texto_plano(self._get(url))[:5000] or "(página vacía)"
