# 🌙 Luma — tu compañera virtual de escritorio

Una criaturita de pixel art que vive en tu pantalla: camina por la barra de tareas, duerme, juega, te mira el cursor,
se aburre, te pregunta cosas y, cuando se lo pedís, te ayuda con programación y búsquedas.
**Todo corre en tu PC con Ollama: sin APIs, sin gastar plata.**

## Instalación (Windows)

1. **Python 3.10+** → https://www.python.org/downloads/ (tildá "Add python.exe to PATH").
2. **Ollama** → https://ollama.com  y en una terminal bajá los modelos:
   ```
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```
3. Doble clic en **`iniciar.bat`** (la primera vez instala PySide6 solo). Si algo falla, usá `iniciar_con_consola.bat` para ver el error.

## Cómo se usa

| Acción | Qué pasa |
|---|---|
| **Clic** | Le hacés cariño |
| **Doble clic** | Abre el chat |
| **Arrastrarla** | La agarrás y la tirás donde quieras (cae con gravedad) |
| **Clic derecho** | Menú: dormir, silencio, permisos, memoria, personalidad, log |
| **Clic en su burbuja** | Abre el chat para contestarle |
| **Ícono junto al reloj** | Mostrar/ocultar y salir |

## Cómo "tiene vida" sin gastar procesamiento
Sus movimientos y estados (energía, aburrimiento, curiosidad, ánimo) los decide código simple (`vida.py`), **no el modelo**.
El modelo solo se usa cuando charlan o, cada ~12 min, para que ella inicie algo (un comentario, una pregunta, o curiosear
el título de la ventana que tenés abierta).  Si no querés que hable sola: clic derecho → *Modo silencio*.

## Sus libertades (limitadas a propósito)
- **No existe ninguna herramienta para borrar archivos ni para ejecutar comandos.**
- Lee solo su espacio propio (`datos/espacio_de_luma`) y las carpetas que vos le habilites desde el menú.
- Nunca lee archivos sensibles (`.env`, claves SSH, `*.pem`, nombres con "password"/"secret"…).
- Para escribir en tus carpetas necesitás darle permiso **y** aceptar cada cambio en una ventanita (guarda backup del archivo anterior).
- Solo ve el *título* de tu ventana activa (no el contenido) y solo para comentar; se apaga con `"curiosear_ventanas": false`.
- Todo lo que hace queda en `datos/actividad.log`.
- El modelo solo *pide* acciones; el código (`herramientas.py`) decide si se permiten.

## Personalizarla
- **Personalidad:** editá `personalidad.md` (clic derecho → *Editar su personalidad*). Se aplica en el siguiente mensaje.
- **Ajustes:** `config.json` (nombre, tu nombre, modelo, tamaño del sprite, velocidad, frecuencia de comentarios…).
- **Modelo:** con GPU podés probar `gemma3:12b` o `qwen2.5:14b` para charla, y poner en `modelo_codigo` algo como
  `qwen2.5-coder:14b`: lo usa solo cuando le pedís código.
- **Aspecto:** `sprites.py` dibuja todo por código (colores en el diccionario `C`, arriba de todo).

## Archivos
`main.py` arranque · `interfaz.py` ventana, burbuja, chat · `vida.py` comportamiento · `agente.py` prompt y herramientas ·
`herramientas.py` permisos · `memoria.py` SQLite + embeddings · `llm.py` Ollama · `sprites.py` pixel art
# Luma
