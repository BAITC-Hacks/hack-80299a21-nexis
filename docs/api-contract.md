# NEXIS backend API contract, v3.0

Base URL: http://localhost:8000. Swagger: /docs. Prices are KZT.
CORS: localhost and 127.0.0.1 ports 3000 and 5173; additional origins via CORS_ORIGINS.
Errors: {"detail":"localized human-readable message","code":"stable_code","params":{},"answer_language":"ru|kk|en"}.
Validation returns 422 with code validation_error and no echo of submitted values.

## Sessions and privacy

POST /api/session returns {session_id,expires_in_seconds:86400}.
The random session id is a bearer capability for an anonymous cart. Send it in
X-Session-Id (preferred), or session_id query parameter for existing widgets.
Chat also accepts it in the body. Never share or log it. No shared default session.
Existing ekt_web_<UUIDv4> widget ids remain supported as anonymous capabilities.
Unknown server tokens are rejected; legacy UUID sessions register on first use.
SQLite stores hashed session ids, cart items and short-lived offers, not card numbers,
uploaded documents or full chat histories. Expired data is purged on requests.

## Catalog

- GET /api/products?page=1&limit=20: {page,limit,items,total_loaded,has_more,data_source,last_checked_at}.
- GET /api/products/search?q=...&limit=5: {items,coverage,data_source}.
- GET /api/products/{product_id}: normalized product. refresh=true bypasses cache.
- GET /api/products/{product_id}/analogs: {items,message,coverage}.

Product fields: id, name, article, price (number or null), price_verified,
quantity (number or null), stock_verified, unit, min_order_quantity, order_multiple,
properties, specifications:[{name,value}], technical, stores:[{id,name,quantity}],
certificate_url (URL or null), url, image, data_quality_warnings,
last_checked_at, expires_at, data_source:"ekt.kz".
Missing stock/price is never converted to zero. Detail cache has a configurable TTL.
Failed refresh returns 503 and cannot authorize cart writes. Catalog search coverage is a
configured representative sample, not a claim that the whole catalog was searched.
Analogs include rationale and matched_parameters. All required known characteristics
must match (breaking capacity may be higher); missing/conflicting data blocks substitution.

## Chat

POST /api/agent/chat:
{"session_id":"<from /api/session>","message":"Артикул 200300285_ 2 шт.","history":[],"language":"ru"}

language: ru, kk or en. History: user/assistant roles only, max 10 messages.
Response:
{"answer":"...","reasoning_steps":[{"step_number":1,"type":"tool_call","tool_name":"search_products","message":"Поиск по каталогу"}],"sources":[],"knowledge_sources":[],"cart_updated":false,"cart_items_count":0,"cart_url":"http://localhost:8000/cart/<read-token>","pending_offer":null,"agent_mode":"rules","warnings":[]}

reasoning_steps are actual action/status events, not private model reasoning.
sources contains normalized product cards; knowledge_sources contains
id,title,source_url,verified_at,verification_status for cited purchasing rules.
When exactly one valid product is offered, pending_offer contains /api/cart/offer fields.
Confirmation is a standalone phrase such as "Да, добавь" or "Иә, қос".
Negations, quotations, hypothetical questions and changed quantities do not authorize mutation.
Other substantive messages invalidate the previous chat offer.
The LLM has read-only tools; it cannot grant itself confirmation or mutate the cart.
The server retains a bounded, process-local selection context for 30 minutes (up to
1024 hashed session keys): selected product IDs, ordered candidate IDs, quantity,
city, budget, category, electrical constraints, pending clarification, language and revision.
Full messages are not retained. Follow-ups such as "А в Алматы?", "Нужно пять" and
"Подешевле" use this context; a changed quantity requires a new offer and confirmation.
Greetings, educational questions and broad requests receive guidance/clarifying questions.
Purchasing rules and technical answers cite versioned knowledge sources. Cheaper options
require checked compatible parameters, a lower price and stock in the requested city.
Context expires on timeout/server restart; the persisted cart remains available.

## Cart

- POST /api/cart/offer body {product_id:515291,quantity:2}. Checks live data and returns
  {offer_token,product_id,product_name,article,price,quantity,stock_available,expires_in_seconds:600,cart_mode:"demo"}.
