# ⚡ HACKALEM AI 2026 — NEXIS AGENT OPERATING INSTRUCTIONS

> **Context**: HackAlem AI Hackathon (Astana, 23 Sep 2026)  
> **Team**: NEXIS (2 Developers: Frontend UI + Backend AI)  
> **Case**: #1 AI-Consultant and Chat Assistant for ekt.kz (ТОО «Электрокомплект»)  
> **Duration**: 5-Hour Sprint (13:00 - 18:00)  
> **Evaluation**: Code-only assessment (NO PITCH). Functionality, clean API, working demo, and repo quality are 100% of the score.

---

## 🛑 Strict Engineering Directives

1. **Simplicity & Speed First**: Write production-ready, minimal, working code. Zero over-engineering, zero bloated abstractions.
2. **CORS & Integration**: All backend APIs must allow CORS from frontend (`http://localhost:3000`, `http://localhost:5173`).
3. **Single Source of Truth**: All API payload structures MUST be documented in `docs/api-contract.md` before coding endpoints.
4. **Git Discipline**: Every 45-60 minutes, produce a clean, atomic commit in the active branch:
   - Backend work strictly in `backend-ai-dev` (folders: `backend/`, `database/`, `docs/`, `.agents/`, `.codex/`).
   - Frontend work strictly in `frontend-ui-dev` (folder: `frontend/`).
   - NEVER commit or merge directly into `main` until final sign-off at 17:30.
5. **Agent Architecture & Guardrails (ekt.kz Case Requirements)**:
   - The agent MUST use **Function Calling (Tools)** to query catalog, prices, specs, and stock levels.
   - The agent MUST have a **RAG pipeline** / smart search across products and purchasing rules.
   - **CRITICAL GUARDRAIL**: The agent MUST NEVER add items to the cart or place orders without explicit user confirmation ("Да, добавь в корзину").
   - **STOCK GUARDRAIL**: The requested quantity must NEVER exceed available stock.
   - **ANALOG FINDER**: When an item has 0 stock, the agent MUST propose relevant alternatives with clear rationale.
   - **REASONING STEPS**: The backend API must return reasoning steps (`reasoning_steps: [...]`) so the UI can display real-time timeline/status pills.

---

## 🤖 Multi-Agent Topology (.agents/agents/)
- **`system_architect`**: API contracts, data schemas, and endpoint alignment.
- **`backend_engineer`**: FastAPI, ekt.kz live API client, caching, and unit tests.
- **`frontend_engineer`**: Responsive UI, chat stream, reasoning pills, and cart integration.
- **`qa_lead`**: Test suite execution, edge-case validation, and jury scenario verification.
- **`ekt_consultant`**: Domain logic, electrical specs, cross-sell recommendations, and Kazakh language.

---

## ⚡ Fast Commands
- **Run Backend**: `cd backend && python main.py` (Port 8000, Swagger UI at `/docs`)
- **Run Frontend**: `cd frontend && python -m http.server 3000` (Port 3000)
- **Run Tests**: `python -m unittest discover -s backend/tests -p "test_*.py" -v`
