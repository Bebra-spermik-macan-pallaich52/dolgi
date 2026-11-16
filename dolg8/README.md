# dolg8

API «Телефонные номера»: клиенты, тарифы, поиск и статистика.

Требования: Python 3.11+, PostgreSQL 14+.

## Запуск

Из папки `dolg8`:

```bash
python -m pip install -r requirements.txt
createdb -h localhost -U postgres dolg8
```

Скопируйте `.env.example` в `.env` и укажите `DATABASE_URL`.
Спецсимволы в пароле URL-кодируйте, например `@` → `%40`.

```bash
uvicorn app.main:main_app --reload
```

Swagger: http://localhost:8000/api/v1/docs
ReDoc: http://localhost:8000/api/v1/redoc

Таблицы создаются автоматически. Добавление данных: `POST /api/v1/tarifs` и `POST /api/v1/clients`.
В query-параметрах код `+7` передавайте как `%2B7`.

Проверка: `python -m unittest discover -v`.
