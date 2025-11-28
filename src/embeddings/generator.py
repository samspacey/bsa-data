"""Generate embeddings for review texts using OpenAI."""

import asyncio
from typing import Optional

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

from src.config.settings import settings


class EmbeddingGenerator:
    """Generate embeddings using OpenAI's embedding models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = settings.openai_embedding_model,
        max_concurrent: int = settings.max_concurrent_requests,
    ):
        """Initialize the embedding generator.

        Args:
            api_key: OpenAI API key
            model: Embedding model to use
            max_concurrent: Maximum concurrent API requests
        """
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = model
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._total_tokens = 0

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for current event loop."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    async def _embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        async with self._get_semaphore():
            # Truncate if too long (8191 tokens max for ada-002, similar for v3)
            if len(text) > 20000:
                text = text[:20000]

            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            self._total_tokens += response.usage.total_tokens
            return response.data[0].embedding

    async def embed_texts(
        self,
        texts: list[str],
        show_progress: bool = True,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            show_progress: Show progress bar

        Returns:
            List of embedding vectors
        """
        tasks = [self._embed_single(text) for text in texts]

        if show_progress:
            embeddings = []
            for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Embedding"):
                embedding = await coro
                embeddings.append(embedding)
            # Reorder to match input order
            # Actually, as_completed doesn't preserve order, so we need a different approach
            # Let's use gather instead
            embeddings = await asyncio.gather(*tasks)
        else:
            embeddings = await asyncio.gather(*tasks)

        return embeddings

    def embed_texts_sync(
        self,
        texts: list[str],
        show_progress: bool = True,
    ) -> list[list[float]]:
        """Synchronous wrapper for embed_texts.

        Args:
            texts: List of texts to embed
            show_progress: Show progress bar

        Returns:
            List of embedding vectors
        """
        return asyncio.run(self.embed_texts(texts, show_progress))

    @property
    def total_tokens(self) -> int:
        """Get total tokens used."""
        return self._total_tokens

    @property
    def estimated_cost(self) -> float:
        """Estimate cost based on tokens used.

        text-embedding-3-small: $0.02 / 1M tokens
        text-embedding-3-large: $0.13 / 1M tokens
        """
        if "small" in self.model:
            return self._total_tokens * 0.02 / 1_000_000
        elif "large" in self.model:
            return self._total_tokens * 0.13 / 1_000_000
        else:
            # Default to small pricing
            return self._total_tokens * 0.02 / 1_000_000
