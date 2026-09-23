# ChipAI frontend

Vite + TypeScript, with the existing React ChipAI mascot. This version uses backend API v2.1.
The repository root contract is in docs/api-contract.md.

## Local launch

Use Node.js 24 LTS (the tests use native TypeScript stripping):

    cd frontend
    npm ci
    npm run dev -- --host 127.0.0.1

Start the backend on http://localhost:8000 first. Open the URL printed by Vite
(default http://localhost:5173). In the combined Docker setup, run docker compose up
--build from the repository root and open http://localhost:5173.

The default API base is http://localhost:8000/api. To change it, set
VITE_API_BASE_URL in frontend/.env.local, e.g. VITE_API_BASE_URL=/api when the
reverse proxy serves both components under one origin. Never put API passwords or
model keys in VITE_ variables: they are public browser configuration.

## What is connected

- Server-created guest sessions, X-Session-Id, expired-session recovery. Expired
  POST requests are never replayed automatically, including text confirmations.
- Quick prompts and ordinary messages use the real chat endpoint. API failures
  remain visible errors; no synthetic answers, prices, stock or certificates.
- Product cards preserve null price/stock, verification flags, structured specs,
  source documents, warehouses, warnings, URLs and freshness timestamps.
- RU maps to API ru; KZ maps to kk. English interface explicitly explains that
  consultation replies are currently in Russian.
- Addition: /cart/offer -> dialog with current name, article, quantity, price,
  stock and warnings -> explicit confirmation -> /cart/add.
- Change/removal: /cart/change-offer -> the same explicit confirmation ->
  /cart/change. Every change is server-owned; the browser never edits live cart
  quantities locally.
- Text confirmation is sent to the agent. Its actual answer and cart_updated
  state are displayed, then the current server cart is fetched.
- Opening the drawer or saved-cart page refreshes the server snapshot. Opening
  that page does not place an order and does not clear the cart.
- Multipart uploads: PDF, TXT, DOCX, XLSX, XLS, JPEG, PNG and WEBP, up to 15 MiB
  each. Results show all matched and unresolved lines, nullable quantities,
  known estimate portion, warning messages and candidate analogs. Uploading does
  not mutate the cart. OCR availability is determined by the backend.
- Keyboard access, focus handling, native confirmation dialog, responsive widget
  and ChipAI thinking/success states are retained.

The backend cart is a persisted demonstration purchasing list. It does not reserve
stock or create a partner order. The background storefront is an illustrative
layout; product consultation uses only actual API data.

## Checks

    npm test
    npm run typecheck
    npm run build

The unit suite covers session creation/reuse, 401 recovery without write replay,
multipart transport, API errors, language mapping, structured specs and unknown
or unverified values. Browser end-to-end checks are separate.

## Production container

frontend/Dockerfile builds the app and serves dist with nginx on port 80.
Build argument VITE_API_BASE_URL defaults to /api. nginx forwards /api/ and
/cart/ unchanged to backend:8000. The root Compose configuration supplies this
service name. It limits request bodies to 16 MiB and allows up to 180 seconds
for upload/OCR responses. Configure HTTPS at the deployment ingress.
