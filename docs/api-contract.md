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

## 2. Agent Chat & Execution (Core)
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
  "answer": "Автоматический выключатель Legrand DRX250 160А есть в наличии...",
  "reasoning_steps": [
    {
      "step_number": 1,
      "type": "thought | tool_call | tool_result",
      "tool_name": "search_products",
      "message": "Поиск в онлайн-каталоге ekt.kz..."
    }
  ],
  "cart_updated": false,
  "cart_items_count": 0,
  "cart_url": "https://ekt.kz/personal/cart/",
  "sources": []
}
```

---

## 3. Catalog Products (для витрины сайта)
- **Endpoint**: `GET /api/products?page=1&limit=20`
- **Response**:
```json
{
  "page": 1,
  "total": 40,
  "items": [
    {
      "id": 515291,
      "name": "027228 АВ DRX250 MT 3ф 160А 18ka Legrand",
      "article": "200300285_",
      "price": 64920,
      "quantity": 23,
      "image": "https://ekt.kz/upload/iblock/...",
      "url": "https://ekt.kz/catalog/..."
    }
  ]
}
```

---

## 4. FAQ & Knowledge Base Endpoints
- **Endpoint**: `GET /api/faq`
- **Response**:
```json
{
  "categories": [
    {"id": "b2b", "title": "Юридическим лицам (Счета с НДС 12%, ЭСФ)"},
    {"id": "b2c", "title": "Оплата (Kaspi QR, Карты, Наличные)"},
    {"id": "delivery", "title": "Доставка и самовывоз по Казахстану"},
    {"id": "registration", "title": "Регистрация (Физлица и Компании по БИН)"},
    {"id": "certificates", "title": "Сертификаты соответствия ТР ТС"}
  ]
}
```

---

## 5. Escalation to Human Manager
- **Endpoint**: `POST /api/manager/escalate`
- **Request**:
```json
{
  "client_name": "Ерлан",
  "phone": "+7 777 123 45 67",
  "comment": "Запрос КП на щитовое оборудование 10 млн тенге",
  "session_id": "session_user_123"
}
```
- **Response**:
```json
{
  "status": "success",
  "ticket_id": "TICK-EKT-8492",
  "message": "Заявка успешно передана дежурному инженеру ekt.kz. С вами свяжутся в течение 10 минут.",
  "manager_whatsapp_url": "https://wa.me/77001234567?text=Здравствуйте!%20Мой%20тикет%20TICK-EKT-8492"
}
```

---

## 6. Cart Endpoints
- **Get Cart**: `GET /api/cart?session_id=session_user_123`
- **Add to Cart**: `POST /api/cart/add?session_id=session_user_123`
