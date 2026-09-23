import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

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

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "online",
        "service": "ekt.kz Agentic AI Backend",
        "team": "NEXIS",
        "agent_ready": True,
        "version": "1.0.0"
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
    # Placeholder initial response for connectivity verification
    session_id = request.session_id or "default_session"
    items = CART_STORE.get(session_id, [])
    
    return AgentQueryResponse(
        answer="Здравствуйте! Я ИИ-консультант ekt.kz. Чем могу помочь по каталогу электротехнической продукции?",
        reasoning_steps=[
            ReasoningStep(
                step_number=1,
                type="thought",
                message="Инициализация сессии консультанта ekt.kz"
            )
        ],
        cart_updated=False,
        cart_items_count=len(items),
        cart_url="/cart"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
