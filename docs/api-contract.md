# 📜 API Contract — Backend & Frontend (SSOT)

> **Host**: `http://localhost:8000` (or local IP during hackathon)  
> **CORS**: Enabled for all origins (`*`)

---

## 1. Healthcheck

- **Endpoint**: `GET /api/health`
- **Response**:
```json
{
  "status": "online",
  "service": "ekt.kz Agentic AI Backend",
  "team": "NEXIS",
  "agent_ready": true,
  "version": "1.0.0"
}
```

---

## 2. Agent Chat & Execution

- **Endpoint**: `POST /api/agent/chat`
- **Request**:
```json
{
  "message": "Есть ли в наличии автомат Legrand 160А и сколько стоит?",
  "session_id": "session_user_123",
  "history": [
    {"role": "user", "content": "Привет"},
    {"role": "assistant", "content": "Здравствуйте! Чем могу помочь?"}
  ],
  "language": "ru"
}
```

- **Response**:
```json
{
  "answer": "Автоматический выключатель Legrand DRX250 160А (арт. 200300285_) есть в наличии: 23 шт. по цене 64 920 ₸. В наличии на складах: Нур-Султан (8 шт.), Алматы (5 шт.), Атырау (3 шт.), Караганда (2 шт.), Тараз (2 шт.), Шымкент (3 шт.). Желаете добавить в корзину?",
  "reasoning_steps": [
    {
      "step_number": 1,
      "type": "tool_call",
      "tool_name": "search_products",
      "tool_input": {"query": "Legrand 160А"},
      "tool_output": "Найдено 1 совпадение: id=515291, 027228 АВ DRX250 MT 3ф 160А"
    },
    {
      "step_number": 2,
      "type": "tool_call",
      "tool_name": "check_stock",
      "tool_input": {"product_id": 515291},
      "tool_output": "В наличии 23 шт. на 6 складах"
    }
  ],
  "cart_updated": false,
  "cart_items_count": 0,
  "cart_url": null,
  "sources": [
    {
      "id": 515291,
      "name": "027228 АВ DRX250 MT 3ф 160А 18ka Legrand (1)",
      "article": "200300285_",
      "price": 64920,
      "quantity": 23,
      "image": "https://ekt.kz/upload/iblock/c39/.../Legrand.jpg",
      "url": "https://ekt.kz/catalog/..."
    }
  ]
}
```

---

## 3. Cart Endpoints

### Get Cart
- **Endpoint**: `GET /api/cart?session_id=session_user_123`
- **Response**:
```json
{
  "session_id": "session_user_123",
  "items": [
    {
      "product_id": 515291,
      "article": "200300285_",
      "name": "027228 АВ DRX250 MT 3ф 160А",
      "price": 64920,
      "quantity": 2,
      "image": "https://ekt.kz/..."
    }
  ],
  "total_items": 1,
  "total_sum": 129840,
  "checkout_url": "https://ekt.kz/personal/cart/"
}
```

### Add to Cart (Manual / Frontend Fallback)
- **Endpoint**: `POST /api/cart/add?session_id=session_user_123`
- **Request**:
```json
{
  "product_id": 515291,
  "article": "200300285_",
  "name": "027228 АВ DRX250 MT 3ф 160А",
  "price": 64920,
  "quantity": 2,
  "image": "https://ekt.kz/..."
}
```
