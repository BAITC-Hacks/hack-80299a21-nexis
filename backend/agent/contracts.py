"""Internal typed boundaries. These contain data, never mutation authority."""
from dataclasses import dataclass, field
import time


@dataclass
class AgentPlan:
    intents: list[str] = field(default_factory=list)
    family: str | None = None
    quantity: int | float | None = None
    city: str | None = None
    budget: float | None = None
    constraints: dict = field(default_factory=dict)
    ordinal: int | None = None
    product_hint: bool = False
    explicit_identifier: bool = False
    followup: bool = False
    answer_kind: str = "general"
    query: str = ""
    knowledge_queries: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    products: dict = field(default_factory=dict)
    selected: dict = field(default_factory=dict)
    analogs: dict = field(default_factory=dict)
    analogs_by_target: dict = field(default_factory=dict)
    articles: dict = field(default_factory=dict)
    cities: dict = field(default_factory=dict)
    model_text: str = ""
    errors: list = field(default_factory=list)
    calls: int = 0

    def cards(self):
        return list((self.selected or self.analogs or self.products).values())


class RequestDeadline:
    def __init__(self, seconds=10, clock=time.monotonic):
        self.clock = clock
        self.started = clock()
        self.until = self.started + seconds

    def remaining(self):
        return max(0.0, self.until - self.clock())

    def require(self):
        remaining = self.remaining()
        if remaining <= 0:
            raise TimeoutError("request_deadline")
        return remaining

    @property
    def elapsed_ms(self):
        return round((self.clock() - self.started) * 1000)
