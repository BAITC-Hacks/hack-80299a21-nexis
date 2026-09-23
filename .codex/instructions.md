# OpenAI Codex Operating Instructions — HackAlem AI 2026

## 🎯 Project Overview
- **Team**: NEXIS
- **Case**: AI Consultant & Assistant for ekt.kz (ТОО «Электрокомплект»)
- **Goal**: Production-grade Agentic AI with Tool Calling & RAG over ekt.kz electrical catalog
- **Evaluation**: 100% Code & Live Demo (Zero Pitch / Zero Slides)

---

## 🏗️ Architecture & Stack
- **Backend**: Python 3.11+, FastAPI, Uvicorn, Pydantic v2, HTTPX / Requests
- **Agent**: OpenAI Function Calling (Tools) with structured JSON reasoning trace
- **Frontend**: Vite / React 19 or Next.js, Tailwind CSS, Lucide icons
- **Data Source**: Live ekt.kz Partner API with Basic Auth (credentials from environment variables)
  - List: `https://ekt.kz/api/products?page={page}`
  - Detail: `https://ekt.kz/api/products/detail?id={id}`

---

## 🛡️ Critical Guardrails (Mandatory Hackathon Rules)
1. **NO CART MUTATION WITHOUT CONFIRMATION**:
   - The agent MUST NEVER add items to the cart or modify cart state unless the customer explicitly confirmed with "да, добавь", "добавляй", "иә, себетке сал".
   - Before adding, the agent must ask: *"Добавить [Название товара] ([Количество] шт.) в корзину?"*.
2. **STOCK LIMIT GUARDRAIL**:
   - Cart quantity must never exceed available stock (`quantity` in `detail` API).
3. **ANALOG RECOMMENDATION (0 STOCK)**:
   - If an item is out of stock (`quantity == 0`), agent MUST propose at least 1 relevant analog with brief technical reasoning (e.g. same amperage, voltage, pole count, manufacturer).
4. **REASONING STEPS**:
   - Every response must include `reasoning_steps: [{"step_number": 1, "type": "thought|tool_call|tool_result", "message": "..."}]` for visual status in the UI.
5. **KAZAKH LANGUAGE (OPTIONAL BONUS)**:
   - If user asks in Kazakh (Қазақ тілі), respond natively in Kazakh.

---

## 📂 Git Branch Conventions
- `backend-ai-dev`: backend/, database/, docs/
- `frontend-ui-dev`: frontend/
- Merge to `main` at 17:30 before final submission.
