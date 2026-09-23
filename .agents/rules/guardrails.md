# 🛡️ Agent Guardrails & Safety Policy (ekt.kz Hackathon)

## Rule 1: Explicit Cart Confirmation (Iron Law)
The agent is STRICTLY PROHIBITED from mutating `CART_STORE` or generating checkout requests unless the customer provided an unambiguous affirmative response in the current or preceding message:
- Valid confirmation phrases: `"да, добавь"`, `"добавляй"`, `"беру"`, `"в корзину"`, `"иә, себетке сал"`, `"қос"`.
- If ambiguous: Ask clarifying question: *"Добавить [Название] ([Количество] шт.) в корзину? (Ответьте 'Да, добавь')*".

## Rule 2: Stock Ceiling Guardrail
The requested quantity in `add_to_cart_confirmed` must NEVER exceed the available warehouse quantity from `ekt.kz` product detail. If the user requests 50 units but only 23 are available, add only 23 and explicitly inform the customer.

## Rule 3: Zero-Stock Analog Mandate
Whenever a queried product has `quantity == 0` (or status unavailable), the agent MUST invoke `find_analogs` and present at least one in-stock alternative with technical reasoning.

## Rule 4: Data Authenticity
Never fabricate product prices, SKUs, or warehouse stock. All figures must strictly originate from `ekt_client.py` live API responses or cached catalog data.
