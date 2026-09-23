# Protocol: Contract Synchronization (ARCH-HACK-01)

## Context
Decouples Frontend and Backend developers during the 5-hour sprint.

## Workflow
1. When a new field or endpoint is needed (e.g. spec upload, city stock filtering):
   - Update `docs/api-contract.md` first.
   - Specify JSON request payload, response schema, and error codes.
2. Backend developer implements FastAPI route and verifies with TestClient.
3. Frontend developer consumes the endpoint using the contract mock before integration.
4. Neither developer modifies endpoint URLs or schemas without updating `docs/api-contract.md`.
