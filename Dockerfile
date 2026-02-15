FROM python:3.12-slim

RUN pip install poetry

WORKDIR /teampling

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false

RUN poetry install --no-root --only main

COPY . .

EXPOSE 8000