
"""
LUMA CAKE SLIME
Pixel art 32x32 generado mediante código.
PySide6 - Sin imágenes externas.

Una pequeña torta viviente de crema blanca y verde menta.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap

SIZE = 32

C = {
    "outline": (67, 53, 68),

    # Bizcocho
    "cake": (255, 231, 207),
    "cake_sh": (224, 190, 166),
    "cake_dark": (190, 153, 135),

    # Crema blanca
    "cream": (255, 250, 237),
    "cream_hi": (255, 255, 255),
    "cream_sh": (238, 225, 208),

    # Crema verde menta
    "mint": (153, 235, 197),
    "mint_hi": (202, 255, 226),
    "mint_sh": (105, 195, 157),

    # Cara
    "eye": (65, 45, 70),
    "eye_hi": (255, 255, 255),
    "blush": (255, 153, 171),
    "mouth": (155, 75, 105),

    # Decoraciones
    "pink": (255, 150, 183),
    "blue": (126, 213, 226),
    "yellow": (255, 220, 120),
    "candle": (255, 160, 180),
    "flame": (255, 177, 65),
    "flame_hi": (255, 240, 140),

    "star": (255, 220, 120),
    "zzz": (165, 190, 255),
    "heart": (255, 105, 150),
}


def _col(name):
    return QColor(*C[name])


class _Canvas:

    def __init__(self):
        self.img = QImage(
            SIZE, SIZE,
            QImage.Format.Format_ARGB32
        )
        self.img.fill(0)

        self.p = QPainter(self.img)
        self.p.setPen(Qt.PenStyle.NoPen)

    def r(self, x, y, w, h, c):
        self.p.fillRect(x, y, w, h, _col(c))

    def px(self, x, y, c):
        self.r(x, y, 1, 1, c)

    def pts(self, points, c):
        for x, y in points:
            self.px(x, y, c)

    def end(self):
        self.p.end()
        return self.img


# --------------------------------------------------
# CONTORNO AUTOMÁTICO
# --------------------------------------------------

def _outline(img):

    out = QImage(img)
    oc = _col("outline")

    for y in range(SIZE):
        for x in range(SIZE):

            if img.pixelColor(x, y).alpha() == 0:

                for nx, ny in (
                    (x + 1, y),
                    (x - 1, y),
                    (x, y + 1),
                    (x, y - 1)
                ):

                    if (
                        0 <= nx < SIZE
                        and 0 <= ny < SIZE
                        and img.pixelColor(nx, ny).alpha() > 0
                    ):
                        out.setPixelColor(x, y, oc)
                        break

    return out


# --------------------------------------------------
# RENDER PRINCIPAL
# --------------------------------------------------

def _render(p):

    cv = _Canvas()
    r, px = cv.r, cv.px

    dy = p["dy"]
    wobble = p["wobble"]
    squash = p["squash"]

    Y = lambda y: y + dy

    # Pequeñas deformaciones inferiores.
    # El cuerpo sigue teniendo una sola capa.

    # --------------------------------------------------
    # BIZCOCHO
    # --------------------------------------------------

    cake_rows = {
        13: (9, 22),
        14: (7, 24),
        15: (6, 25),
        16: (5, 26),
        17: (5, 26),
        18: (5, 26),
        19: (5, 26),
        20: (5, 26),
        21: (5, 26),
        22: (5, 26),
        23: (6, 25),
        24: (7, 24),
        25: (9, 22),
    }

    for y, (x1, x2) in cake_rows.items():

        shift = wobble if y >= 21 else 0

        if squash and y >= 23:
            x1 -= squash
            x2 += squash

        r(
            x1 + shift,
            Y(y),
            x2 - x1 + 1,
            1,
            "cake"
        )

    # Sombra lateral e inferior.
    r(6, Y(18), 1, 4, "cake_sh")
    r(25, Y(18), 1, 4, "cake_sh")
    r(8, Y(24), 16, 1, "cake_sh")
    r(10, Y(25), 12, 1, "cake_dark")

    # Base.
    r(9, Y(26), 14, 1, "cream_sh")

    # --------------------------------------------------
    # COBERTURA SUPERIOR
    # --------------------------------------------------

    # Forma de crema sobre la torta.
    r(12, Y(8), 8, 1, "cream")
    r(9, Y(9), 14, 1, "cream")
    r(8, Y(10), 16, 1, "cream")
    r(7, Y(11), 18, 1, "cream")
    r(7, Y(12), 18, 1, "cream")

    # Crema verde menta en algunos sectores.
    r(8, Y(11), 4, 1, "mint")
    r(9, Y(10), 3, 1, "mint_hi")
    r(20, Y(11), 4, 1, "mint")
    r(21, Y(10), 2, 1, "mint_hi")

    # Brillos superiores.
    px(13, Y(9), "cream_hi")
    px(14, Y(8), "cream_hi")
    px(19, Y(10), "cream_hi")

    # --------------------------------------------------
    # GLASEADO QUE CAE POR LOS BORDES
    # --------------------------------------------------

    # Frente blanco.
    r(7, Y(13), 18, 1, "cream")
    r(6, Y(14), 2, 2, "cream")
    r(24, Y(14), 2, 2, "cream")

    # Goteos blancos.
    r(8, Y(14), 2, 2, "cream")
    r(12, Y(14), 2, 3, "cream")
    r(17, Y(14), 2, 2, "cream")
    r(22, Y(14), 2, 3, "cream")

    # Goteos verdes.
    r(10, Y(13), 2, 1, "mint")
    r(10, Y(14), 1, 2, "mint")
    r(20, Y(13), 2, 1, "mint")
    r(21, Y(14), 1, 2, "mint")

    # Sombras del glaseado.
    px(9, Y(16), "cream_sh")
    px(13, Y(17), "cream_sh")
    px(18, Y(16), "cream_sh")
    px(23, Y(17), "cream_sh")

    # --------------------------------------------------
    # CARA KAWAII
    # --------------------------------------------------

    eye_y = Y(17)

    if p["eyes"] == "open":

        # Ojos.
        r(10, eye_y, 3, 4, "eye")
        r(19, eye_y, 3, 4, "eye")

        # Reflejos.
        px(11, eye_y, "eye_hi")
        px(20, eye_y, "eye_hi")

        px(12, eye_y + 2, "cream_hi")
        px(21, eye_y + 2, "cream_hi")

    elif p["eyes"] == "happy":

        cv.pts([
            (10, eye_y + 2),
            (11, eye_y + 1),
            (12, eye_y + 2),
            (19, eye_y + 2),
            (20, eye_y + 1),
            (21, eye_y + 2)
        ], "eye")

    elif p["eyes"] == "closed":

        r(10, eye_y + 2, 3, 1, "eye")
        r(19, eye_y + 2, 3, 1, "eye")

    elif p["eyes"] == "sad":

        r(10, eye_y, 3, 3, "eye")
        r(19, eye_y, 3, 3, "eye")
        px(13, eye_y + 4, "blue")

    elif p["eyes"] == "squint":

        r(10, eye_y + 2, 3, 1, "eye")
        r(19, eye_y + 2, 3, 1, "eye")

    # Mejillas.
    if p["blush"]:
        r(8, Y(21), 2, 1, "blush")
        r(22, Y(21), 2, 1, "blush")

    # Boca.
    mouth = p["mouth"]

    if mouth == "closed":
        r(15, Y(22), 2, 1, "mouth")

    elif mouth == "smile":
        cv.pts([
            (14, Y(21)),
            (15, Y(22)),
            (16, Y(22)),
            (17, Y(21))
        ], "mouth")

    elif mouth == "open":
        r(14, Y(21), 4, 2, "mouth")

    elif mouth == "o":
        r(15, Y(21), 2, 2, "mouth")

    # --------------------------------------------------
    # DECORACIONES DE LA TORTA
    # --------------------------------------------------

    # Sprinkles de colores.
    r(11, Y(12), 1, 1, "pink")
    r(15, Y(11), 1, 1, "blue")
    r(19, Y(12), 1, 1, "pink")
    r(23, Y(12), 1, 1, "yellow")

    # Pequeños detalles del frente.
    px(8, Y(15), "mint_hi")
    px(23, Y(15), "mint_hi")

    # --------------------------------------------------
    # VELITAS
    # --------------------------------------------------

    if p["candles"]:

        # Vela izquierda.
        r(9, Y(5), 2, 5, "candle")
        r(9, Y(6), 2, 1, "cream_hi")

        # Vela derecha.
        r(21, Y(5), 2, 5, "blue")
        r(21, Y(7), 2, 1, "cream_hi")

        # Llamas.
        r(9, Y(3), 2, 2, "flame")
        px(9, Y(2), "flame_hi")
        px(10, Y(3), "flame_hi")

        r(21, Y(3), 2, 2, "flame")
        px(21, Y(2), "flame_hi")
        px(22, Y(3), "flame_hi")

    # --------------------------------------------------
    # EFECTOS
    # --------------------------------------------------

    # Corazón.
    if p["heart"]:

        rows = [
            " X X ",
            "XXXXX",
            "XXXXX",
            " XXX ",
            "  X  "
        ]

        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch == "X":
                    px(24 + i, Y(2 + j), "heart")

    # Estrellas.
    if p["star"]:

        cv.pts([
            (3, Y(10)),
            (4, Y(9)),
            (5, Y(10)),
            (4, Y(11)),
            (27, Y(8)),
            (28, Y(7)),
            (29, Y(8)),
            (28, Y(9))
        ], "star")

    # Sueño.
    if p["zzz"]:

        cv.pts([
            (25, Y(5)),
            (26, Y(5)),
            (27, Y(5)),
            (26, Y(6)),
            (25, Y(7)),
            (26, Y(7)),
            (27, Y(7))
        ], "zzz")

    # Puntos de pensamiento.
    for i in range(p["dots"]):
        px(21 + i * 2, Y(5), "blue")

    return _outline(cv.end())


# --------------------------------------------------
# CONTROL DE ANIMACIONES
# --------------------------------------------------

def make_pose(
    state,
    t,
    look=0,
    lookup=False,
    talking=False
):

    p = dict(
        dy=0,
        wobble=0,
        squash=0,
        eyes="open",
        mouth="smile",
        blush=True,
        candles=False,
        heart=0,
        star=False,
        zzz=0,
        dots=0
    )

    phase = int(t * 4) % 4

    # IDLE: respiración gelatinosa.
    if state == "idle":

        p["dy"] = int(t * 2) % 2
        p["squash"] = 0

    # WALK: se balancea de lado a lado.
    elif state == "walk":

        p["dy"] = phase % 2
        p["wobble"] = 1 if phase < 2 else -1
        p["squash"] = 1 if phase == 0 else 0

    # CURIOSIDAD.
    elif state == "curious":

        p["dy"] = 1
        p["eyes"] = "open"
        p["mouth"] = "o"

    # DESCANSO.
    elif state == "sit":

        p["dy"] = int(t * 2) % 2
        p["eyes"] = "closed" if t % 5 < 0.15 else "open"

    # SUEÑO.
    elif state == "sleep":

        p["eyes"] = "closed"
        p["mouth"] = "closed"
        p["zzz"] = 1

    # PENSAMIENTO.
    elif state == "think":

        p["eyes"] = "closed"
        p["dots"] = int(t * 1.5) % 4

    # FELICIDAD.
    elif state == "happy":

        p["eyes"] = "happy"
        p["mouth"] = "smile"
        p["dy"] = phase % 2
        p["squash"] = 1 if phase == 0 else 0
        p["candles"] = True
        p["heart"] = 1

    # JUEGO.
    elif state == "play":

        p["eyes"] = "happy"
        p["mouth"] = "open"
        p["dy"] = phase % 2
        p["wobble"] = 1 if phase < 2 else -1
        p["candles"] = True
        p["star"] = True

    # TIMIDEZ.
    elif state == "shy":

        p["eyes"] = "closed"
        p["mouth"] = "smile"
        p["blush"] = True

    # TRISTEZA.
    elif state == "sad":

        p["eyes"] = "sad"
        p["mouth"] = "closed"
        p["dy"] = 1

    # ESFUERZO.
    elif state == "drag":

        p["eyes"] = "squint"
        p["mouth"] = "o"
        p["wobble"] = 1

    # SALUDAR.
    elif state == "wave":

        p["eyes"] = "happy"
        p["mouth"] = "smile"
        p["wobble"] = phase % 2

    # PARPADEO.
    if state not in ("sleep", "sad", "think"):

        if t % 4.3 < 0.14:
            p["eyes"] = "closed"

    # HABLAR.
    if talking and state not in ("sleep", "drag"):

        p["mouth"] = (
            "open" if int(t * 7) % 2 else "closed"
        )

    return p


# --------------------------------------------------
# PIXMAP Y CACHÉ
# --------------------------------------------------

_cache = {}


def pixmap(pose, facing=1, scale=5):

    key = (
        tuple(pose.values()),
        facing,
        scale
    )

    pm = _cache.get(key)

    if pm is None:

        img = _render(pose)

        if facing < 0:
            img = img.mirrored(True, False)

        img = img.scaled(
            SIZE * scale,
            SIZE * scale,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )

        pm = QPixmap.fromImage(img)

        if len(_cache) > 600:
            _cache.clear()

        _cache[key] = pm

    return pm
