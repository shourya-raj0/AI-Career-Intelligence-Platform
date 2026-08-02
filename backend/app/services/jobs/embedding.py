"""Job embedding generation.

Uses a sentence-transformers model (default ``all-MiniLM-L6-v2``, 384 dims) to
embed normalized job text. The model is loaded lazily on first use so importing
this module never downloads models or loads torch.
"""

from __future__ import annotations

import os
from typing import Any

#: Process-wide cache of loaded SentenceTransformer models keyed by model name.
#: Every :class:`JobEmbedder` (jobs, developer-profile, resource retrieval)
#: shares one model object per name, so the (relatively large) model is loaded
#: at most once per process instead of once per service instance.
_SHARED_MODELS: dict[str, Any] = {}


class JobEmbedder:
    """Generates normalized embeddings for job documents."""

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, model_name: str | None = None) -> None:
        self._model_name = model_name or os.getenv("EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self._model: Any = None

    def embed_documents(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed ``texts`` in batches, returning normalized vectors."""
        if not texts:
            return []
        model = self._get_model()
        vectors = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def _get_model(self) -> Any:
        """Return the shared model for ``self._model_name``, loading on first use."""
        if self._model is None:
            if self._model_name not in _SHARED_MODELS:
                from sentence_transformers import SentenceTransformer

                _SHARED_MODELS[self._model_name] = SentenceTransformer(self._model_name)
            self._model = _SHARED_MODELS[self._model_name]
        return self._model
