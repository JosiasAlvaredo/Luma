"""Configuración de Luma. Se guarda en config.json (podés editarlo a mano)."""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATOS = BASE / "datos"
DATOS.mkdir(exist_ok=True)
RUTA_CONFIG = BASE / "config.json"

DEFAULTS = {
    "nombre": "Luma",
    "usuario": "",                      # tu nombre (opcional; si no, lo va aprendiendo)
    "modelo": "qwen2.5:7b",             # modelo de charla (Ollama)
    "modelo_codigo": "",                # opcional: modelo para tareas de código, ej "qwen2.5-coder:14b"
    "modelo_embeddings": "nomic-embed-text",
    "ollama_url": "http://localhost:11434",
    "contexto_tokens": 4096,
    "escala_sprite": 5,                 # tamaño del dibujo (4 = chico, 6 = grande)
    "velocidad": 70,                    # píxeles por segundo al caminar
    "silencio": False,                  # True = no habla sola (solo responde si le hablás)
    "minutos_entre_comentarios": 12,    # cada cuánto puede iniciar charla con el modelo
    "curiosear_ventanas": True,         # puede ver el TÍTULO de la ventana activa para comentar
    "minutos_para_dormir_ausente": 10,  # si no tocás la PC, se duerme
    "carpetas_lectura": [],             # carpetas que puede LEER (se agregan desde el menú)
    "carpetas_escritura": [],           # carpetas donde puede PROPONER archivos (pide confirmación)
}


class Config(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        if RUTA_CONFIG.exists():
            try:
                self.update(json.loads(RUTA_CONFIG.read_text(encoding="utf-8")))
            except Exception:
                pass
        self.guardar()

    def guardar(self):
        RUTA_CONFIG.write_text(json.dumps(dict(self), indent=2, ensure_ascii=False), encoding="utf-8")
