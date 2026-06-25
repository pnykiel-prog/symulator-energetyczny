# Samodzielny moduł koferymentacyjny (web + API) — obraz do hostingu u gminy.
FROM python:3.11-slim

WORKDIR /app

# zależności (warstwa cache'owana, gdy kod się zmienia a wymagania nie)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# kod aplikacji
COPY pyproject.toml ./
COPY koferymentacja ./koferymentacja
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# uruchomienie serwera ASGI
CMD ["uvicorn", "koferymentacja.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
