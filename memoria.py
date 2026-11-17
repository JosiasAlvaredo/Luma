"""Memoria de Luma en SQLite: historial de charla + recuerdos duraderos (con búsqueda semántica)."""
import json
import logging
import math
import re
import sqlite3
import threading
import time

log = logging.getLogger("luma")


def _coseno(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def _palabras(t):
    return set(re.findall(r"\w{4,}", t.lower()))


class Memoria:
    def __init__(self, ruta, llm):
        self.db = sqlite3.connect(ruta, check_same_thread=False)
        self.lock = threading.Lock()
        self.llm = llm
        self._sin_embed_hasta = 0.0
        with self.lock:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS mensajes(id INTEGER PRIMARY KEY, ts REAL, rol TEXT, texto TEXT);
                CREATE TABLE IF NOT EXISTS recuerdos(id INTEGER PRIMARY KEY, ts REAL, texto TEXT, fuente TEXT, emb TEXT);
            """)

    # --- historial ---
    def agregar_mensaje(self, rol, texto):
        with self.lock:
            self.db.execute("INSERT INTO mensajes(ts,rol,texto) VALUES(?,?,?)", (time.time(), rol, texto))
            self.db.commit()

    def recientes(self, n=12):
        with self.lock:
            filas = self.db.execute("SELECT rol,texto FROM mensajes ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [{"role": r, "content": t} for r, t in reversed(filas)]

    # --- recuerdos ---
    def _embed(self, texto):
        if time.time() < self._sin_embed_hasta:
            return None
        try:
            return self.llm.embed(texto)
        except Exception as e:
            log.info("Sin embeddings (%s). Uso búsqueda por palabras.", e)
            self._sin_embed_hasta = time.time() + 600
            return None

    def agregar_recuerdo(self, texto, fuente="luma"):
        texto = texto.strip()
        if len(texto) < 4:
            return False
        with self.lock:
            existentes = [t.lower() for (t,) in self.db.execute("SELECT texto FROM recuerdos")]
        if texto.lower() in existentes:
            return False
        emb = self._embed(texto)
        with self.lock:
            self.db.execute("INSERT INTO recuerdos(ts,texto,fuente,emb) VALUES(?,?,?,?)",
                            (time.time(), texto, fuente, json.dumps(emb) if emb else None))
            self.db.commit()
        return True

    def recuerdos(self):
        with self.lock:
            return self.db.execute("SELECT id,texto FROM recuerdos ORDER BY id DESC").fetchall()

    def olvidar(self, id_):
        with self.lock:
            self.db.execute("DELETE FROM recuerdos WHERE id=?", (id_,))
            self.db.commit()

    def buscar(self, consulta, k=4):
        with self.lock:
            filas = self.db.execute("SELECT id,texto,emb FROM recuerdos ORDER BY id DESC").fetchall()
        if not filas:
            return []
        q = self._embed(consulta) if consulta else None
        puntajes = []
        if q:
            for _, t, e in filas:
                puntajes.append((_coseno(q, json.loads(e)) if e else 0.0, t))
            umbral = 0.35
        else:
            pq = _palabras(consulta or "")
            for _, t, _e in filas:
                puntajes.append((len(pq & _palabras(t)), t))
            umbral = 1
        puntajes.sort(key=lambda x: -x[0])
        elegidos = [t for s, t in puntajes[:k] if s >= umbral]
        return elegidos or [t for _, t, _e in filas[:2]]
