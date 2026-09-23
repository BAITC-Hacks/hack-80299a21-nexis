# Backend NEXIS — API v2.1

FastAPI, клиент ekt.kz, AgentService, обработка документов и SQLite-корзина. Все команды ниже выполняются из корня репозитория.

## Запуск

Для общего запуска с frontend и OCR используйте [Docker-инструкцию](../docs/docker-setup.md):

~~~powershell
if (!(Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
# Заполните EKT_API_USER и EKT_API_PASS, сохранив существующие настройки.
docker compose up --build -d
~~~

Для разработки на Windows: Python 3.14, Node.js 24.

~~~powershell
python backend/scripts/dev.py --install
# Последующие запуски:
python backend/scripts/dev.py
~~~

Флаг --install подготавливает .venv, устанавливает Python/npm зависимости и запускает оба сервера. Ctrl+C завершает дочерние процессы. Для отдельных портов доступны --api-port и --ui-port.

Backend отдельно после установки зависимостей:

~~~powershell
.\.venv\Scripts\python.exe backend/main.py
~~~

На Linux путь Python — .venv/bin/python. .env загружается из корня репозитория независимо от текущего каталога.

- Swagger: http://localhost:8000/docs
- Состояние: http://localhost:8000/api/health
- Интеграции: http://localhost:8000/api/integrations

Нативный сервер слушает 127.0.0.1; Docker задаёт HOST=0.0.0.0 внутри контейнера и публикует порт на localhost. Локальная SQLite создаётся в database/nexis.sqlite3, контейнерная — в /data/nexis.sqlite3 на volume.

## Сессия и консультация

Сессия — случайный секретный идентификатор гостевой корзины, а не учётная запись покупателя. Получите его через /api/session, передавайте в X-Session-Id; для чата он также требуется в JSON.

~~~powershell
$api = 'http://localhost:8000'
$session = Invoke-RestMethod -Method Post "$api/api/session"
$headers = @{ 'X-Session-Id' = $session.session_id }
$body = @{
  session_id=$session.session_id
  message='515291'
  history=@()
  language='ru'
} | ConvertTo-Json
$reply = Invoke-RestMethod -Method Post "$api/api/agent/chat" -Headers $headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
$reply.answer
$reply.sources
~~~

Языки API: ru и kk. Интерфейс KZ отправляет kk; EN пока использует русскую консультацию с видимым пояснением.

AgentService умеет приветствовать, уточнять неполный запрос и продолжать выбор словами «а в Алматы», «нужно 5 шт.», «подешевле». Для этого он хранит product_id, quantity, city, budget и family в RAM: до 30 минут с последнего обновления и до 1024 сессий. Сообщения и файлы в этот контекст не записываются. Перезапуск или истечение контекста потребуют выбрать товар снова.

При наличии OPENAI_API_KEY модель выбирает инструменты чтения. При отсутствии/ошибке модели используются программные правила с тем же каталогом. В текущем проверенном окружении ключ не настроен; реальный вызов модели не включён в результаты приёмки.

## Добавление после подтверждения

Первый запрос проверяет данные и возвращает предложение; корзина не меняется:

~~~powershell
$selection = @{ product_id=515291; quantity=1 } | ConvertTo-Json
$offer = Invoke-RestMethod -Method Post "$api/api/cart/offer" -Headers $headers -ContentType 'application/json' -Body $selection
$offer
~~~

Покажите покупателю товар, артикул, количество, цену и предупреждения. Только после его согласия:

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
~~~

Токен связан с сессией, ID, количеством, ценой и операцией. При подтверждении сервер снова читает карточку, проверяет совокупное количество и потребляет токен в транзакции. Повтор, другая сессия или изменившаяся цена отклоняются.

Текст «Да, добавь» или «Иә, қос» разрешает добавление только для действующего chat-предложения. История, цитата, отрицание и вопрос не выдают согласие. Изменение количества в диалоге требует нового предложения.

## Изменение и удаление

| Действие | Подготовка | Подтверждение |
| --- | --- | --- |
| Добавить количество к имеющемуся | POST /api/cart/offer | POST /api/cart/add |
| Установить новое общее количество | POST /api/cart/change-offer | POST /api/cart/change |
| Удалить позицию | change-offer с quantity:0 | change с quantity:0 |

Обе пары принимают product_id и quantity; запрос подтверждения дополнительно принимает confirmed:true и offer_token. Для изменения quantity — итоговое количество, не приращение. Предложение содержит operation:set_quantity и previous_quantity.

Сервер отклоняет устаревшее предложение, если исходная корзина уже изменилась. Для положительного количества снова проверяются цена и остаток. Удаление локальной позиции разрешено при недоступном каталоге, но также требует подтверждения. Токены разных операций невзаимозаменяемы.

GET /api/cart возвращает текущее состояние и checkout_url. GET /api/cart/export формирует CSV. Ссылка /cart/<read_token> показывает актуальную сохранённую корзину и действует 10 минут. Просмотр не очищает корзину и не создаёт заказ.

## Документы и OCR

~~~powershell
curl.exe -F "file=@C:\path\specification.pdf" http://localhost:8000/api/agent/upload-spec
~~~

Поддерживаются PDF/TXT/DOCX/XLSX/XLS/JPEG/PNG/WEBP. Ограничения: файл 15 МиБ, multipart 16 МиБ, 250 товарных строк, 100 тысяч извлечённых символов, PDF 50 страниц и до 10 сканов, изображение до 16 Мп. Формат проверяется по содержимому; архивы ограничены размером распаковки.

Результат содержит matched_items, unmatched_items, ignored_lines, предупреждения и estimate_complete. Неизвестные количества остаются null. Неполная смета показывает известную часть суммы; загрузка никогда не изменяет корзину.

Docker содержит Tesseract и eng/rus/kaz. Нативный запуск требует отдельной установки движка и языковых данных, затем настройки TESSERACT_CMD или PATH. /api/health проверяет executable; doctor дополнительно проверяет языки и реальное распознавание:

~~~powershell
.\.venv\Scripts\python.exe backend/scripts/doctor.py
docker compose run --rm --no-deps backend python backend/scripts/doctor.py --require-ocr --ocr-smoke
~~~

Без движка фото/скан возвращает ocr_unavailable. Качество зависит от читаемости маркировки; распознавание товара только по внешнему виду не реализовано. Старый .doc нужно сохранить как .docx.

## Данные, защита и эксплуатация

- Credentials ekt.kz/OpenAI остаются на backend. Партнёрские запросы — только GET по HTTPS с Basic Auth.
- Кеш страниц — 300 секунд, деталей — 30 секунд по умолчанию. Изменения корзины с положительным количеством проверяют свежие данные.
- Поиск по названию/артикулу ограничен EKT_CATALOG_PAGES, по умолчанию 4, максимум 50. Прямой числовой ID доступен за пределами выборки. Coverage описывает фактическое покрытие.
- SQLite хранит хеши сессий, позиции, предложения и хеши ссылок чтения. Сессия по умолчанию 24 часа, предложение/ссылка — 10 минут. Просроченные данные очищаются при запросах; фоновой политики удаления нет.
- Полная история не сохраняется в БД. В браузере для API ограничивается последними 10 сообщениями. При включённой модели ограниченная история и результаты инструментов передаются OpenAI.
- Файлы не сохраняются приложением и не передаются модели; multipart может использовать временный файл, который закрывается после обработки.
- Явные платёжные реквизиты отклоняются. Гостевая сессия и ссылки корзины дают доступ владельцу токена, поэтому их нельзя публиковать.
- CORS разрешает localhost/127.0.0.1 на 3000/5173; дополнительные адреса задаются CORS_ORIGINS.
- Контекст, кеш и rate limiter локальны одному процессу. Для нескольких воркеров нужны общее состояние/лимиты и проверка нагрузки. Внешний reverse proxy должен корректно ограничивать запросы; произвольному X-Forwarded-For backend не доверяет.

Корзина не резервирует остатки ekt.kz и не передаёт заказ партнёру. CRM отвечает ссылкой на контакты без фиктивной заявки. Для настоящего оформления и эскалации нужны официальные контракты партнёра.

## Проверки

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend/tests -p "test_*.py" -v
.\.venv\Scripts\python.exe backend/scripts/smoke_live.py
~~~

На 23 сентября 2026: 81 backend-тестов прошли в Windows/Python 3.14.6 и Docker/Linux/Python 3.14.7. В контейнере также прошли настоящий OCR на сгенерированном изображении и HTTP-запуск.

Тесты используют синтетический транспорт и временные SQLite. Live smoke отдельно читает настоящий API с .env и проверяет только временную локальную корзину; записей у партнёра нет. Основные браузерные сценарии прошли; работа настоящей модели, нагрузка и мобильное устройство требуют отдельной оценки.

[Контракт API](../docs/api-contract.md) · [Архитектура](../docs/architecture.md) · [План и приёмка](../docs/integration-plan.md)
