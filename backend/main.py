import os
import secrets
import time
from threading import RLock
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from agent_service import agent_service
from ekt_client import ekt_client
from knowledge_base import KB_ARTICLES, search_knowledge_base
from spec_parser import spec_parser

app = FastAPI(
    title="NEXIS - ekt.kz Agentic AI Assistant",
    description="Production-grade AI Assistant with Tool Calling & RAG for ekt.kz electrical catalog",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for Next.js / Vite / localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Cart Storage for hackathon session
CART_STORE: Dict[str, List[Dict[str, Any]]] = {
    "default_session": []
}
CART_OFFERS: Dict[str, Dict[str, Any]] = {}
CART_LOCK = RLock()

class HealthResponse(BaseModel):
    status: str
    service: str
    team: str
    agent_ready: bool
    version: str

class ChatMessage(BaseModel):
    role: str
    content: str

class AgentQueryRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"
    history: Optional[List[ChatMessage]] = []
    language: Optional[str] = "ru"

class ReasoningStep(BaseModel):
    step_number: int
    type: str  # thought | tool_call | tool_result
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Any] = None
    message: Optional[str] = None

class AgentQueryResponse(BaseModel):
    answer: str
    reasoning_steps: List[ReasoningStep]
    cart_updated: bool = False
    cart_items_count: int = 0
    cart_url: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = []

class CartOfferRequest(BaseModel):
    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1, le=1000)

class CartItem(CartOfferRequest):
    confirmed: bool = False
    offer_token: Optional[str] = None

class EscalateRequest(BaseModel):
    client_name: Optional[str] = "Клиент"
    phone: Optional[str] = "+7 700 000 00 00"
    comment: str
    session_id: Optional[str] = "default_session"

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "online",
        "service": "ekt.kz Agentic AI Backend",
        "team": "NEXIS",
        "agent_ready": True,
        "version": "1.0.0"
    }

@app.get("/api/products")
def get_products(page: int = Query(1, ge=1, le=50), limit: int = Query(20, ge=1, le=100)):
    """Returns products from the live ekt.kz catalog for storefront display."""
    ekt_client.preload_catalog(pages=page)
    items = ekt_client._catalog_cache
    start = (page - 1) * limit
    paged_items = items[start:start + limit] if items else []
    return {
        "page": page,
        "limit": limit,
        "total": len(items),
        "items": paged_items,
        "data_source": "ekt.kz" if ekt_client._is_indexed else "unavailable",
    }

@app.get("/api/faq")
def get_faq_categories():
    """Returns official ekt.kz knowledge base articles and categories."""
    return {
        "categories": [
            {"id": "b2b", "title": "Юридическим лицам (Счета с НДС 12%, ЭСФ)"},
            {"id": "b2c", "title": "Оплата (Kaspi QR, Карты, Наличные)"},
            {"id": "delivery", "title": "Доставка и склады по Казахстану"},
            {"id": "registration", "title": "Регистрация (Физлица и Компании по БИН)"},
            {"id": "certificates", "title": "Сертификаты соответствия ТР ТС"}
        ],
        "articles": KB_ARTICLES
    }

@app.post("/api/manager/escalate")
def escalate_to_manager(req: EscalateRequest):
    """Escalates complex requests or bulk orders to human sales engineer."""
    ticket_id = f"TICK-EKT-{os.urandom(2).hex().upper()}"
    return {
        "status": "success",
        "ticket_id": ticket_id,
        "client_name": req.client_name,
        "message": f"Заявка #{ticket_id} передана дежурному инженеру ekt.kz. С вами свяжутся в течение 10 минут.",
        "manager_whatsapp_url": f"https://wa.me/77001234567?text=Здравствуйте!%20Мой%20тикет%20{ticket_id}"
    }

@app.get("/api/cart")
def get_cart(session_id: str = Query("default_session", min_length=1, max_length=128)):
    items = CART_STORE.get(session_id, [])
    total_sum = sum(item["price"] * item["quantity"] for item in items)
    return {
        "session_id": session_id,
        "items": items,
        "total_items": sum(int(item.get("quantity", 0)) for item in items),
        "total_sum": total_sum,
        "checkout_url": "https://ekt.kz/personal/cart/",
        "cart_mode": "demo",
    }

