# Protocol: Backend-to-Frontend Data Contract (ARCH-HACK-02)

## Chat Endpoint: `POST /api/agent/chat`

### Request Schema
```json
{
  "message": "Найди автоматический выключатель Legrand",
  "session_id": "default_session",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "language": "ru"
}
```

### Response Schema
```json
{
  "answer": "Подробный ответ консультанта с ценами и артикулами",
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

### UI Requirements
1. Render `reasoning_steps` as an expandable pill or timeline above the assistant message.
2. If `cart_updated == true`, trigger `GET /api/cart` to refresh the header cart badge and total amount.
3. If `cart_url` is provided, display an emerald checkout button linking directly to ekt.kz cart.
