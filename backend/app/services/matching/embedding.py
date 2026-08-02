"""Developer profile embedding for matching.

Serializes the structured :class:`DeveloperProfile` into a text representation
and embeds it with the same sentence-transformers model used for jobs, so both
sides of a cosine similarity share one embedding space.
"""

from __future__ import annotations

from app.services.developer_profile.models import DeveloperProfile
from app.services.jobs.embedding import JobEmbedder


def profile_to_text(profile: DeveloperProfile) -> str:
    """Serialize a developer profile into a single embedding document."""
    parts: list[str] = [f"Developer {profile.github_username}"]
    if profile.languages:
        parts.append("Languages: " + ", ".join(item.name for item in profile.languages))
    if profile.frameworks:
        parts.append("Frameworks: " + ", ".join(item.name for item in profile.frameworks))
    if profile.libraries:
        parts.append("Libraries: " + ", ".join(item.name for item in profile.libraries))
    if profile.domains:
        parts.append("Domains: " + ", ".join(item.name for item in profile.domains))
    projects = [f"{item.name}: {item.description}" for item in profile.projects if item.description]
    if projects:
        parts.append("Projects: " + " ".join(projects))
    return ". ".join(parts)


class DeveloperEmbedder(JobEmbedder):
    """Embeds a developer profile into a normalized vector."""

    def embed_profile(self, profile: DeveloperProfile) -> list[float]:
        """Return the normalized embedding vector for ``profile``."""
        return self.embed_documents([profile_to_text(profile)])[0]
