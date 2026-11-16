# dolg5

Просмотр, добавление и удаление клиентов в PostgreSQL.

Требования: Python 3.10+, PostgreSQL 14+.

## Запуск

Из папки `dolg5`:

```bash
python -m pip install -r requirements.txt
createdb -h localhost -U postgres cafe_db
psql -h localhost -U postgres -d cafe_db -v ON_ERROR_STOP=1 -f script_cafe_db.sql
```

Скопируйте `.env.example` в `.env` и заполните параметры подключения `DB_*`.

```bash
python -m app.main
```
