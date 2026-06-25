"""Punkt wejścia dla funkcji serverless Vercel.

Vercel (@vercel/python) wykrywa obiekt ASGI ``app`` i obsługuje przez niego
wszystkie żądania (patrz ``vercel.json``). Dodajemy katalog główny projektu do
``sys.path``, aby pakiet ``koferymentacja`` był importowalny z katalogu ``api/``.

Jeśli import silnika zawiedzie (np. brak zależności albo niezbundlowany pakiet),
zamiast nieczytelnego „could not import api/index.py" wstaje minimalna aplikacja
ASGI bez zależności, która pokazuje pełny traceback na każdym adresie — to
ułatwia diagnozę na środowisku serverless.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from koferymentacja.web.app import app  # noqa: E402
except Exception:  # pragma: no cover - tylko ścieżka diagnostyczna na deployu
    _traceback = traceback.format_exc()
    _diag = (
        "IMPORT modułu koferymentacja NIE POWIÓDŁ SIĘ na środowisku serverless.\n\n"
        f"Python: {sys.version}\n"
        f"sys.path[0]: {sys.path[0]}\n"
        f"__file__: {os.path.abspath(__file__)}\n"
        f"zawartość katalogu głównego: {os.listdir(sys.path[0])}\n\n"
        f"{_traceback}"
    )

    async def app(scope, receive, send):  # type: ignore[no-redef]
        """Awaryjna aplikacja ASGI — zwraca traceback importu jako tekst."""
        if scope["type"] != "http":
            return
        body = _diag.encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": body})


__all__ = ["app"]
