# dolg5 — подключение PostgreSQL из Python

Учебное консольное приложение по материалу «Подключение базы данных».
Сохранена структура исходного проекта: модели, контроллеры, конфигурация,
пул соединений и контекстный курсор. Приложение показывает клиентов,
добавляет их и удаляет по ID.

## Что реализовано

- Настройки PostgreSQL загружаются из `.env` в корне проекта.
- `psycopg` и `psycopg_pool` обеспечивают подключение через пул.
- `get_cursor()` фиксирует успешную транзакцию и откатывает её при исключении.
- `ClientController` выполняет параметризованные запросы к таблице `clients`
  и возвращает объекты `Client`.
- Меню обрабатывает неверный ввод, повторяющиеся имя/email,
  отсутствующий ID и запрет удаления клиента с заказами.
- Пароль вводится скрыто и хранится как PBKDF2-SHA256 с индивидуальной солью.
  Хеш отсутствует в выводе меню, `to_dict()` и `repr()` клиента.
- Пул закрывается при выходе, Ctrl+C, завершении ввода и ошибке подключения.

## Требования

Python 3.10 или новее, установленный и запущенный PostgreSQL 14 или новее.
Команды `psql` и `createdb` должны быть доступны в терминале.
В Windows при необходимости добавьте папку `bin` PostgreSQL в `PATH`
или используйте SQL Shell/pgAdmin.

## 1. Подготовить Python

Откройте терминал в распакованной папке `dolg5`:

```text
python -m venv .venv
```

Активируйте окружение одной из команд для вашей системы.

Windows (cmd):

```bat
.venv\Scripts\activate.bat
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Установите зависимости:

```text
python -m pip install -r requirements.txt
```

`Faker` включён в зависимости согласно презентации; приложение не заполняет
базу автоматически. После импорта исходного SQL таблицы пустые.

## 2. Создать базу и импортировать SQL

Используйте новую пустую базу `cafe_db` и пользователя `postgres`:

```text
createdb -h localhost -p 5432 -U postgres cafe_db
psql -h localhost -p 5432 -U postgres -d cafe_db -v ON_ERROR_STOP=1 -f script_cafe_db.sql
```

Утилиты запросят установленный при настройке PostgreSQL пароль.
Исходный SQL включён без изменения: он создаёт `clients`, `menu`, `orders`,
`order_items`, последовательности, уникальные и внешние ключи.
В дампе владельцем объектов указан `postgres`, поэтому для импорта используется
именно этот пользователь. Повторно импортировать скрипт в ту же базу не нужно.

Если базу создаёте через pgAdmin, выполните только второй шаг — импорт через
`psql`. Дамп содержит команды `COPY ... FROM stdin`, поэтому для его загрузки
используется `psql`.

## 3. Настроить подключение

Скопируйте `.env.example` в `.env`.

Windows (cmd):

```bat
copy .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Откройте `.env` и укажите параметры своего сервера:

```dotenv
DB_USER=postgres
DB_PASSWORD=ваш_пароль_PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cafe_db
```

Для пароля с пробелами или символом `#` используйте кавычки по формату `.env`,
например `DB_PASSWORD="пароль с пробелами"`.
Переменные окружения операционной системы имеют приоритет над `.env`.
Локальный файл `.env` исключён из Git; исходные учётные данные в архив не входят.

## 4. Запустить

Из папки `dolg5`:

```text
python -m app.main
```

Меню:

```text
1. Показать всех клиентов
2. Добавить клиента
3. Удалить клиента
0. Выход
```

Сначала добавьте клиента пунктом `2`, затем проверьте пункт `1`.
Телефон можно оставить пустым. Имя, пароль и email обязательны,
имя и email должны быть уникальны. Пароль при вводе не отображается.
Для удаления используйте ID, показанный после добавления или в списке.
Клиент, на которого ссылается заказ, не удаляется: действует внешний ключ БД.

## Структура

```text
dolg5/
├── app/
│   ├── main.py                         # Консольное меню и точка входа
│   ├── core/
│   │   ├── config.py                   # .env и строка подключения
│   │   └── utils.py                    # Хеширование пароля
│   ├── db/
│   │   ├── database.py                 # Жизненный цикл пула
│   │   └── session.py                  # Курсор и транзакции
│   ├── models/client.py                # Dataclass Client
│   └── controllers/client_controller.py
├── tests/test_integration.py
├── .env.example
├── .gitignore
├── requirements.txt
├── script_cafe_db.sql
└── README.md
```

## Проверка

Интеграционные тесты проверяют реальные операции PostgreSQL, фиксацию и откат,
пагинацию, уникальность, внешние ключи, хеширование и повторное открытие пула.
Создайте отдельную тестовую базу и один раз импортируйте в неё тот же SQL:

```text
createdb -h localhost -p 5432 -U postgres cafe_test_db
psql -h localhost -p 5432 -U postgres -d cafe_test_db -v ON_ERROR_STOP=1 -f script_cafe_db.sql
```

После настройки `.env` запустите тесты с другим именем базы.

Windows (cmd):

```bat
set DB_NAME=cafe_test_db
set CAFE_TEST_DB=1
python -m unittest discover -v
set CAFE_TEST_DB=
set DB_NAME=
```

PowerShell:

```powershell
$env:DB_NAME = "cafe_test_db"
$env:CAFE_TEST_DB = "1"
python -m unittest discover -v
Remove-Item Env:CAFE_TEST_DB
Remove-Item Env:DB_NAME
```

Linux/macOS:

```bash
CAFE_TEST_DB=1 DB_NAME=cafe_test_db python -m unittest discover -v
```

Тесты удаляют только созданные ими записи. Без `CAFE_TEST_DB=1` проверки БД
пропускаются. Для встраивания контроллера в другой код сначала вызовите
`init_db()`, а в блоке `finally` — `close_db()`. Метод `add_client()` принимает
уже готовый `password_hash`; меню формирует его через `hash_password()`.
