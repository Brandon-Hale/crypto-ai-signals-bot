"""News API clients — CryptoPanic and NewsAPI."""

import json
from datetime import datetime, timezone

import httpx
from loguru import logger

from clients.redis import RedisClient
from config import Settings
from models.news import NewsArticle


class NewsClient:
    """Fetches crypto news from CryptoPanic with NewsAPI as fallback."""

    CRYPTOPANIC_URL = "https://cryptopanic.com/api/developer/v2/posts/"
    NEWSAPI_URL = "https://newsapi.org/v2/everything"

    def __init__(self, settings: Settings, redis: RedisClient) -> None:
        self.cryptopanic_key = settings.cryptopanic_api_key
        self.newsapi_key = settings.news_api_key
        self.redis = redis
        self.http = httpx.AsyncClient(timeout=15.0)

    async def close(self) -> None:
        await self.http.aclose()

    async def fetch_news(self, asset: str, limit: int = 5) -> list[NewsArticle]:
        """Fetch recent news for an asset. Checks cache first (10 min TTL)."""
        cache_key = f"news:{asset.lower()}"
        cached = await self.redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return [NewsArticle(**a) for a in data]

        articles = await self._fetch_cryptopanic(asset, limit)
        if not articles and self.newsapi_key:
            articles = await self._fetch_newsapi(asset, limit)

        if articles:
            await self.redis.set(
                cache_key,
                json.dumps([a.model_dump(mode="json") for a in articles]),
                ex=600,  # 10 minute cache
            )

        return articles

    async def _fetch_cryptopanic(
        self, asset: str, limit: int
    ) -> list[NewsArticle]:
        """Fetch from CryptoPanic API."""
        if not self.cryptopanic_key:
            return []

        try:
            resp = await self.http.get(
                self.CRYPTOPANIC_URL,
                params={
                    "auth_token": self.cryptopanic_key,
                    "currencies": asset.upper(),
                    "kind": "news",
                    "filter": "important",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            articles: list[NewsArticle] = []
            for item in data.get("results", [])[:limit]:
                articles.append(
                    NewsArticle(
                        title=item["title"],
                        source=item.get("source", {}).get("title", "unknown"),
                        url=item.get("url", ""),
                        published_at=datetime.fromisoformat(
                            item["published_at"].replace("Z", "+00:00")
                        ),
                        currencies=[
                            c["code"] for c in item.get("currencies", [])
                        ],
                    )
                )
            return articles
        except Exception as e:
            logger.warning(f"CryptoPanic fetch failed for {asset}: {e}")
            return []

    async def _fetch_newsapi(self, asset: str, limit: int) -> list[NewsArticle]:
        """Fallback: fetch from NewsAPI."""
        try:
            resp = await self.http.get(
                self.NEWSAPI_URL,
                params={
                    "q": f"{asset} crypto",
                    "sortBy": "publishedAt",
                    "pageSize": limit,
                    "apiKey": self.newsapi_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            articles: list[NewsArticle] = []
            for item in data.get("articles", [])[:limit]:
                pub = item.get("publishedAt", "")
                articles.append(
                    NewsArticle(
                        title=item.get("title", ""),
                        source=item.get("source", {}).get("name", "unknown"),
                        url=item.get("url", ""),
                        published_at=datetime.fromisoformat(
                            pub.replace("Z", "+00:00")
                        )
                        if pub
                        else datetime.now(timezone.utc),
                    )
                )
            return articles
        except Exception as e:
            logger.warning(f"NewsAPI fetch failed for {asset}: {e}")
            return []
