"""Punkt wejścia dla funkcji serverless Vercel.

Vercel (@vercel/python) najpierw STATYCZNIE szuka zmiennej ``app`` na najwyższym
poziomie pliku (detekcja w buildzie), a potem WYKONUJE import w runtime. Dlatego
``app`` musi być przypisany na top-level (kolumna 0) — jego wartość liczy helper
``_zbuduj_app`` z obsługą błędu.

Jeśli import silnika zawiedzie (brak zależności / niezbundlowany pakiet), zamiast
nieczytelnego „could not import" wstaje minimalna aplikacja ASGI bez zależności,
która pokazuje pełny traceback na każdym adresie — ułatwia diagnozę na deployu.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _zbuduj_app():
    try:
        from koferymentacja.web.app import app as prawdziwa_app

        return prawdziwa_app
    except Exception:  # pragma: no cover - ścieżka diagnostyczna na deployu
        diag = (
            "IMPORT modułu koferymentacja NIE POWIÓDŁ SIĘ na środowisku serverless.\n\n"
            f"Python: {sys.version}\n"
            f"sys.path[0]: {sys.path[0]}\n"
            f"__file__: {os.path.abspath(__file__)}\n"
            f"zawartość {sys.path[0]}: {sorted(os.listdir(sys.path[0]))}\n\n"
            f"{traceback.format_exc()}"
        )

        async def _awaryjna(scope, receive, send):
            if scope["type"] != "http":
                return
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            })
            await send({"type": "http.response.body", "body": diag.encode("utf-8")})

        return _awaryjna


app = _zbuduj_app()

__all__ = ["app"]
