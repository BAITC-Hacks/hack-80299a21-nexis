# 🏆 NEXIS — ИИ-ассистент консультант для сайта ekt.kz (ТОО «Электрокомплект»)

> **HackAlem AI 2026** (Астана, 23 сентября 2026 г.)  
> **Команда**: NEXIS  
> **Кейс**: №1 «ИИ-ассистент для чата на сайте ekt.kz»

---

## 🎯 О решении

Интеллектуальный Agentic AI ассистент для интернет-магазина электротехнической продукции [ekt.kz](https://ekt.kz):
- **Онлайн-консультация по каталогу**: технические характеристики, сертификаты, остатки по региональным складам (Нур-Султан, Алматы, Шымкент, Караганда и др.).
- **Подбор релевантных аналогов**: при нулевом остатке агент мгновенно находит аналоги по техническим параметрам (ток, напряжение, полюса, назначение) с четким обоснованием.
- **Ответы на условия покупки**: способы оплаты, доставка по городам РК, минимальные партии и работа с юр. лицами.
- **Безопасная корзина с подтверждением**: добавление позиций в корзину осуществляется **строго после явного подтверждения** («Да, добавь»), с контролем складских остатков.
- **Прозрачность работы (Reasoning Timeline)**: визуализация каждого шага агента (поиск в каталоге, проверка остатков, вызов инструментов).

---

## 🚀 Быстрый запуск

### 1. Бэкенд и AI-Агент (Python 3.10+ / FastAPI)

```bash
cd backend

# Настройка виртуального окружения
python -m venv venv

# Активация (Windows):
.\venv\Scripts\activate
# Активация (Linux / MacOS):
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
copy ..\.env.example .env

# Запуск API сервера
uvicorn main:app --reload --port 8000
```
- Документация Swagger/OpenAPI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Проверка здоровья API: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 2. Фронтенд (UI)

```bash
cd frontend
npm install # или pnpm install
npm run dev
```
- Интерфейс доступен по адресу: [http://localhost:3000](http://localhost:3000)

---

## 🏗️ Архитектура и технологии

- **Backend**: Python 3.12+, FastAPI, OpenAI Function Calling / Tool Calling, Pydantic V2, HTTPX.
- **Data Integration**: Прямая интеграция с live API ekt.kz (`https://ekt.kz/api/products`, `https://ekt.kz/api/products/detail`).
- **Frontend**: Next.js / React, Tailwind CSS, Lucide Icons.
- **Документация контрактов**: Спецификация API доступна в [`docs/api-contract.md`](docs/api-contract.md), архитектура в [`docs/architecture.md`](docs/architecture.md).
