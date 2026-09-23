# NEXIS Product Improvement Plan

Implementation order for the HackAlem AI ekt.kz case. The plan follows the case acceptance criteria and uses the supplied ekt.kz API sample as the catalog schema reference.

## P0 — trustworthy product data and cart safety

- Load ekt.kz Basic Auth only from local environment settings; never commit credentials.
- Parse catalog pagination from `page`, `per_page`, `count`, and `items`; search by exact id/article before fuzzy name matching.
- Remove fabricated stock and random-product fallbacks. Report unavailable data as unavailable.
- Normalize product properties, warehouse stock, certificates, and product links into the API response.
- Enforce explicit confirmation, authoritative product/price lookup, and aggregate stock limits on every server cart mutation.
- Store a chat offer per session so a plain confirmation cannot add an unrelated hard-coded product.
- Return the verified add-to-cart summary from the backend and render it in chat after successful button confirmation.

## P1 — complete the main buyer journey

- Return structured product cards and analogs from chat alongside reasoning steps.
- Find analogs by electrical characteristics and return only candidates whose stock was verified as positive.
- Connect frontend file uploads to the backend specification parser; validate size and file type server-side.
- Parse PDF, text, DOCX, and XLSX specifications; report unmatched lines and insufficient stock without overstating availability.
- Keep the demo cart visibly separate from the real ekt.kz cart until an official cart handoff API is available.

## P2 — polish and acceptance review

- Synchronize the API contract, README, and frontend integration notes with actual routes and schemas.
- Restrict CORS to the two local frontend origins used during development.
- Review every Must Have scenario: real article lookup, zero-stock analog, purchase terms, rejected unconfirmed cart writes, quantity caps, cart URL, and uploaded specification.
- Check Russian/Kazakh response language and graceful behavior when the live catalog or LLM is unavailable.

## Acceptance limits

- A catalog or stock API failure must never be presented as a verified price or quantity.
- A cart write must use catalog data and cannot exceed current stock, including items already in the session cart.
- A file upload produces a price estimate only for confidently matched lines; all other lines remain for clarification.
- The external checkout URL is informational unless an official ekt.kz cart integration is configured.
