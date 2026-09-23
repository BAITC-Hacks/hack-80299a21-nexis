# 📜 API Contract — Backend & Frontend (SSOT)

> **Host**: `http://localhost:8000` (or local IP during hackathon)  
> **CORS**: `http://localhost:3000` and `http://localhost:5173`

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
  "sources": [
    {
      "id": 515291,
      "name": "027228 АВ DRX250 MT 3ф 160А 18ka Legrand (1)",
      "article": "200300285_",
      "price": 64920,
      "quantity": 23,
      "stock_verified": true,
      "stores": [{"id": 24, "name": "Нур-Султан", "quantity": 8}],
      "specifications": [{"name": "Количество полюсов", "value": "3"}],
      "certificate_url": null,
      "data_quality_warnings": [],
      "image": "https://ekt.kz/upload/iblock/...",
      "url": "https://ekt.kz/catalog/..."
    }
  ]
}
```

---

## 3. Catalog Products (для витрины сайта)
- **Endpoint**: `GET /api/products?page=1&limit=20`
- **Response**:
```json
{
  "page": 1,
  "total": 80,
  "data_source": "ekt.kz",
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
- **Prepare Offer**: `POST /api/cart/offer?session_id=session_user_123` with `{"product_id":515291,"quantity":2}`. The server checks current product, price, and stock, then returns a one-time `offer_token` bound to this session, product, and quantity for 10 minutes. The UI shows these verified terms and asks for a separate confirmation.
- **Add to Cart**: `POST /api/cart/add?session_id=session_user_123`
- The add request is an explicit confirmation action and must contain the selected catalog product id, requested quantity, `confirmed: true`, and the token from the offer response:
```json
{"product_id": 515291, "quantity": 2, "confirmed": true, "offer_token": "one-time-token"}
```
- The token must match the session, product id, and exact quantity and can be used once. Product name, article, image, price, and availability are re-read from ekt.kz by the backend. A missing live detail returns `503`; a stale/insufficient stock or missing confirmation returns `409`. The session cart is an in-memory demo cart (`cart_mode: "demo"`) and is not synchronized with the ekt.kz account cart.
- A successful response includes `answer` (the verified item name, article, price, quantity, available stock, cart count, and cart URL) and `cart_confirmation` with structured values for the frontend.

## 7. Specification Upload
- **Endpoint**: `POST /api/agent/upload-spec` (`multipart/form-data`, field `file`)
- **Supported formats**: PDF, TXT, DOCX, XLSX, XLS, JPG, JPEG, PNG, WEBP; maximum 15 MB. Image parsing also requires the Tesseract OCR executable with Russian and English language data installed on the backend host.
- **Response**:
```json
{
  "status": "success",
  "filename": "sample.pdf",
  "content_type": "application/pdf",
  "estimate": {
    "total_positions_found": 1,
    "total_estimate_kzt": 64920,
    "matched_items": [],
    "unmatched_items": [],
    "summary_text": "..."
  }
}
```
- The estimate is preliminary. Unmatched lines and unverified stock are reported instead of being treated as available.
