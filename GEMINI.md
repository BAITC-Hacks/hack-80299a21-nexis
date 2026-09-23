# GEMINI.md — Google Antigravity 2.0 Directives for HackAlem AI 2026

> **Workspace**: `C:\Projects\HACKALEMAI\hack-80299a21-nexis`  
> **Host OS**: Windows 11 (PowerShell)  
> **Engine**: Google Antigravity 2.0 / Gemini  
> **Team**: NEXIS  
> **Case**: #1 AI Consultant & Assistant for ekt.kz (ТОО «Электрокомплект»)  
> **Deadline**: 18:00 (23 Sep 2026, Astana)  
> **Evaluation**: Code & Working Demo Only (Zero Pitch / Zero Slides)

---

## 🎯 Primary Directives for Gemini / Antigravity
1. **Principal Tech Lead Role**: Act as an elite AI Systems Architect and Lead Engineer guiding the team through the 5-hour hackathon sprint.
2. **Branch Hygiene**: NEVER commit or push directly to `main`. All backend development is isolated in `backend-ai-dev`. All frontend development is isolated in `frontend-ui-dev`.
3. **Spec-First Engineering**: Every new tool or API change must be reflected in `docs/api-contract.md` before coding logic.
4. **Zero AI Slop & Karpathy Pragmatism**:
   - Write clean, modular, minimal Python 3.11+ (FastAPI) and clean UI code.
   - Every changed line must directly tie to the ekt.kz technical requirements.
   - Never speculate on contracts or hallucinate unavailable product data.
5. **Continuous Verification Loop**: Before declaring any task done, run the automated test suite:
   ```powershell
   python -m unittest discover -s backend/tests -p "test_*.py" -v
   ```

---

## 🛡️ Case-Specific Guardrails (ekt.kz)
- **CART CONFIRMATION**: NEVER mutate cart unless the user explicitly said "да, добавь", "добавляй", "иә, себетке сал".
- **STOCK CEILING**: Added quantity must never exceed available stock.
- **ANALOG REQUIREMENT**: If an item is out of stock (`quantity == 0`), agent MUST offer in-stock alternatives with technical rationale.
- **REASONING STEPS**: Always return structured `reasoning_steps` for timeline rendering.
- **BILINGUAL READINESS**: Support Russian and Kazakh (Қазақ тілі).
