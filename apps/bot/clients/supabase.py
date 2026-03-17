"""Supabase client for persistent storage."""

from loguru import logger
from supabase import AsyncClient, acreate_client

from config import settings


class SupabaseClient:
    """Async Supabase client for reading and writing signals, trades, and pairs."""

    def __init__(self) -> None:
        self._client: AsyncClient | None = None

    async def init(self) -> None:
        """Initialize the async Supabase client."""
        self._client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )

    @property
    def client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError("SupabaseClient not initialized — call init() first")
        return self._client

    async def insert(self, table: str, data: dict) -> dict | None:
        """Insert a row and return the created record."""
        try:
            result = await self.client.table(table).insert(data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase insert to {table} failed: {e}")
            return None

    async def update(self, table: str, id: str, data: dict) -> dict | None:
        """Update a row by ID."""
        try:
            result = await self.client.table(table).update(data).eq("id", id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Supabase update on {table}/{id} failed: {e}")
            return None

    async def select(
        self,
        table: str,
        columns: str = "*",
        filters: dict | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """Query rows from a table."""
        try:
            query = self.client.table(table).select(columns)
            if filters:
                for col, val in filters.items():
                    query = query.eq(col, val)
            if order:
                query = query.order(order, desc=True)
            if limit:
                query = query.limit(limit)
            result = await query.execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Supabase select from {table} failed: {e}")
            return []


supabase_client = SupabaseClient()
