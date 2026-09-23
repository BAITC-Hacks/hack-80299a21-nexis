# ChipAI frontend

Vite + TypeScript, with the existing React ChipAI mascot. This version uses backend API v3.0.
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
- RU maps to API `ru`, KZ to `kk`, EN to `en`. The same selected language is sent
  in `X-Language` on every API call, including sessions, uploads and cart operations;
  chat also sends the authoritative `language` body field. English is never changed
  to Russian. Legacy saved `kz` and canonical `kk` preferences are both recognized.
- Language switching preserves the private session, selected products, entered
  quantities and pending confirmation offer. It does not issue a cart mutation or
  extend an offer's expiration. Product names, articles, numerical facts and URLs
  retain their source values; stable specification `key` fields localize labels.
  `unit_display` provides a translated unit label while the original `unit` is
  preserved. Unknown packaging rules remain null; the positive integer input floor
  does not assert a known minimum order, and the server validates every offer.
- Chat displays cited `knowledge_sources` with source links, page numbers and
  verification dates where provided. Additional `clarification.message` is shown
  when it is not already in the answer. Source HTML is escaped, links are checked
  and duplicate chunks from the same source/page are collapsed.
- Optional `comparison` responses display a horizontally scrollable table of
  verified product facts, using the server's localized parameter labels. Same,
  different and insufficient-data indicators are translated; null values remain
  unknown. All cell content uses text nodes. Comparing products adds no cart actions.
- `answer_language` marks the returned message language; `request_id` is retained
  as the message element's `data-request-id` for support. Raw diagnostics, model
  traces and tool JSON are not displayed in customer messages. The timeline shows
  actual backend action messages and localized fallbacks.
- Interface, network errors, confirmations and client validation have RU/KK/EN
  copy. v3 errors use the localized `detail`, stable `code` and `params`; older
  foreign-language errors use a localized code fallback. Upload summaries/statuses
  and product rationale are localized by the backend. Previous conversation text
  remains in the language in which the response was received.
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

The unit suite (41 cases) covers session creation/reuse, 401 recovery without write
replay, multipart transport, API errors, all-language headers, language switching
without a new session, keyed specifications, preserved facts, source/clarification
rendering, comparison tables, escaped content and unknown or unverified values. Browser end-to-end
checks are separate; unit results do not establish model answer quality.

## Production container

frontend/Dockerfile builds the app and serves dist with nginx on port 80.
Build argument VITE_API_BASE_URL defaults to /api. nginx forwards /api/ and
/cart/ unchanged to backend:8000. The root Compose configuration supplies this
service name. It limits request bodies to 16 MiB and allows up to 180 seconds
for upload/OCR responses. Configure HTTPS at the deployment ingress.
