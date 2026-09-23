# Frontend — ekt.kz AI Chat UI

## Быстрый старт (2 варианта):

### Вариант 1: Мгновенный запуск без сборщиков
Просто откройте `index.html` в браузере или запустите легкий HTTP-сервер:
```bash
# Из папки frontend:
python -m http.server 3000
```
И откройте `http://localhost:3000`.

### Вариант 2: Для React / Next.js разработки
Интерфейс уже подключен к эндпоинтам FastAPI:
- `GET http://localhost:8000/api/health` — проверка статуса
- `POST http://localhost:8000/api/agent/chat` — основной чат с агентом (возвращает `answer`, `reasoning_steps`, `cart_updated`, `cart_url`)
- `GET http://localhost:8000/api/cart` — актуальное состояние корзины

Все CORS-заголовки на бэкенде включены (`allow_origins=["*"]`).
