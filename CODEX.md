# 🤖 CODEX.md — OpenAI Codex Operating System for HackAlem AI

> **Model**: OpenAI Codex / GPT-4o / GPT-4o-mini  
> **Repository**: `C:\Projects\HACKALEMAI\hack-80299a21-nexis`  
> **Team**: NEXIS  
> **Case**: #1 AI Assistant for ekt.kz (ТОО «Электрокомплект»)

---

## 🚀 How to Use Codex in this Project
1. **VS Code Extension**: Open this repository in VS Code with OpenAI Codex extension installed. Codex will automatically read `.codex/config.json` and `.codex/instructions.md`.
2. **Web / App Codex**: Point Codex to this workspace folder or copy prompts from `.codex/prompts/`.
3. **Role-Specific Tasks**:
   - Backend logic: Refer to `.codex/prompts/backend-ai.prompt.md`
   - Frontend UI: Refer to `.codex/prompts/frontend-ui.prompt.md`
   - QA & Testing: Refer to `.codex/prompts/qa-audit.prompt.md`

---

## 🔒 Non-Negotiable Directives for Codex
1. **Work in Current Branch Only**: If working on backend, work in `backend-ai-dev`. If working on frontend, work in `frontend-ui-dev`.
2. **Never Break Contracts**: All requests and responses must match `docs/api-contract.md`.
3. **Always Run Tests**: After any code changes in `backend/`, verify by running:
   ```bash
   python -m unittest discover -s backend/tests -p "test_*.py" -v
   ```
4. **Enforce Cart Guardrail**: Never implement automatic cart additions without explicit user confirmation.
