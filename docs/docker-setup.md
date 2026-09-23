# Общий запуск через Docker

Docker Compose запускает backend с OCR и собранный frontend с nginx. Установленный в Windows Tesseract не требуется: движок и языки eng/rus/kaz входят в backend-образ.

## Первый запуск

Нужен Docker Desktop с Linux containers и работающим Docker Engine. Из корня репозитория создайте `.env`, только если его ещё нет:

```powershell
if (!(Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```

Заполните `EKT_API_USER` и `EKT_API_PASS`. `OPENAI_API_KEY` необязателен. Эти значения доступны только backend. Файлы `.env`, SQLite, виртуальное окружение и Git исключены из контекста сборки; пароль не попадает в образ.

```powershell
docker compose up --build -d
```

Первый запуск загружает образы, системные и Python/npm зависимости. Frontend запускается после успешного healthcheck backend.

- Приложение: http://localhost:5173
- Swagger: http://localhost:8000/docs
- Состояние: http://localhost:5173/api/health
- Логи: `docker compose logs --tail 100`
- Остановить: `docker compose down`

Порты публикуются только на localhost. Перед запуском остановите отдельные dev-серверы, если они занимают 5173 или 8000. Для удалённой демонстрации настройте адреса публикации и HTTPS отдельно.

## Данные и настройки

SQLite хранится в именованном volume `nexis_data` проекта Compose и сохраняется после `docker compose down`. Удаление volume удаляет демонстрационные корзины и сессии; для обычной остановки оно не требуется.

Браузер обращается к `/api` и `/cart` на frontend. nginx передаёт эти запросы backend внутри Docker. Контейнер backend создаёт ссылки корзины с адресом `http://localhost:5173`. Для развёртывания укажите `NEXIS_PUBLIC_URL=https://ваш-домен` в `.env`; значение должно совпадать с публичным адресом frontend.

Compose задаёт контейнерные `HOST`, `PORT`, `NEXIS_DB_PATH`, `TESSERACT_CMD` и `BACKEND_PUBLIC_URL` поверх локальных значений `.env`. Остальные настройки backend остаются доступными через `.env`. Frontend собирается с `VITE_API_BASE_URL=/api`.

Это локальная демонстрационная корзина: товары на ekt.kz не резервируются и заказ партнёру не передаётся.

## Проверка OCR и backend

```powershell
docker compose run --rm --no-deps backend python backend/scripts/doctor.py --require-ocr --ocr-smoke
docker compose run --rm --no-deps backend python -m unittest discover -s backend/tests -p "test_*.py" -v
```

Doctor проверяет executable и языки, затем распознаёт сгенерированное изображение с артикулом и количеством. Он не отправляет запросы в ekt.kz/OpenAI, не печатает секреты и не использует документы клиентов. Эта проверка подтверждает работу движка; качество на фотографиях пользователя зависит от читаемости маркировки.

Тесты работают с синтетическим каталогом и временными SQLite. Для диагностики без Docker: `.\.venv\Scripts\python.exe backend/scripts/doctor.py`. В нативном режиме движок OCR устанавливается отдельно.

## Источники зависимостей

- [Официальный Python Docker image](https://hub.docker.com/_/python): Python 3.14.7 slim-trixie.
- [Установка Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html): нужны движок и языковые данные.
- Языковые пакеты Debian: [русский](https://packages.debian.org/trixie/tesseract-ocr-rus), [казахский](https://packages.debian.org/trixie/tesseract-ocr-kaz).

Python зависимости зафиксированы в `backend/requirements-lock.txt`; системные пакеты Debian получают актуальные исправления при новой сборке.
