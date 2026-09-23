"""FastAPI backend for the EKT hackathon prototype."""
import csv
import hashlib
import html
import io
import os
import time
import uuid
from collections import OrderedDict, deque
from typing import Any, Literal

from fastapi import Depends, FastAPI, File, Header, Path, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool
from starlette.concurrency import run_in_threadpool

from agent_service import AgentService, agent_service
from cart_service import CartService
from ekt_client import ekt_client
from knowledge_base import CONTACTS_URL, KB_ARTICLES, purchase_terms, search_knowledge_base
import knowledge_base
from localization import (LANGUAGES, normalize_language, tr, localize_error, localize_product,
                          localize_cart_result, localize_estimate, localized_url, category_title)
from settings import ServiceError, env_int
from spec_parser import MAX_BYTES, SpecificationParser, ocr_available


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatMessage(Payload):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(Payload):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=36, max_length=128)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)
    language: Literal["ru", "kk", "en"] = "ru"


class ChatResponse(BaseModel):
    answer: str
    answer_language: Literal["ru", "kk", "en"] = "ru"
    request_id: str = ""
    clarification: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    reasoning_steps: list[dict[str, Any]]
    sources: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_sources: list[dict[str, Any]] = Field(default_factory=list)
    cart_updated: bool = False
    cart_items_count: int = 0
    cart_url: str | None = None
    pending_offer: dict[str, Any] | None = None
    agent_mode: str
    warnings: list[str] = Field(default_factory=list)
    warning_codes: list[str] = Field(default_factory=list)
    cart_mode: str = "demo"


class CartOfferRequest(Payload):
    product_id: int = Field(strict=True, ge=1)
    quantity: int = Field(strict=True, ge=1, le=100000)


class CartItem(CartOfferRequest):
    confirmed: StrictBool = False
    offer_token: str | None = Field(default=None, max_length=128)


class CartChangeRequest(Payload):
    product_id: int = Field(strict=True, ge=1)
    quantity: int = Field(strict=True, ge=0, le=100000)


class CartChange(CartChangeRequest):
    confirmed: StrictBool = False
    offer_token: str | None = Field(default=None, max_length=128)


class EscalationRequest(Payload):
    comment: str = Field(default="", max_length=2000)


def request_language(request):
    return normalize_language(getattr(request.state, "language", None) or
                              request.query_params.get("language") or request.headers.get("x-language"))


def error_payload(code, language, fallback="", params=None):
    return {"detail": localize_error(code, language, fallback, params), "code": code,
            "params": params or {}, "answer_language": normalize_language(language)}


def language_parameters(request: Request, language: Literal["ru", "kk", "en"] | None = Query(None),
                        x_language: Literal["ru", "kk", "en"] | None = Header(None)):
    request.state.language = language or x_language or "ru"


