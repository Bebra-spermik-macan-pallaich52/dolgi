# dolg7

REST API для ролей и профилей на FastAPI и PostgreSQL.

Требования: Python 3.11+, PostgreSQL 14+.

## Запуск

Из папки `dolg7`:

```bash
python -m pip install -r requirements.txt
createdb -h localhost -U postgres dolg7
```

Скопируйте `.env.example` в `.env` и укажите `DATABASE_URL`.
Спецсимволы в пароле URL-кодируйте, например `@` → `%40`.

```bash
uvicorn app.main:main_app --reload
```

Swagger: http://localhost:8000/api/v1/docs
ReDoc: http://localhost:8000/api/v1/redoc

Таблицы создаются автоматически. Сначала добавьте роль, затем профиль.

Проверка: `python -m unittest discover -v`.