@app.post("/api/cart/offer")
def prepare_cart_offer(item: CartOfferRequest, session_id: str = Query("default_session", min_length=1, max_length=128)):
    detail = ekt_client.get_product_detail(item.product_id, force_refresh=True)
    if not detail or not detail.get("stock_verified"):
        raise HTTPException(status_code=503, detail="Не удалось проверить товар и текущий остаток в каталоге ekt.kz.")
    try:
        price = float(detail["price"])
        available = int(detail["quantity"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=503, detail="В карточке товара отсутствует проверенная цена или остаток.")
    with CART_LOCK:
        existing = next((entry for entry in CART_STORE.get(session_id, []) if entry["product_id"] == item.product_id), None)
        remaining = max(0, available - int(existing.get("quantity", 0) if existing else 0))
        if item.quantity > remaining:
            raise HTTPException(status_code=409, detail=f"Доступно для добавления не более {remaining} шт.")
        token = secrets.token_urlsafe(24)
        CART_OFFERS[session_id] = {
            "token": token, "product_id": item.product_id,
            "quantity": item.quantity, "created_at": time.time(),
        }
    return {
        "offer_token": token,
        "product_id": item.product_id,
        "product_name": detail.get("name", "Товар ekt.kz"),
        "article": detail.get("article", "Н/Д"),
        "price": price,
        "quantity": item.quantity,
        "stock_available": available,
        "expires_in_seconds": 600,
        "cart_mode": "demo",
    }

@app.post("/api/cart/add")
def add_to_cart(item: CartItem, session_id: str = Query("default_session", min_length=1, max_length=128)):
    if not item.confirmed:
        raise HTTPException(status_code=409, detail="Явно подтвердите добавление товара.")
    with CART_LOCK:
        offer = CART_OFFERS.get(session_id)
        if (
            not offer
            or time.time() - offer["created_at"] > 600
            or offer["product_id"] != item.product_id
            or offer["quantity"] != item.quantity
            or not secrets.compare_digest(offer["token"], item.offer_token or "")
        ):
            raise HTTPException(status_code=409, detail="Предложение товара не найдено, истекло или не совпадает с количеством. Выберите товар заново.")
    detail = ekt_client.get_product_detail(item.product_id, force_refresh=True)
    if not detail or not detail.get("stock_verified"):
        raise HTTPException(status_code=503, detail="Не удалось проверить цену и остаток товара в каталоге ekt.kz.")
    try:
        price = float(detail["price"])
        available = int(detail["quantity"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=503, detail="В карточке товара отсутствует проверенная цена или остаток.")
    if available < 1:
        raise HTTPException(status_code=409, detail="Товар отсутствует на складе; добавление невозможно.")
    canonical_item = {
        "product_id": detail["id"],
        "article": detail.get("article", ""),
        "name": detail.get("name", "Товар ekt.kz"),
        "price": price,
        "quantity": item.quantity,
        "image": detail.get("image"),
    }
    with CART_LOCK:
        current_offer = CART_OFFERS.get(session_id)
        if current_offer is not offer:
            raise HTTPException(status_code=409, detail="Предложение уже использовано или заменено. Выберите товар заново.")
        entries = CART_STORE.setdefault(session_id, [])
        existing = next((entry for entry in entries if entry["product_id"] == item.product_id), None)
        current_quantity = int(existing.get("quantity", 0)) if existing else 0
        remaining = max(0, available - current_quantity)
        if item.quantity > remaining:
            raise HTTPException(status_code=409, detail=f"Доступно для добавления не более {remaining} шт.")
        if existing:
            existing["quantity"] = current_quantity + item.quantity
        else:
            entries.append(canonical_item)
        CART_OFFERS.pop(session_id, None)
        total_quantity = sum(int(entry.get("quantity", 0)) for entry in entries)
    confirmation = {
        "product_name": canonical_item["name"],
        "article": canonical_item["article"] or "Н/Д",
        "price": price,
        "quantity_added": item.quantity,
        "stock_available": available,
        "cart_items_count": total_quantity,
        "cart_url": "https://ekt.kz/personal/cart/",
        "cart_mode": "demo",
    }
    answer = (
        "✅ Товар добавлен в демонстрационную корзину.\n\n"
        f"📦 {canonical_item['name']}\n"
        f"🔢 Артикул: {canonical_item['article'] or 'Н/Д'}\n"
        f"💰 Цена: {price:,.0f} ₸\n"
        f"📊 Добавлено: {item.quantity} шт. · Проверенный остаток: {available} шт.\n"
        f"🛒 В корзине: {total_quantity} шт.\n"
        "🔗 Корзина ekt.kz: https://ekt.kz/personal/cart/"
    )

    return {
        "success": True,
        "message": answer,
        "answer": answer,
        "cart_confirmation": confirmation,
        "cart": CART_STORE[session_id],
        "cart_mode": "demo",
    }

@app.post("/api/agent/chat", response_model=AgentQueryResponse)
def agent_chat(request: AgentQueryRequest):
    """
    Main Agentic AI endpoint.
    Processes user query, executes Function Calling / RAG, respects confirmation guardrails.
    """
    session_id = request.session_id or "default_session"
    history_dicts = [{"role": m.role, "content": m.content} for m in (request.history or [])]
    
    result = agent_service.process_message(
        message=request.message,
        history=history_dicts,
        cart_store=CART_STORE,
        session_id=session_id
    )
    
    formatted_steps = [
        ReasoningStep(
            step_number=s.get("step_number", i + 1),
            type=s.get("type", "thought"),
            tool_name=s.get("tool_name"),
            tool_input=s.get("tool_input"),
            tool_output=s.get("tool_output"),
            message=s.get("message")
        )
        for i, s in enumerate(result.get("reasoning_steps", []))
    ]
    
    return AgentQueryResponse(
        answer=result.get("answer", ""),
        reasoning_steps=formatted_steps,
        cart_updated=result.get("cart_updated", False),
        cart_items_count=result.get("cart_items_count", 0),
        cart_url=result.get("cart_url", "https://ekt.kz/personal/cart/"),
        sources=result.get("sources", [])
    )

@app.post("/api/agent/upload-spec")
async def upload_specification(file: UploadFile = File(...)):
    """
    Multimodal entry point: Accepts specification documents (PDF / text)
    and extracts electrical articles for instant catalog check and estimate calculation.
    """
    filename = file.filename or ""
    extension = os.path.splitext(filename)[1].lower()
    allowed_extensions = {".pdf", ".txt", ".docx", ".xlsx", ".xls", ".jpg", ".jpeg", ".png", ".webp"}
    if extension not in allowed_extensions:
        raise HTTPException(status_code=415, detail="Поддерживаются PDF, TXT, DOCX, XLSX и XLS.")
    content = await file.read(15 * 1024 * 1024 + 1)
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Размер файла не должен превышать 15 МБ.")
    result = spec_parser.parse_specification(content, filename=filename)
    if not result.get("lines") and not result.get("error"):
        raise HTTPException(status_code=422, detail="Не удалось извлечь текст из файла.")
    if result.get("error"):
        raise HTTPException(status_code=422, detail=result["error"])
    return {
        "status": "success",
        "filename": file.filename,
        "content_type": file.content_type,
        "estimate": result
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
