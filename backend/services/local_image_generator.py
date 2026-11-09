"""
Client for the local image worker (local_image_worker/worker.py, FLUX.1 Kontext on your GPU).

The worker runs in its own virtualenv because of its heavy dependencies; the backend only talks
to it over HTTP on 127.0.0.1. See local_image_worker/README.md.
"""

import io
import logging
import os

import httpx
from PIL import Image

logger = logging.getLogger(__name__)

WORKER_URL = os.environ.get("SAGA_IMAGE_WORKER_URL", "http://127.0.0.1:8071")
TIMEOUT = 900          # the first image also loads the model (minutes on a 12 GB card)


class LocalWorkerUnavailable(RuntimeError):
    pass


class LocalImageGenerator:
    def health(self) -> dict:
        try:
            r = httpx.get(f"{WORKER_URL}/health", timeout=3)
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def generate_image(self, prompt: str, negative_prompt: str = "", width: int = 1024, height: int = 1024,
                       reference_image_path: str | None = None, edit: bool = False) -> Image.Image:
        """edit=True: change the reference picture itself (same framing), e.g. open a door."""
        payload = {"prompt": prompt, "width": int(width), "height": int(height), "edit": bool(edit)}
        if reference_image_path:
            payload["reference_image"] = os.path.abspath(reference_image_path)
        try:
            r = httpx.post(f"{WORKER_URL}/generate", json=payload, timeout=TIMEOUT)
        except httpx.ConnectError:
            raise LocalWorkerUnavailable(
                "O gerador local de imagens não está rodando. Inicie-o com "
                "`local_image_worker\\.venv\\Scripts\\python local_image_worker\\worker.py` "
                "(veja local_image_worker/README.md) ou troque a fonte das imagens para Gemini.")
        if r.status_code != 200:
            try:
                detail = r.json().get("error")
            except Exception:
                detail = r.text[:300]
            raise RuntimeError(f"gerador local falhou: {detail}")
        return Image.open(io.BytesIO(r.content)).convert("RGB")


local_image_service = LocalImageGenerator()