class UploadSizeLimit:
    """Bound the incoming stream before multipart parsing can spool it to disk."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] != "/api/agent/upload-spec" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        chunks, size = [], 0
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            body = event.get("body", b"")
            size += len(body)
            if size > 16 * 1024 * 1024:
                language = request_language(Request(scope))
                response = JSONResponse(error_payload("file_too_large", language),
                                        status_code=413, headers={"Cache-Control": "no-store"})
                return await response(scope, receive, send)
            chunks.append(body)
            if not event.get("more_body", False):
                break
        delivered = False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()
        await self.app(scope, bounded_receive, send)


def create_app(catalog=None, carts=None, agent=None, parser=None, request_limit=None):
    catalog = catalog or ekt_client
    carts = carts or (agent_service.carts if catalog is ekt_client else CartService(catalog))
    agent = agent or (agent_service if carts is agent_service.carts else AgentService(catalog, carts))
    parser = parser or SpecificationParser(catalog)
    app = FastAPI(title="NEXIS — консультант ekt.kz", version="3.0.0", dependencies=[Depends(language_parameters)])
    app.add_middleware(UploadSizeLimit)
    app.state.catalog, app.state.carts, app.state.agent = catalog, carts, agent
    origins = [f"http://{host}:{port}" for host in ("localhost", "127.0.0.1") for port in (3000, 5173)]
    origins += [value.strip() for value in os.getenv("CORS_ORIGINS", "").split(",") if value.strip()]
    buckets = OrderedDict()
    limit = request_limit or env_int("REQUESTS_PER_MINUTE", 60, 1, 10000)

    @app.middleware("http")
    async def safety_headers(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex
        if request.method != "OPTIONS" and request.url.path not in {"/api/health", "/openapi.json", "/docs", "/redoc"}:
            identity = request.headers.get("x-session-id") or request.query_params.get("session_id")
            address = request.client.host if request.client else "unknown"
            group = "upload" if request.url.path.endswith("upload-spec") else "api"
            now = time.monotonic()
            cap = min(limit, 8) if group == "upload" else limit
            keys = [hashlib.sha256(("ip:" + address + group).encode()).hexdigest()]
            if identity:
                keys.append(hashlib.sha256(("session:" + identity + group).encode()).hexdigest())
            for key in keys:
                bucket = buckets.setdefault(key, deque())
                while bucket and now - bucket[0] > 60:
                    bucket.popleft()
                if len(bucket) >= cap:
                    return JSONResponse(error_payload("rate_limited", request_language(request)),
                                        status_code=429, headers={"Retry-After": "60", "Cache-Control": "no-store",
                                                                 "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})
            for key in keys:
                buckets[key].append(now)
                buckets.move_to_end(key)
            while len(buckets) > 10000:
                buckets.popitem(last=False)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["Content-Language"] = request_language(request)
        return response

    @app.exception_handler(ServiceError)
    async def service_error(request, error):
        return JSONResponse(error_payload(error.code, request_language(request), error.message, error.params), status_code=error.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        body = error.body
        if request.url.path == "/api/agent/chat" and isinstance(body, dict) and body.get("language") in LANGUAGES:
            request.state.language = body["language"]
        return JSONResponse(error_payload("validation_error", request_language(request)), status_code=422)

    def session(query, header):
        if query and header and query != header:
            raise ServiceError("Идентификаторы сессии не совпадают.", "session_mismatch", 401)
        token = header or query
        carts.session(token)
        return token

    @app.post("/api/session")
    def new_session(request: Request):
        return {**carts.new_session(), "answer_language": request_language(request)}

    @app.get("/api/health")
    def health():
        return {"status": "online", "service": "NEXIS ekt.kz backend", "team": "NEXIS", "version": "3.0.0",
                "agent_ready": bool(catalog.auth), "agent_mode": "tools" if agent.client else "rules",
                "catalog_configured": bool(catalog.auth), "catalog": catalog.coverage(),
                "ocr_available": ocr_available(), "cart_persistence": "sqlite",
                "partner_cart_connected": False, "crm_connected": False, "languages": list(LANGUAGES),
                "retrieval": knowledge_base.retrieval_status()}

    @app.get("/api/products")
    def products(request: Request, page: int = Query(1, ge=1, le=50), limit: int = Query(20, ge=1, le=100)):
        result = catalog.get_page(page)
        if result is None:
            raise ServiceError("Каталог временно недоступен.", "catalog_unavailable")
        language = request_language(request)
        return {"page": page, "limit": limit, "items": [localize_product(item, language) for item in result["items"][:limit]],
                "total_loaded": catalog.coverage()["loaded_products"],
                "has_more": result["count"] >= result["per_page"] if result["per_page"] else False,
                "data_source": "ekt.kz", "last_checked_at": result["last_checked_at"], "answer_language": language}

    @app.get("/api/products/search")
    def search(request: Request, q: str = Query(..., min_length=1, max_length=500), limit: int = Query(5, ge=1, le=10)):
        hits = catalog.search_products(q, limit)
        items = [detail for hit in hits if (detail := catalog.get_product_detail(hit["id"]))]
        if not items and catalog.last_error:
            raise ServiceError("Не удалось проверить каталог.", "catalog_unavailable")
        language = request_language(request)
        return {"items": [localize_product(item, language) for item in items], "coverage": catalog.coverage(),
                "data_source": "ekt.kz", "answer_language": language}

    def product_detail(product_id, refresh=False):
        detail = catalog.get_product_detail(product_id, force_refresh=refresh)
        if not detail:
            if catalog.last_error == "upstream_http_404":
                raise ServiceError("Товар не найден.", "product_not_found", 404)
            raise ServiceError("Карточка товара недоступна.", "catalog_unavailable")
        return detail

    @app.get("/api/products/{product_id}")
    def product(request: Request, product_id: int = Path(ge=1), refresh: bool = False):
        return localize_product(product_detail(product_id, refresh), request_language(request))

    @app.get("/api/products/{product_id}/analogs")
    def analogs(request: Request, product_id: int = Path(ge=1)):
        detail = product_detail(product_id, True)
        items = catalog.find_analogs(detail)
        language = request_language(request)
        return {"items": [localize_product(item, language) for item in items], "coverage": catalog.coverage(),
                "message": tr("analogs_found" if items else "analogs_missing", language), "answer_language": language}

    @app.get("/api/faq")
    def faq(request: Request, q: str | None = Query(None, max_length=500)):
        language = request_language(request)
        articles = search_knowledge_base(q, 6, language=language) if q else [knowledge_base.localize_article(item, language) for item in KB_ARTICLES]
        return {"categories": [{"id": key, "title": category_title(key, language)} for key in sorted({item["category"] for item in KB_ARTICLES})],
                "articles": articles, "answer_language": language}

    @app.get("/api/purchase-terms")
    def terms(request: Request):
        return {**purchase_terms(language=request_language(request)), "answer_language": request_language(request)}

    @app.post("/api/manager/escalate")
    def escalate(body: EscalationRequest, request: Request):
        return {"status": "manual_handoff_required", "contacts_url": CONTACTS_URL,
                "message": tr("manual_handoff", request_language(request)), "answer_language": request_language(request)}

    @app.get("/api/integrations")
    def integrations(request: Request):
        return {"catalog": {"configured": bool(catalog.auth), "mode": "read_only"},
                "cart": {"mode": "demo", "persisted": True, "read_link": True, "partner_connected": False},
                "crm": {"connected": False, "contacts_url": CONTACTS_URL},
                "required_from_partner": [tr(key, request_language(request)) for key in ("partner_cart_contract", "partner_test_access", "partner_crm_contract")],
                "answer_language": request_language(request)}

    def select_from_card(sid, product_id, quantity, language):
        # Selection is context only; this never authorizes a mutation or a chat offer.
        previous = agent.context.get(sid)
        agent.context.update(sid, product_id=product_id, selected_ids=[product_id], candidate_ids=[product_id],
                             quantity=quantity, language=language, constraints={}, pending_clarification=None,
                             family=None, topic="product", city=None, budget=None, revision=previous.get("revision", 0) + 1)

    @app.get("/api/cart")
    def get_cart(request: Request, session_id: str | None = None, x_session_id: str | None = Header(None)):
        return localize_cart_result(carts.snapshot(session(session_id, x_session_id)), request_language(request))

    @app.post("/api/cart/offer")
    def offer(body: CartOfferRequest, request: Request, session_id: str | None = None, x_session_id: str | None = Header(None)):
        sid, language = session(session_id, x_session_id), request_language(request)
        result = carts.prepare(sid, body.product_id, body.quantity)
        select_from_card(sid, body.product_id, body.quantity, language)
        return localize_cart_result(result, language)

    @app.post("/api/cart/add")
    def add(body: CartItem, request: Request, session_id: str | None = None, x_session_id: str | None = Header(None)):
        result = carts.confirm(session(session_id, x_session_id), body.product_id, body.quantity, body.offer_token, body.confirmed)
        result.pop("product", None)
        return localize_cart_result(result, request_language(request))

    @app.post("/api/cart/change-offer")
    def change_offer(body: CartChangeRequest, request: Request, session_id: str | None = None, x_session_id: str | None = Header(None)):
        return localize_cart_result(carts.prepare_change(session(session_id, x_session_id), body.product_id, body.quantity), request_language(request))

    @app.post("/api/cart/change")
    def change(body: CartChange, request: Request, session_id: str | None = None, x_session_id: str | None = Header(None)):
        return localize_cart_result(carts.confirm_change(session(session_id, x_session_id), body.product_id, body.quantity, body.offer_token, body.confirmed), request_language(request))

    @app.get("/api/cart/export")
    def export(request: Request, session_id: str | None = None, x_session_id: str | None = Header(None)):
        snapshot = carts.snapshot(session(session_id, x_session_id))
        output = io.StringIO()
        writer = csv.writer(output)
        language = request_language(request)
        writer.writerow([tr("article", language), tr("name", language), tr("quantity", language),
                         tr("price", language) + " KZT", tr("sum", language) + " KZT"])
        def cell(value):
            text = str(value)
            return "'" + text if text[:1] in "=+-@\t\r" else text
        for item in snapshot["items"]:
            writer.writerow([cell(item["article"]), cell(item["name"]), item["quantity"], item["price"],
                             round(item["price"] * item["quantity"], 2)])
        return Response("\ufeff" + output.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": 'attachment; filename="nexis-cart.csv"'})

    @app.get("/cart/{read_token}", response_class=HTMLResponse)
    def view_cart(read_token: str, request: Request):
        cart = carts.read_link(read_token)
        language = request_language(request)
        def label(key):
            return html.escape(tr(key, language))
        rows = "".join(f"<tr><td>{html.escape(item['article'])}</td><td>{html.escape(item['name'])}</td>"
                       f"<td>{item['quantity']}</td><td>{item['price']:,.2f} ₸</td></tr>" for item in cart["items"])
        page = (f'<!doctype html><html lang="{language}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{label("cart_title")}</title><style>body{{font:16px system-ui;max-width:900px;margin:4vw auto;padding:16px}}'
                'table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;border-bottom:1px solid #ddd}'
                '.table{overflow:auto}p{line-height:1.6}</style>'
                f'<h1>{label("cart_title")}</h1><p>{label("cart_notice")}</p>'
                f'<div class="table"><table><thead><tr><th>{label("article")}</th><th>{label("name")}</th><th>{label("quantity")}</th><th>{label("price")}</th></tr></thead><tbody>'
                + (rows or f'<tr><td colspan="4">{label("cart_empty")}</td></tr>') +
                f'</tbody></table></div><p><strong>{label("total")}: {cart["total_sum"]:,.2f} ₸</strong></p>'
                f'<p>{label("partner_cart_notice")}</p>'
                f'<a href="https://ekt.kz/personal/cart/" rel="noreferrer">{label("partner_cart_open")}</a></html>')
        return HTMLResponse(page, headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'"})

    @app.post("/api/agent/chat", response_model=ChatResponse)
    def chat(body: ChatRequest, request: Request, x_session_id: str | None = Header(None)):
        request.state.language = body.language
        sid = session(body.session_id, x_session_id)
        result = agent.process_message(body.message, [item.model_dump() for item in body.history], sid, body.language,
                                       request_id=request.state.request_id)
        result.update(answer_language=body.language, request_id=request.state.request_id)
        result["sources"] = [localize_product(item, body.language) for item in result.get("sources", [])]
        result["cart_url"] = localized_url(result.get("cart_url"), body.language)
        return result

    @app.post("/api/agent/upload-spec")
    async def upload(request: Request, file: UploadFile = File(...)):
        try:
            content = await file.read(MAX_BYTES + 1)
            filename = os.path.basename(file.filename or "unknown")[:200]
            estimate = await run_in_threadpool(parser.parse_specification, content, filename)
            language = request_language(request)
            return {"status": "success", "filename": filename, "content_type": file.content_type,
                    "estimate": localize_estimate(estimate, language), "answer_language": language}
        finally:
            await file.close()

    # CORS wraps early error/rate-limit responses too.
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "X-Session-Id", "X-Language"],
                       expose_headers=["X-Request-Id", "Content-Language"])
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.getenv("HOST", "127.0.0.1"), port=env_int("PORT", 8000, 1, 65535), access_log=False)
