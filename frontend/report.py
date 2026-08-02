"""Markdown report export for the Career Intelligence Platform.

Builds a single downloadable Markdown document from an analysis result
covering the App Flow's report contents: developer summary, job matches,
skill gap, learning plan, and suggested projects.
"""

from __future__ import annotations


def build_markdown_report(username: str, result: dict) -> str:
    """Render ``result`` as a Markdown report string."""
    lines: list[str] = [f"# Career Intelligence Report — @{username}", ""]

    profile = result.get("profile")
    if profile is not None:
        lines += _profile_section(profile)

    ranked = result.get("ranked_jobs") or []
    lines += _jobs_section(ranked)

    guidance = result.get("guidance")
    if guidance is not None:
        lines += _gap_section(guidance)
        lines += _roadmap_section(guidance)
        lines += _projects_section(guidance)
        lines += _explainability_section(guidance)

    return "\n".join(lines).rstrip() + "\n"


def _profile_section(profile) -> list[str]:
    lines = ["## Developer Summary", ""]
    lines.append(f"- **Overall Profile Score:** {profile.quality_score}/100")
    lines.append(f"- **Confidence:** {profile.confidence.level} ({profile.confidence.score})")
    top = [item.name for item in profile.frameworks[:6]]
    if profile.languages:
        top = [item.name for item in profile.languages[:3]] + top
    lines.append(f"- **Top Skills:** {', '.join(top) or '—'}")
    domains = ", ".join(f"{d.name} ({d.strength})" for d in profile.domains[:5])
    lines.append(f"- **Preferred Domains:** {domains or '—'}")
    lines.append("")
    return lines


def _jobs_section(ranked) -> list[str]:
    lines = ["## Job Matches", ""]
    if not ranked:
        lines.append("No job matches available.")
        lines.append("")
        return lines
    for i, match in enumerate(ranked[:10], start=1):
        job = match.job
        lines.append(
            f"{i}. **{job.title}** — {job.company or 'Unknown'} "
            f"(score {match.match_score}, {match.confidence})"
        )
        if job.location:
            lines.append(f"   - Location: {job.location} | Type: {job.employment_type or 'N/A'}")
        if match.matched_skills:
            lines.append(f"   - Matched: {', '.join(match.matched_skills)}")
        if match.missing_skills:
            lines.append(f"   - Missing: {', '.join(match.missing_skills)}")
    lines.append("")
    return lines


def _gap_section(guidance) -> list[str]:
    lines = ["## Skill Gap", ""]
    gaps = guidance.skill_gap.missing_skills
    if not gaps:
        lines.append("No skill gaps identified.")
    else:
        for gap in gaps:
            lines.append(
                f"- **{gap.name}** — importance {gap.importance}, difficulty {gap.difficulty}, "
                f"required by {gap.demand_count} job(s)"
            )
    lines.append("")
    return lines


def _roadmap_section(guidance) -> list[str]:
    lines = ["## Learning Plan", ""]
    if not guidance.roadmap.steps:
        lines.append("No learning plan generated.")
    for step in guidance.roadmap.steps:
        lines.append(f"### {step.title}")
        lines.append(f"- Goal: {step.goal}")
        for resource in step.resources:
            lines.append(
                f"- [{resource.title} ({resource.source})]({resource.url}) — {resource.difficulty}"
            )
    lines.append("")
    return lines


def _projects_section(guidance) -> list[str]:
    lines = ["## Suggested Projects", ""]
    if not guidance.portfolio_projects:
        lines.append("No project suggestions available.")
    for project in guidance.portfolio_projects:
        lines.append(
            f"### {project.title} (difficulty {project.difficulty}, "
            f"~{project.estimated_weeks} weeks)"
        )
        lines.append(f"- {project.summary}")
        lines.append(f"- Skills: {', '.join(project.skills)}")
        for resource in project.resources:
            lines.append(
                f"- Resource: [{resource.title}]({resource.url}) — {resource.source}"
            )
    lines.append("")
    return lines


def _explainability_section(guidance) -> list[str]:
    lines = ["## Explainability", ""]
    lines.append(guidance.explainability.summary)
    if guidance.explainability.top_gap_skills:
        lines.append("")
        lines.append(f"- Priority gaps: {', '.join(guidance.explainability.top_gap_skills)}")
    if guidance.explainability.grounded_resources:
        lines.append(
            f"- Grounded in {len(guidance.explainability.grounded_resources)} learning resources."
        )
    lines.append("")
    return lines
