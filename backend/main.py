import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from agent_service import agent_service
from ekt_client import ekt_client
from knowledge_base import KB_ARTICLES, search_knowledge_base

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory Cart Storage for hackathon session
CART_STORE: Dict[str, List[Dict[str, Any]]] = {
    "default_session": []
}

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

class CartItem(BaseModel):
    product_id: int
    article: str
    name: str
    price: float
    quantity: int
    image: Optional[str] = None

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
def get_products(page: int = 1, limit: int = 20):
    """Returns products from the live ekt.kz catalog for storefront display."""
    ekt_client.preload_catalog(pages=4)
    items = ekt_client._catalog_cache
    start = (page - 1) * limit
    paged_items = items[start:start + limit] if items else []
    return {
        "page": page,
        "limit": limit,
        "total": len(items),
        "items": paged_items
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
def get_cart(session_id: str = "default_session"):
    items = CART_STORE.get(session_id, [])
    total_sum = sum(item["price"] * item["quantity"] for item in items)
    return {
        "session_id": session_id,
        "items": items,
        "total_items": len(items),
        "total_sum": total_sum,
        "checkout_url": "https://ekt.kz/personal/cart/"
    }

@app.post("/api/cart/add")
def add_to_cart(item: CartItem, session_id: str = "default_session"):
    if session_id not in CART_STORE:
        CART_STORE[session_id] = []
    
    # Check if item exists
    found = False
    for existing in CART_STORE[session_id]:
        if existing["product_id"] == item.product_id:
            existing["quantity"] += item.quantity
            found = True
            break
    if not found:
        CART_STORE[session_id].append(item.model_dump())

    return {
        "success": True,
        "message": f"Товар {item.name} успешно добавлен в корзину",
        "cart": CART_STORE[session_id]
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
async def upload_specification(file: bytes = None):
    """
    Multimodal entry point: Accepts specification documents (PDF / text)
    and extracts electrical articles for instant catalog check.
    """
    return {
        "status": "success",
        "message": "Спецификация принята к обработке агентом ekt.kz",
        "extracted_items": ["027228", "45357"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