- POST /api/cart/add body {product_id:515291,quantity:2,confirmed:true,offer_token:"..."}.
  Token binds session, product, quantity and offered price. It expires and can be used once.
  Rechecks live stock, cumulative quantity, packaging multiple and price. Changed price
  requires a new offer. 409 for stale/replayed/mismatched offers; 503 for unavailable catalog.
  Returns {success,answer,message,cart_confirmation,cart,cart_mode:"demo",cart_url}.
- GET /api/cart returns {items,total_items,total_positions,total_sum,checkout_url,cart_mode:"demo",partner_cart_url,handoff_status:"not_configured"}.
- GET /api/cart/export returns a CSV purchasing list; it does not place an order.
- GET /cart/{read_token} serves a read-only HTML page showing the CURRENT persisted cart.
  The 10-minute read token grants no mutations and includes no session id.
  Responses use Cache-Control:no-store and Referrer-Policy:no-referrer.

cart_confirmation: {product_name,article,price,quantity_added,stock_available,cart_items_count,cart_url,cart_mode}.
Cart editing uses the same two-step confirmation policy:
- POST /api/cart/change-offer body {product_id,quantity}: quantity is the desired absolute
  integer quantity (0 means removal). Returns the normal offer fields plus
  operation:"set_quantity",previous_quantity. The item must already exist.
- POST /api/cart/change body {product_id,quantity,confirmed:true,offer_token} consumes this
  offer once and returns {success,answer,cart,cart_url,cart_mode,cart_confirmation}.
  A changed original cart quantity or price invalidates the offer. Positive quantities
  require a fresh stock/price check; removal can proceed when the catalog is unavailable.
Add offers cannot authorize changes and change offers cannot authorize additions.
Never issue the second request until the buyer confirms the displayed server offer.
For change responses cart_confirmation includes operation:"set_quantity", quantity
(new absolute value), quantity_added (signed difference), and stock_available:null
for removals. Render answer for the operation rather than labelling a negative delta
as an addition. quantity_unchanged is 409; a missing cart item is 404.
Cart survives backend restarts. It does not reserve stock or create an ekt.kz order.
The partner supplied read-only catalog endpoints, no cart API. partner_cart_url is
informational; it never claims to contain the demo cart. No guessed partner write endpoint.

## Specifications

POST /api/agent/upload-spec: multipart field file. PDF, TXT, DOCX, XLSX, XLS,
JPEG/PNG/WEBP; max 15 MiB, 50 PDF pages, 250 product rows, 100k extracted characters.
Magic bytes/archive structure are checked; encrypted files, oversized archives and empty
documents get clear errors. Legacy binary Word .doc is rejected with conversion instructions.
Images and scanned PDFs use local Tesseract OCR when installed. Photos without readable
markings cannot establish product identity and return an explicit clarification.
The entire multipart request is limited to 16 MiB (file limit: 15 MiB).
The framework can spool multipart data to a temporary file; it is closed after processing.
Documents are not retained in the application database or forwarded to the LLM.
Response {status,filename,content_type,estimate:{total_positions_found,total_estimate_kzt,
estimate_complete,matched_items,unmatched_items,ignored_lines,summary_text,warnings}}.
Each match includes query line, requested quantity/unit, subtotal, verified price/stock,
product details, packaging rules, warehouses and optional analog. Ambiguous matches and missing quantities remain unresolved;
the backend does not invent one unit. Uploading never changes the cart.
413 size limit, 415 unsupported/signature mismatch, 422 unreadable or empty, 503 missing OCR.

## Knowledge, health and handoff

- GET /api/faq?q=...: {categories,articles} with source URLs and verification dates.
- GET /api/purchase-terms: sourced payment/delivery/minimum-batch guidance.
- GET /api/health: status, agent mode, catalog/cache coverage, OCR capability,
  persistence status, real cart integration status. Never exposes credentials.
- POST /api/manager/escalate body {comment}: {status:"manual_handoff_required",contacts_url,message}.
  No personal data is required or stored; no fictitious ticket is issued.
