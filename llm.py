"""Cliente mínimo de Ollama (todo local, sin APIs de pago)."""
import json
import threading
import urllib.error
import urllib.request


class LLMError(Exception):
    pass


class Ollama:
    def __init__(self, cfg):
        self.cfg = cfg
        self.lock = threading.Lock()   # una sola charla con el modelo a la vez

    @property
    def url(self):
        return self.cfg["ollama_url"].rstrip("/")

    def _post(self, path, payload, timeout):
        req = urllib.request.Request(self.url + path, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise LLMError(f"No encuentro el modelo '{payload.get('model')}'. "
                               f"Bajalo con:  ollama pull {payload.get('model')}")
            raise LLMError("Ollama devolvió un error: " + e.read().decode(errors="replace")[:200])
        except (urllib.error.URLError, OSError):
            raise LLMError("No puedo hablar con Ollama. ¿Está abierto? "
                           "(abrí la app de Ollama o corré 'ollama serve' en una terminal)")

    def chat(self, messages, model=None, on_text=None, temperature=0.8, max_tokens=None):
        model = model or self.cfg["modelo"]
        options = {"temperature": temperature, "num_ctx": int(self.cfg["contexto_tokens"])}
        if max_tokens:
            options["num_predict"] = max_tokens
        payload = {"model": model, "messages": messages, "stream": True,
                   "keep_alive": "30m", "options": options}
        if "qwen3" in model:
            payload["think"] = False
        partes = []
        with self._post("/api/chat", payload, 600) as resp:
            for linea in resp:
                if not linea.strip():
                    continue
                d = json.loads(linea)
                if "error" in d:
                    raise LLMError(str(d["error"])[:200])
                trozo = d.get("message", {}).get("content", "")
                if trozo:
                    partes.append(trozo)
                    if on_text:
                        on_text("".join(partes))
                if d.get("done"):
                    break
        return "".join(partes)

    def embed(self, texto):
        with self._post("/api/embed", {"model": self.cfg["modelo_embeddings"], "input": texto}, 30) as resp:
            return json.loads(resp.read())["embeddings"][0]
