"""Punkt wejścia dla funkcji serverless Vercel.

Vercel (@vercel/python) wykrywa obiekt ASGI ``app`` i obsługuje przez niego
wszystkie żądania (patrz ``vercel.json``). Dodajemy katalog główny projektu do
``sys.path``, aby pakiet ``koferymentacja`` był importowalny z katalogu ``api/``.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from koferymentacja.web.app import app  # noqa: E402

__all__ = ["app"]
