"""Luma — compañera virtual de escritorio. Ejecutá:  python main.py"""
import logging
import sys

from PySide6.QtWidgets import QApplication

from agente import Agente
from config import DATOS, Config
from herramientas import Herramientas
from interfaz import Mascota
from llm import Ollama
from memoria import Memoria
from vida import Vida


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # Registro de TODO lo que hace con herramientas/permisos (podés leerlo cuando quieras)
    h = logging.FileHandler(DATOS / "actividad.log", encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s  %(message)s"))
    logging.getLogger("luma.actividad").addHandler(h)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    cfg = Config()
    llm = Ollama(cfg)
    memoria = Memoria(DATOS / "memoria.db", llm)
    herramientas = Herramientas(cfg, memoria)
    vida = Vida()
    agente = Agente(cfg, llm, memoria, herramientas, vida.estado_texto)
    ventana = Mascota(cfg, vida, agente, memoria, herramientas, llm)  # noqa: F841 (se mantiene viva)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
