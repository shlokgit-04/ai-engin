from __future__ import annotations
import os
from typing import Any, Optional
import httpx


class KnowledgeSearchService:
    """Searches the backend Knowledge Hub via its REST API."""

    def __init__(self) -> None:
        self._backend_url = os.getenv(
            "BACKEND_URL",
            os.getenv("NUROFIN_BACKEND_URL", "http://127.0.0.1:8099"),
        ).rstrip("/")

    async def search(
        self,
        query: str,
        source_type: Optional[str] = None,
        project_id: Optional[int] = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        url = f"{self._backend_url}/api/v1/knowledge/search"
        params: dict[str, Any] = {"q": query, "top_k": top_k}
        if source_type:
            params["source_type"] = source_type
        if project_id:
            params["project_id"] = project_id

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
        except Exception:
            return []

    async def get_stats(self) -> dict[str, Any]:
        url = f"{self._backend_url}/api/v1/knowledge/stats"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.json().get("data", {})
        except Exception:
            return {"total_chunks": 0, "by_source": {}, "by_type": {}}

    def build_rag_context(self, search_results: list[dict]) -> str:
        if not search_results:
            return ""

        parts = ["RELEVANT KNOWLEDGE FROM COMPANY KNOWLEDGE BASE:"]
        for i, result in enumerate(search_results[:8], 1):
            source = result.get("source_type", "unknown")
            title = result.get("title", "Untitled")
            content = result.get("content", "")
            source_title = result.get("source_title", "")
            score = result.get("score", 0)
            chunk_type = result.get("chunk_type", "")

            parts.append(
                f"\n[{i}] Source: {source.title()} - {source_title} "
                f"| Type: {chunk_type} | Relevance: {score:.2f}\n"
                f"Title: {title}\n"
                f"Content: {content[:1500]}\n"
            )

        parts.append(
            "\nUsing the above knowledge, answer the user's question. "
            "Cite specific sources when possible (e.g., 'According to the meeting on...' or 'Based on task...'). "
            "If the knowledge base does not contain relevant information, say so honestly."
        )
        return "\n".join(parts)
