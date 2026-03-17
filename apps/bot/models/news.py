"""News data models."""

from datetime import datetime

from pydantic import BaseModel


class NewsArticle(BaseModel):
    """A single news article from CryptoPanic or NewsAPI."""

    title: str
    source: str
    url: str
    published_at: datetime
    sentiment: str | None = None  # "positive" | "negative" | "neutral"
    currencies: list[str] = []  # related currency symbols
