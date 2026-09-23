# Backend NEXIS

FastAPI API версии 2.0.0. Все команды ниже выполняются из корня репозитория. Frontend для проверки API не нужен.

## Установка и запуск

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-lock.txt
Copy-Item .env.example .env
# Заполните API credentials в локальном .env.
.\.venv\Scripts\python.exe backend/main.py
~~~

Не перезаписывайте существующий .env. Он читается из корня независимо от текущего каталога. SQLite создаётся автоматически в database/nexis.sqlite3 и исключена из Git.

На Linux/macOS путь Python — .venv/bin/python. Набор зависимостей проверен на Windows/Python 3.14. Для переносимости есть список прямых зависимостей requirements.txt.

- Swagger: http://localhost:8000/docs
- Состояние: http://localhost:8000/api/health
- Возможности интеграции: http://localhost:8000/api/integrations

Сервер по умолчанию слушает 127.0.0.1. Для контейнера задайте HOST=0.0.0.0. Для развёртывания настройте HTTPS, BACKEND_PUBLIC_URL и точные CORS_ORIGINS. Не доверяйте произвольному X-Forwarded-For; ограничение IP использует адрес соединения. Для нескольких воркеров нужен общий лимитер на reverse proxy; текущий лимитер локален процессу.

## Консультация и добавление

Пример PowerShell: первая часть ничего не добавляет.

~~~powershell
$api = 'http://localhost:8000'
$session = Invoke-RestMethod -Method Post "$api/api/session"
$headers = @{ 'X-Session-Id' = $session.session_id }
$body = @{ session_id=$session.session_id; message='515291'; history=@(); language='ru' } | ConvertTo-Json
$reply = Invoke-RestMethod -Method Post "$api/api/agent/chat" -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$reply.answer
$reply.sources
$selection = @{ product_id=515291; quantity=1 } | ConvertTo-Json
$offer = Invoke-RestMethod -Method Post "$api/api/cart/offer" -Headers $headers -ContentType 'application/json' -Body $selection
$offer
~~~

Покажите клиенту товар, количество, цену и предупреждения. Только после его явного подтверждения выполните следующую часть:

~~~powershell
$confirmation = @{
  product_id=$offer.product_id
  quantity=$offer.quantity
  offer_token=$offer.offer_token
  confirmed=$true
} | ConvertTo-Json
$result = Invoke-RestMethod -Method Post "$api/api/cart/add" -Headers $headers -ContentType 'application/json' -Body $confirmation
$result.answer
$result.cart_url
Invoke-RestMethod "$api/api/cart" -Headers $headers
~~~

Токен используется один раз. Изменившаяся цена, превышенный остаток, чужая сессия или другое количество отклоняются. Наличие перепроверяется при каждой записи. Остаток не резервируется у партнёра.

В чате простое «Да, добавь» разрешено только для действующего предложения pending_offer, которое создал backend. Старая переписка и ответ LLM не могут выдать согласие. Отрицание, цитата, вопрос или новое количество не изменяют корзину.

У товара 515291 название и свойство тока могут расходиться. При конфликте чат не предлагает автоматическое добавление или аналог; выбор по ID через API возвращает предупреждение для покупателя.

## Загрузка спецификации

~~~powershell
curl.exe -F "file=@C:\path\specification.pdf" http://localhost:8000/api/agent/upload-spec
~~~

Разрешены PDF/TXT/DOCX/XLSX/XLS/JPEG/PNG/WEBP. Файл до 15 МиБ, весь multipart до 16 МиБ, до 250 товарных строк, PDF до 50 страниц / 10 сканов, изображение до 16 Мп. Архивы DOCX/XLSX ограничены размером распаковки и числом записей. Расширение проверяется по содержимому.

Результат содержит matched_items, unmatched_items, ignored_lines, предупреждения и estimate_complete. Неизвестное количество остаётся null; неполная смета не выдаётся за полную. Загрузка не добавляет ничего в корзину.

Для OCR отдельно установите Tesseract и языковые данные rus/eng/kaz, затем задайте TESSERACT_CMD или добавьте executable в PATH. /api/health показывает наличие executable. Качество распознавания зависит от маркировки и изображения; семантического определения модели по внешнему виду нет. Без runtime возвращается ocr_unavailable. Двоичный .doc требует конвертации в .docx.

## Данные и хранение

- EKT API credentials остаются на backend; запросы только GET, Basic Auth по HTTPS.
- Кеш списков — 300 секунд, карточек — 30 секунд по умолчанию. Операция добавления всегда обходит кеш.
- Поиск по названиям/артикулам ограничен настроенными страницами. В ответе есть coverage; отсутствие совпадения не означает отсутствие товара во всём магазине.
- SQLite: хеши идентификаторов сессии, товары корзины, краткоживущие предложения и хеши ссылок чтения. Сессия по умолчанию 24 часа, предложение и ссылка чтения — 10 минут.
- Просроченные записи удаляются при обслуживании сессий. Это не фоновая задача удаления и не криптографическое стирание файла SQLite; для production нужна отдельная политика обслуживания и резервных копий.
- История чата в БД не сохраняется. Если OpenAI включён, ограниченная история и результаты read-only инструментов передаются модели. Очевидные карточные реквизиты отклоняются; не передавайте персональные данные в чат.
- Файлы не передаются модели и не сохраняются приложением. Multipart библиотека может использовать временный файл, который закрывается после обработки.
- URL корзины содержит временный токен только чтения. Сессию и ссылки не публикуйте; стандартный запуск отключает access log с query-параметрами.

## Приёмка

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p "test_*.py" -v
.\.venv\Scripts\python.exe backend/scripts/smoke_live.py
~~~

Автотесты воспроизводимы без сети: синтетический API, временные SQLite и подставной LLM. Проверяются конкурентное подтверждение, replay, изоляция сессий, кеш/сбой API, цена/остаток/упаковка, инструменты, отрицания, PDF/DOCX/XLSX/TXT, ограничения и OCR-ветки.

Live smoke требует реальных EKT credentials. Выполняет только чтение партнёрского API; локальную корзину проверяет во временной базе, которая затем удаляется. Реальная работа модели OpenAI, установленного OCR и нагрузочные характеристики проверяются отдельно.

Полные схемы: [API contract](../docs/api-contract.md). Архитектура: [architecture](../docs/architecture.md).