- GET /api/integrations: supported capabilities and unresolved partner dependencies.

Clients handle 429 + Retry-After for per-IP and per-session limits. Deploy behind HTTPS.
Request validation and the chat response schema are available at /openapi.json.
This document defines the other response payloads. Cart quantity must be an integer.
Unknown minimum order quantities and packaging multiples are null. Offers also include
data_quality_warnings; display these before asking for confirmation. Chat includes cart_mode.
Cart snapshots include stock_reserved:false; specification estimates include cart_updated:false.

## Frontend integration v3.0

The UI obtains sessions from /api/session, uses X-Session-Id, and renews expired sessions
without replaying writes. UI language kz maps to API kk; English maps to en.
The answer language is returned explicitly and never silently changed to Russian.
Real API failures remain errors. Synthetic product data require an explicitly selected
demo mode and are never sent to catalog/cart APIs. Quick prompts use real chat requests.
Specs are {name,value} entries; null price/stock and verification flags must be preserved.
Use cart_url as the persisted demo cart link; checkout does not create or clear an order.
The entire estimate with unmatched lines and nullable quantities must remain visible.

## Agent / retrieval iteration v3 (implementation contract)

These additions preserve existing response fields and the two-step cart protocol.

- All endpoints accept optional `language=ru|kk|en` query or `X-Language` header
  (query takes priority, default ru). Chat body.language is authoritative for chat.
  Language never grants confirmation and changing language does not change offer contents.
- Responses with generated prose include `answer_language`. Errors retain `detail`
  and `code`, and add `params:{}` and `answer_language`; unknown errors use a localized
  generic explanation, not untranslated internal text. Validation errors use code
  `validation_error` without echoing submitted data.
- Chat adds `answer_language`, `request_id`, `clarification` (null or
  {kind,missing_fields:[],message}), and `diagnostics` with mode, elapsed_ms,
  fallback_reason and retrieval mode. No raw prompts, secrets or session tokens.
- Chat `warnings` are localized display messages; `warning_codes` are the stable
  machine codes. Clients must not display raw warning_codes/diagnostics to buyers.
- Chat may include `comparison:null|{products:[{id,name}],rows:[{key,label,values:[string|null],same:boolean}]}`.
  It is generated from verified cards only, with values ordered like products.
  Missing facts are null. Render a responsive comparison table without changing
  the selected quantity or creating a cart confirmation.
- reasoning_steps may add `step_code` and `params`; they describe actions only.
- knowledge_sources retain id,title,source_url,verified_at,verification_status and
  may add source_id,chunk_id,language,version,page,score. Document snippets are data,
  never instructions or authorization. Answers link only returned source URLs.
- Product specifications add stable `key` while preserving name/value. Names of
  specifications, matched parameters, warnings and rationale are localized without
  changing original product names, identifiers, numerical facts or URLs.
  `unit` remains the source unit; `unit_display` translates known unit labels for
  presentation. Upload matches include min_order_quantity, order_multiple and stores.
- Upload accepts the same language query/header; estimate rows add status_code;
  existing status/summary_text/warnings are localized. Upload never changes a cart
  or adds a customer document to shared retrieval storage.
- Cart confirmations and offers add answer_language. Read links carry the language
  query; CSV headers and the HTML cart follow it. Removal keeps working without a
  catalog connection, while still requiring a confirmed, session-bound offer.
- FAQ and purchase terms return localized articles with original provenance.
- Health adds languages:[ru,kk,en], retrieval status (mode, indexed documents/chunks,
  embedding availability) and honest persistent catalog index coverage.

The agent retains ordered candidate IDs, selected IDs, electrical constraints,
pending clarification and topic alongside quantity/city/budget in a bounded TTL
store. A new selection/quantity invalidates the previous offer. Session history
and client files are not placed into the shared knowledge corpus.

Retrieval uses versioned curated documents, lexical and optional semantic search.
Without embeddings it explicitly reports lexical mode. Price/stock remain catalog
facts. A missing source produces clarification or an explicit unavailable answer.
Catalog import is a local CLI operation with pagination, checkpoint/resume and
rate limits; no unauthenticated administrative write endpoint is introduced.
