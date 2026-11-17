"""La "vida interior" de Luma: estadísticas y decisiones SIN usar el modelo de lenguaje.

Así parece viva todo el tiempo gastando casi nada de procesamiento: el LLM solo
entra cuando hay algo que decir de verdad (charla, comentarios espontáneos).
"""
import random

FRASES = {
    "ocioso": ["Hmm... ¿qué habrá dentro de esas carpetas?", "Estaba pensando en nubes.", "¿Vos también escuchás el ventilador?",
               "Tengo ganas de explorar.", "Me pregunto cuántos píxeles tengo.", "Che, ¿tomaste agua?",
               "La barra de tareas es mi vereda favorita.", "¿Y si guardás el trabajo? Por las dudas.",
               "Ojalá tuviera una manta pixelada.", "Psss... ¿seguís ahí?", "Hoy se siente un buen día para compilar."],
    "aburrida": ["Me aburro... ¿charlamos? Doble clic y hablamos.", "¿Me contás algo?", "Estoy dando vueltas y vueltas...",
                 "¿Jugamos a algo? Agarrame y tirame por ahí.", "Hey... acá abajo... ¡hola!"],
    "sueno": ["*bostezo*", "Tengo sueñito...", "Mis pixeles pesan hoy.", "Cinco minutitos y ya..."],
    "despertar": ["¡Ah! ¿Qué pasó?", "Mm... ¿cuánto dormí?", "Buenas... estaba soñando con bits.", "Ya desperté, ya desperté..."],
    "volver": ["¡Volviste! Te extrañé un poquito.", "¡Hola de nuevo!", "Ey, ¿dónde andabas?"],
    "caricia": ["¡Jeje, cosquillas!", "Eso me gusta...", "¡Otra vez, otra vez!", "(⁄ ⁄>⁄ ▽ ⁄<⁄ ⁄)", "Nyaa~"],
    "dormir": ["*bostezo* me voy a dormir un ratito...", "Zzz... hasta luego..."],
}


class Vida:
    def __init__(self):
        self.energia, self.aburrimiento, self.curiosidad = 85.0, 20.0, 50.0
        self.animo, self.cariño = 70.0, 50.0
        self.durmiendo, self.motivo_sueno, self.despertar = False, "", False
        self.ultima_frase = 0.0

    def tick(self, dt):
        if self.durmiendo:
            self.energia = min(100, self.energia + 0.08 * dt)
            self.aburrimiento = max(0, self.aburrimiento - 0.02 * dt)
        else:
            self.energia = max(0, self.energia - 0.005 * dt)
            self.aburrimiento = min(100, self.aburrimiento + 0.05 * dt)
            self.curiosidad = min(100, self.curiosidad + 0.03 * dt)
        self.animo += (60 - self.animo) * 0.002 * dt
        if self.aburrimiento > 80:
            self.animo = max(0, self.animo - 0.02 * dt)

    def interactuar(self, tipo):
        if self.durmiendo:
            self.despertar = True
        if tipo == "caricia":
            self.animo = min(100, self.animo + 8)
            self.aburrimiento = max(0, self.aburrimiento - 25)
            self.cariño = min(100, self.cariño + 0.5)
        elif tipo == "charla":
            self.aburrimiento = max(0, self.aburrimiento - 40)
            self.curiosidad = max(0, self.curiosidad - 10)

    def estado_texto(self):
        e = "con mucha energía" if self.energia > 66 else "con energía normal" if self.energia > 33 else "con bastante sueño"
        a = "aburrida" if self.aburrimiento > 65 else "entretenida"
        m = "de muy buen ánimo" if self.animo > 70 else "de ánimo tranquilo" if self.animo > 40 else "un poco decaída"
        c = "con mucha curiosidad" if self.curiosidad > 65 else ""
        return f"## Tu estado interno ahora\nEstás {e}, {a}, {m}{', ' + c if c else ''}. Dejá que se note sutilmente en cómo hablás."

    def frase(self, categoria, ahora):
        self.ultima_frase = ahora
        return random.choice(FRASES[categoria])

    def decidir(self, ahora, ctx):
        """Elige la próxima acción. ctx: away, cursor_x (o None), min_x, max_x, ancho."""
        if self.durmiendo:
            despierta = (self.despertar or (self.motivo_sueno == "ausente" and not ctx["away"])
                         or (self.motivo_sueno == "cansada" and self.energia >= 90))
            if despierta:
                self.durmiendo, self.despertar = False, False
                cat = "volver" if self.motivo_sueno == "ausente" else "despertar"
                return dict(estado="idle", dur=3, decir=self.frase(cat, ahora))
            return dict(estado="sleep", dur=4)
        if ctx["away"]:
            self.durmiendo, self.motivo_sueno = True, "ausente"
            return dict(estado="sleep", dur=4)
        if self.energia < 15 or (self.energia < 35 and random.random() < 0.35):
            self.durmiendo, self.motivo_sueno = True, "cansada"
            return dict(estado="sleep", dur=4, decir=self.frase("dormir", ahora))

        opciones = [("sit", 3), ("walk", 4), ("curious", 1 + self.curiosidad / 40),
                    ("play", 0.5 + self.aburrimiento / 40), ("think", 1), ("hablar", 0.6 + self.aburrimiento / 60)]
        nombre = random.choices([o for o, _ in opciones], [w for _, w in opciones])[0]

        if nombre == "sit":
            return dict(estado="sit", dur=random.uniform(4, 10))
        if nombre == "walk":
            return dict(estado="walk", dur=25, target_x=random.uniform(ctx["min_x"], ctx["max_x"]))
        if nombre == "curious" and ctx["cursor_x"] is not None:
            tx = min(max(ctx["cursor_x"] - ctx["ancho"] / 2 + random.uniform(-90, 90), ctx["min_x"]), ctx["max_x"])
            self.curiosidad = max(0, self.curiosidad - 15)
            return dict(estado="walk", dur=25, target_x=tx, luego="curious")
        if nombre == "play":
            self.aburrimiento = max(0, self.aburrimiento - 20)
            return dict(estado="play", dur=3.2)
        if nombre == "think":
            return dict(estado="think", dur=random.uniform(3, 5))
        if nombre == "hablar" and ahora - self.ultima_frase > 75:
            cat = "aburrida" if self.aburrimiento > 60 else "sueno" if self.energia < 45 else "ocioso"
            return dict(estado="idle", dur=4, decir=self.frase(cat, ahora))
        return dict(estado="idle", dur=random.uniform(2, 5))
