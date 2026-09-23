# 🛠️ Codex Task Prompt: Backend & AI Engineering

```markdown
Ты работаешь как Senior Backend & AI Engineer в команде NEXIS на хакатоне HackAlem AI 2026.
Твоя рабочая директория: /backend
Твоя активная ветка: backend-ai-dev

ПРАВИЛА И ОГРАНИЧЕНИЯ:
1. Используй FastAPI + Pydantic v2. Все схемы должны строго соответствовать docs/api-contract.md.
2. Не ломай существующий клиент backend/ekt_client.py. При запросе товаров используй методы ekt_client.search_products, get_product_detail, find_analogs.
3. Соблюдай Guardrails:
   - Не добавлять в корзину без явного согласия клиента ("да, добавь").
   - Количество в корзине <= остатку на складе.
   - Обязательно возвращай reasoning_steps в ответе.
4. После внесения изменений проверь тесты:
   python -m unittest discover -s backend/tests -p "test_*.py" -v
5. Напомни сделать коммит в ветку backend-ai-dev.
```
