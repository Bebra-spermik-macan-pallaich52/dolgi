# dolg8

API клиентов и тарифов на FastAPI, SQLModel и PostgreSQL.
Сессия БД передаётся из роутера в контроллер через `Depends(get_session)`.

Создайте БД `dolg8`, скопируйте `.env.example` в `.env` и укажите подключение.

```bash
python -m pip install -r requirements.txt
python -m app.main
```

Запускайте из папки `dolg8`. Swagger: http://localhost:8000/api/v1/docs

Сначала добавьте тариф через `POST /api/v1/tarifs`, затем клиента через `POST /api/v1/clients`.
Проверка: `python -m unittest discover -v`.
