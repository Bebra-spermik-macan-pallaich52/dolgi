"""Параметры подключения из окружения и .env в корне проекта."""

import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DB_USER = os.getenv("DB_USER") or "postgres"
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST") or "localhost"
DB_PORT = os.getenv("DB_PORT") or "5432"
DB_NAME = os.getenv("DB_NAME") or "cafe_db"

# make_conninfo экранирует пробелы, кавычки и символы @, :, / в пароле.
DATABASE_URL = make_conninfo(
    user=DB_USER, password=DB_PASSWORD, host=DB_HOST,
    port=DB_PORT, dbname=DB_NAME, connect_timeout=5,
)
