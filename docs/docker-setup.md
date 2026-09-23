# Общий запуск через Docker

Docker Compose запускает backend API v3 с OCR и собранный frontend с nginx. Установленный в Windows Tesseract не требуется: движок и языки eng/rus/kaz входят в backend-образ. В образ также входит утверждённый корпус знаний RU/KK/EN; рабочие индексы создаются на постоянном volume.

## Первый запуск

Нужен Docker Desktop с Linux containers и работающим Docker Engine. Из корня репозитория создайте `.env`, только если его ещё нет:

```powershell
if (!(Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
```

Заполните `EKT_API_USER` и `EKT_API_PASS`. `OPENAI_API_KEY` необязателен: без него работают правила и лексический поиск знаний. Эти значения доступны только backend. Файлы `.env`, SQLite, виртуальное окружение и Git исключены из контекста сборки; пароль не попадает в образ. `.dockerignore` отдельно разрешает `database/knowledge/*.json` и `*.md`, которые Dockerfile копирует в `/app/database/knowledge`.

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

Три SQLite хранятся в именованном volume `nexis_data` проекта Compose и сохраняются после `docker compose down`:

| Путь контейнера | Содержимое |
| --- | --- |
| /data/nexis.sqlite3 | Гостевые сессии, корзины, предложения и ссылки чтения |
| /data/knowledge.sqlite3 | Фрагменты корпуса, метаданные и необязательные embeddings |
| /data/catalog.sqlite3 | Поисковые записи товаров и checkpoint импорта |

Удаление volume удаляет эти данные; для обычной остановки оно не требуется. RAM-контекст диалога, оперативный кеш и лимитер после перезапуска очищаются. Индексы, созданные нативным Python в `database/`, автоматически в Docker volume не копируются.

Браузер обращается к `/api` и `/cart` на frontend. nginx передаёт эти запросы backend внутри Docker. Контейнер backend создаёт ссылки корзины с адресом `http://localhost:5173`. Для развёртывания укажите `NEXIS_PUBLIC_URL=https://ваш-домен` в `.env`; значение должно совпадать с публичным адресом frontend.

Compose задаёт контейнерные `HOST`, `PORT`, `NEXIS_DB_PATH`, `NEXIS_KNOWLEDGE_DB_PATH`, `NEXIS_CATALOG_DB_PATH`, `TESSERACT_CMD` и `BACKEND_PUBLIC_URL` поверх локальных значений `.env`. Остальные настройки backend остаются доступными через `.env`. Frontend собирается с `VITE_API_BASE_URL=/api`.

Это локальная демонстрационная корзина: товары на ekt.kz не резервируются и заказ партнёру не передаётся.

## Индекс знаний и импорт каталога

Лексический индекс создаётся при первом запросе; явная подготовка без сети и модели:

```powershell
docker compose run --rm --no-deps backend python backend/scripts/index_knowledge.py
```

Корпус содержит 53 материала и 159 фрагментов RU/KK/EN. Изменения JSON/версий обновляют индекс, удалённые записи исключаются. После редактирования корпуса сначала пересоберите backend-образ; затем выполните индексацию или запрос к backend. Источники, статусы проверки и ограничения переводов описаны в [README корпуса](../database/knowledge/README.md).

Импорт товаров ограничивается числом страниц за запуск и продолжает с сохранённой точки:

```powershell
docker compose run --rm --no-deps backend python backend/scripts/import_catalog.py --max-pages 100
# Повтор той же команды продолжит импорт; --restart начинает новое обновление.
```

CLI требует настройки ekt.kz, выполняет только GET и сохраняет checkpoint в `/data/catalog.sqlite3`. `complete_catalog:true` появляется только после успешной пустой страницы. Поисковые записи не являются подтверждением цены/остатка: эти поля берутся из актуальной карточки API. В локальной разработке загружены 11 страниц / 220 товаров, следующая страница 12; свежий Docker volume начинает с пустого индекса. Текущее покрытие проверяйте в `/api/health`.

### Необязательные embeddings

После настройки OPENAI_API_KEY следующий явный запуск делает платные запросы для изменённых фрагментов:

```powershell
docker compose run --rm --no-deps backend python backend/scripts/index_knowledge.py --embeddings
```

Чтобы использовать готовые векторы при поиске, задайте `NEXIS_EMBEDDINGS_ENABLED=true` в `.env` и выполните `docker compose up -d backend`. `NEXIS_EMBEDDING_MODEL` по умолчанию `text-embedding-3-small`; индекс и запрос должны использовать одну модель. Поисковые вопросы также требуют внешней векторизации. При отсутствии готовых векторов/ключа или ошибке остаётся лексический поиск с указанием фактического режима.

В текущей проверенной конфигурации ключ отсутствовал; платные вызовы не выполнялись. Health возвращает `retrieval` с объёмом индекса, моделью, количеством векторов и причиной недоступности гибридного режима. `agent_mode:tools` отражает настройку планировщика и не доказывает успешный ответ OpenAI.

## Проверка OCR и backend

```powershell
docker compose run --rm --no-deps backend python backend/scripts/doctor.py --require-ocr --ocr-smoke
docker compose run --rm --no-deps backend python -m unittest discover -s backend/tests -p "test_*.py" -v
docker compose run --rm --no-deps backend python -m backend.evals.run
```

Doctor проверяет executable и языки, затем распознаёт сгенерированное изображение с артикулом и количеством. Он не отправляет запросы в ekt.kz/OpenAI, не печатает секреты и не использует документы клиентов. Эта проверка подтверждает работу движка; качество на фотографиях пользователя зависит от читаемости маркировки.

Тесты работают с синтетическим каталогом и временными SQLite. 72 сценария `backend.evals` — офлайн-набор разработки на RU/KK/EN, не измерение качества реальной модели или скорости живого API. Runner отключает модель/embeddings внутри процесса и не меняет `.env`. Итог новых прогонов: [журнал v3](agent-v3-implementation.md).

Для диагностики без Docker: `.\.venv\Scripts\python.exe backend/scripts/doctor.py`. В нативном режиме движок OCR устанавливается отдельно. Публичного deployed-адреса в репозитории нет; `localhost:5173` доступен только на компьютере, где запущен стек.

## Источники зависимостей

- [Официальный Python Docker image](https://hub.docker.com/_/python): Python 3.14.7 slim-trixie.
- [Установка Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html): нужны движок и языковые данные.
- Языковые пакеты Debian: [русский](https://packages.debian.org/trixie/tesseract-ocr-rus), [казахский](https://packages.debian.org/trixie/tesseract-ocr-kaz).

Python зависимости зафиксированы в `backend/requirements-lock.txt`; системные пакеты Debian получают актуальные исправления при новой сборке.
