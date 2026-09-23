# 🏛️ NEXIS Architecture & System Design — ekt.kz AI Assistant

> **HackAlem AI 2026** — 5-Hour Sprint  
> **Team**: NEXIS (Frontend Dev & Backend/AI Dev)

---

## 1. System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (Next.js / React)                 │
│  - Interactive Chat Widget with Reasoning Steps Timeline    │
│  - Cart Preview & Direct Checkout Link                     │
│  - Product Cards (Specs, Stock per warehouse, Certificates) │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON REST API (CORS enabled)
┌──────────────────────────────▼──────────────────────────────┐
│                  Backend (Python / FastAPI)                 │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                Agentic AI Controller                  │  │
│  │   (OpenAI GPT-4o-mini / Function Calling Engine)      │  │
│  └───────┬──────────────┬───────────────┬────────────────┘  │
│          │              │               │                   │
│          ▼              ▼               ▼                   │
│   ┌────────────┐ ┌─────────────┐ ┌─────────────┐            │
│   │ Tools:     │ │ Guardrails: │ │  Knowledge  │            │
│   │ - Search   │ │ - Explicit  │ │     Base    │            │
│   │ - Detail   │ │   Cart Add  │ │ (FAQ, Terms,│            │
│   │ - Stock    │ │ - Stock Max │ │  Delivery,  │            │
│   │ - Analogs  │ │ - No PII    │ │  Payment)   │            │
│   └──────┬─────┘ └─────────────┘ └─────────────┘            │
│          │                                                  │
└──────────┼──────────────────────────────────────────────────┘
           ▼
┌─────────────────────────────────────────────────────────────┐
│             Live ekt.kz Catalog & Stores API                │
│  - https://ekt.kz/api/products                              │
│  - https://ekt.kz/api/products/detail?id={id}               │
│  - Basic Auth: apiuser / ApiEkt!2026                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Key Modules & Responsibilities

1. **`backend/services/catalog_service.py`**:
   - Fetches products from `https://ekt.kz/api/products`.
   - Local in-memory / SQLite caching for millisecond response times.
   - Fuzzy search and semantic query resolution (by name, article, characteristics).
   - Analog finder algorithm (matches category `OBYEM`, current, voltage, poles, brand).

2. **`backend/services/agent_service.py`**:
   - OpenAI tool execution loop.
   - Registered Tools:
     - `search_products(query: str, category: Optional[str])`
     - `get_product_detail(product_id: int)`
     - `check_stock(product_id: int, city: Optional[str])`
     - `find_analogs(product_id: int)`
     - `get_purchase_terms(topic: str)` (delivery, payment, MOQ, legal entities)
     - `propose_add_to_cart(product_id: int, quantity: int)`
     - `confirm_add_to_cart(product_id: int, quantity: int)`
   - Emits structured `reasoning_steps` for frontend visualization.

3. **`backend/guardrails.py`**:
   - Explicit confirmation validator: ensures `confirm_add_to_cart` is only executed when user explicitly said yes.
   - Stock validator: ensures `quantity <= available_stock`.

4. **`frontend/`**:
   - Modern Next.js chat interface.
   - Displays real-time reasoning steps badge (Search -> Stock Check -> Reasoning).
   - Product preview card with buy confirmation button.
   - Live cart widget with link to `https://ekt.kz/personal/cart/`.
