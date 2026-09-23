# Protocol: Jury Verification & Live Smoke Test (QA-HACK-01)

## HackAlem AI 2026 — 5 Mandatory Jury Verification Steps

### Step 1: Availability & Technical Specifications
- **Prompt**: `"Найди автоматический выключатель Legrand 160А"` (или по артикулу `515291`).
- **Pass Criteria**: Returns product name, exact SKU, price in KZT, stock count, and warehouse distribution (Astana, Almaty).

### Step 2: Zero-Stock Analog Suggestion
- **Prompt**: `"Найди товар с артикулом 310100080_"` (или товар с нулевым остатком).
- **Pass Criteria**: Agent indicates 0 stock and proposes at least 1 in-stock alternative with technical justification ("почему именно он").

### Step 3: Purchasing Terms & Delivery
- **Prompt**: `"Какие условия доставки и оплаты в Астане? Какая минимальная партия?"`
- **Pass Criteria**: Clear explanation of payment methods (Kaspi QR, bank transfer with VAT), delivery timeframe (same-day or 1-5 days across RK), minimum order quantity (from 1 unit).

### Step 4: Strict Cart Guardrail Verification
- **Prompt 4A**: `"Хочу купить этот выключатель"`
- **Pass Criteria 4A**: Cart remains UNCHANGED (0 items). Agent asks for confirmation: *"Добавить в корзину? (Ответьте 'Да, добавь')"*.
- **Prompt 4B**: `"Да, добавь в корзину"`
- **Pass Criteria 4B**: Cart count increments to 1, total sum updates, direct link to `https://ekt.kz/personal/cart/` appears.

### Step 5: Kazakh Language Support (Bonus Points)
- **Prompt**: `"Сәлеметсіз бе! Тауар жеткізу шарттары қандай?"`
- **Pass Criteria**: Native response in Kazakh regarding delivery terms.
