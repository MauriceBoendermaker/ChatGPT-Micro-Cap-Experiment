from typing import List, Optional
from pydantic import BaseModel, Field, validator


class Order(BaseModel):
    ticker: str = Field(..., min_length=1)
    side: str
    shares: float
    reason: Optional[str] = ""

    @validator("side")
    def v_side(cls, v):
        s = v.lower()
        if s not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        return s

    @validator("shares")
    def v_shares(cls, v):
        if v <= 0:
            raise ValueError("shares must be positive")
        return vs


class AIResponse(BaseModel):
    orders: List[Order] = []
    thesis: str = ""
