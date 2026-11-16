# dolg6

Работа с ролями и профилями: CRUD, поиск, сортировка, авторизация.

Требования: Python 3.10+, PostgreSQL 14+.

## Запуск

Из папки `dolg6`:

```bash
python -m pip install -r requirements.txt
createdb -h localhost -U postgres dolg6
```

Скопируйте `.env.example` в `.env` и укажите `DATABASE_URL`.
Спецсимволы в пароле URL-кодируйте, например `@` → `%40`.

```bash
python -m app.main
```

Таблицы создаются автоматически. Сначала добавьте роль, затем профиль.

Проверка: `python -m unittest discover -v`.
