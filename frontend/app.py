"""Career Intelligence Platform — Streamlit frontend.

Screens follow Career_Intelligence_Platform_App_Flow.md: Landing → Analysis
Progress → Career Dashboard → Job Matches / Job Details / Learning Roadmap /
Portfolio Projects / Explainability / Export Report. All data comes from the
existing backend Python APIs via :mod:`backend_client`; the backend is never
modified here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend_client import ANALYSIS_STEPS, analyze  # noqa: E402
from report import build_markdown_report  # noqa: E402

ROLE_OPTIONS = [
    "AI/ML",
    "Backend",
    "Frontend",
    "Data",
    "Full-Stack",
    "Software Engineering",
]

DASHBOARD_VIEWS = [
    "Career Dashboard",
    "Job Matches",
    "Learning Roadmap",
    "Portfolio Projects",
    "Explainability",
    "Export Report",
]


def main() -> None:
    st.set_page_config(page_title="Career Intelligence Platform", layout="wide")
    _bootstrap_state()

    if st.session_state.view == "landing":
        _render_landing()
    elif st.session_state.view == "error":
        _render_error()
    elif st.session_state.view == "progress":
        _run_and_render_dashboard()
    else:
        _render_dashboard_shell()


def _bootstrap_state() -> None:
    defaults = {
        "view": "landing",
        "username": "",
        "role": "AI/ML",
        "location": "",
        "result": None,
        "error_messages": [],
        "current_page": "Career Dashboard",
        "selected_job_index": 0,
        "show_job_details": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def _reset() -> None:
    for key in ("view", "username", "result", "error_messages"):
        st.session_state[key] = None if key == "result" else "landing" if key == "view" else ""
    st.session_state.error_messages = []


def _start_analysis() -> None:
    username = st.session_state.username.strip()
    if not username:
        st.error("Please enter a GitHub username.")
        return
    st.session_state.view = "progress"
    st.rerun()


def _render_landing() -> None:
    st.title("Career Intelligence Platform")
    st.subheader("Understand where you stand, discover fitting jobs, and close skill gaps.")
    st.write(
        "Enter a GitHub username and we will analyze your public repositories, "
        "build a structured developer profile, match you against live job "
        "postings, and generate an evidence-backed learning plan."
    )

    with st.form("landing_form"):
        st.text_input(
            "GitHub username",
            key="username",
            placeholder="e.g. octocat",
            value=st.session_state.username,
        )
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Target role", ROLE_OPTIONS, key="role")
        with col2:
            st.text_input("Location (optional)", key="location", placeholder="e.g. United States")
        submitted = st.form_submit_button("Start Analysis", type="primary")

    if submitted:
        _start_analysis()


def _map_error(message: str) -> str:
    lowered = message.lower()
    if "rate limit" in lowered:
        return "GitHub rate limit exceeded. Please try again later."
    if "not found" in lowered:
        return "GitHub profile not found. Please check the username."
    if "no public repositories" in lowered or "repositories to analyze" in lowered:
        return "Not enough public repositories to analyze."
    return message


def _render_error() -> None:
    st.title("Analysis Failed")
    for message in st.session_state.error_messages:
        st.error(_map_error(message))
    if st.button("Try Again"):
        _reset()
        st.rerun()


def _run_and_render_dashboard() -> None:
    st.title("Analyzing Profile")
    st.write(f"Building your career dashboard for **@{st.session_state.username}**.")

    progress_bar = st.progress(0.0)
    status = st.empty()

    def on_step(index: int, label: str) -> None:
        progress_bar.progress((index + 1) / len(ANALYSIS_STEPS))
        status.markdown(f"### {label}")
        if index < len(ANALYSIS_STEPS) - 1:
            status.markdown(
                f"**{label}** — estimated {max(1, (len(ANALYSIS_STEPS) - index - 1) * 4)}s remaining"
            )

    result = analyze(
        st.session_state.username,
        role=st.session_state.role,
        location=st.session_state.location or None,
        on_step=on_step,
    )

    if result["errors"]:
        st.session_state.error_messages = result["errors"]
        st.session_state.view = "error"
    else:
        st.session_state.result = result
        st.session_state.view = "dashboard"
    st.rerun()


def _render_dashboard_shell() -> None:
    with st.sidebar:
        st.header(f"@{st.session_state.username}")
        if st.session_state.result is not None:
            warnings = st.session_state.result.get("warnings") or []
            for warning in warnings:
                st.warning(warning)
        current_index = DASHBOARD_VIEWS.index(st.session_state.current_page)
        st.radio(
            "Navigation",
            DASHBOARD_VIEWS,
            index=current_index,
            key="nav_view",
            on_change=_sync_current_page,
        )
        if st.button("New Analysis"):
            _reset()
            st.rerun()

    page = st.session_state.current_page
    if page == "Career Dashboard":
        _render_dashboard()
    elif page == "Job Matches":
        _render_jobs_page()
    elif page == "Learning Roadmap":
        _render_roadmap()
    elif page == "Portfolio Projects":
        _render_projects()
    elif page == "Explainability":
        _render_explainability()
    elif page == "Export Report":
        _render_export()


def _sync_current_page() -> None:
    selected = st.session_state.nav_view
    if selected != st.session_state.current_page:
        st.session_state.current_page = selected
        st.session_state.show_job_details = False


def _navigate(page: str, *, show_job_details: bool = False) -> None:
    st.session_state.current_page = page
    st.session_state.show_job_details = show_job_details


def _render_jobs_page() -> None:
    if st.session_state.show_job_details:
        _render_job_details_for_selected()
    else:
        _render_jobs()


def _render_dashboard() -> None:
    result = st.session_state.result
    profile = result["profile"]
    report = result["report"]
    guidance = result.get("guidance")

    st.title("Career Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("Overall Profile Score", f"{profile.quality_score:.1f}/100")
    col2.metric("Confidence", profile.confidence.level)
    col3.metric("Experience Level", _experience_level(profile))

    st.subheader("Developer Summary")
    top_skills = [s.name for s in profile.frameworks[:6]]
    if profile.languages:
        top_skills = [l.name for l in profile.languages[:3]] + top_skills
    st.write(f"**Top Skills:** {', '.join(top_skills) or '—'}")
    if profile.domains:
        st.write(
            "**Preferred Domains:** "
            + ", ".join(f"{d.name} ({d.strength:.0f})" for d in profile.domains[:5])
        )
    if profile.confidence.reason:
        st.caption(f"Confidence: {profile.confidence.reason}")

    st.subheader("Skill Overview")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Languages**")
        st.write(", ".join(l.name for l in profile.languages) or "—")
        st.markdown("**Frameworks**")
        st.write(", ".join(f.name for f in profile.frameworks) or "—")
    with c2:
        databases, cloud, tools = _bucket_libraries(profile.libraries)
        st.markdown("**Databases**")
        st.write(", ".join(databases) or "—")
        st.markdown("**Cloud**")
        st.write(", ".join(cloud) or "—")
        st.markdown("**Tools & Libraries**")
        st.write(", ".join(tools) or "—")

    st.subheader("Repository Quality")
    quality_metrics = _repository_quality_metrics(profile, report)
    qcols = st.columns(len(quality_metrics))
    for col, (label, value) in zip(qcols, quality_metrics.items()):
        col.metric(label, value)

    st.subheader("Quick Statistics")
    stats = _quick_statistics(report, profile)
    scol = st.columns(len(stats))
    for col, (label, value) in zip(scol, stats.items()):
        col.metric(label, value)

    if guidance is not None:
        st.success(guidance.explainability.summary)
    else:
        st.info("Job intelligence unavailable; showing profile analysis only.")


def _render_jobs() -> None:
    st.title("Job Matches")
    ranked = st.session_state.result.get("ranked_jobs") or []
    if not ranked:
        st.info("No job matches available.")
        return

    for index, match in enumerate(ranked):
        job = match.job
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"### {job.title}")
            c1.caption(f"{job.company or 'Unknown'} · {job.location or 'Remote'} · {job.employment_type or '—'}")
            c2.metric("Match Score", f"{match.match_score:.0f}%")
            c3.metric("Confidence", match.confidence)
            if c1.button("View Details", key=f"details_{index}"):
                st.session_state.selected_job_index = index
                _navigate("Job Matches", show_job_details=True)
                st.rerun()


def _render_job_details_for_selected() -> None:
    ranked = st.session_state.result.get("ranked_jobs") or []
    index = st.session_state.selected_job_index
    if index >= len(ranked):
        st.info("No job selected.")
        return
    _render_job_details(ranked[index])
    if st.button("Back to Job Matches"):
        _navigate("Job Matches")
        st.rerun()


def _render_job_details(match) -> None:
    st.title("Job Details")
    job = match.job
    st.markdown(f"### {job.title}")
    st.caption(f"{job.company or 'Unknown'} · {job.location or 'Remote'} · {job.employment_type or '—'}")
    if job.url:
        st.link_button("Apply on Jobicy", job.url)

    st.subheader("Match Breakdown")
    b = match.breakdown
    cols = st.columns(4)
    cols[0].metric("Overall Match", f"{match.match_score:.0f}%")
    cols[1].metric("Semantic Match", f"{b.semantic_similarity * 100:.0f}%")
    cols[2].metric("Skill Match", f"{b.skill_overlap * 100:.0f}%")
    cols[3].metric("Repository Quality", f"{b.quality_score:.0f}%")

    st.subheader("Why You Match")
    if match.matched_skills:
        st.write(", ".join(f"**{s}**" for s in match.matched_skills))
        _render_evidence_for_skills(match.matched_skills)
    else:
        st.write("No directly matched skills; your profile is close semantically.")

    st.subheader("Missing Skills")
    if match.missing_skills:
        st.write(", ".join(f"**{s}**" for s in match.missing_skills))
    else:
        st.success("You have all the skills this job requires.")

    if st.button("View Learning Plan"):
        _navigate("Learning Roadmap")
        st.rerun()


def _render_evidence_for_skills(skills: list[str]) -> None:
    profile = st.session_state.result["profile"]
    wanted = {skill.lower() for skill in skills}
    items = [
        item for item in profile.evidence.items if item.skill.lower() in wanted
    ]
    if not items:
        return
    st.markdown("**Evidence**")
    for item in items[:8]:
        location = f"{item.repository} · {item.file_path}" if item.file_path else item.repository
        st.write(f"- {item.skill} — {location} (confidence {item.confidence:.0%})")


def _render_roadmap() -> None:
    st.title("Learning Roadmap")
    guidance = st.session_state.result.get("guidance")
    if guidance is None or not guidance.roadmap.steps:
        st.info("No learning plan available.")
        return
    for step in guidance.roadmap.steps:
        with st.container(border=True):
            st.markdown(f"### {step.title}")
            st.write(step.goal)
            st.caption(f"Skills: {', '.join(step.skills)}")
            if step.driven_by:
                st.caption(f"Driven by: {', '.join(step.driven_by[:3])}")
            for resource in step.resources:
                st.markdown(
                    f"- [{resource.title}]({resource.url}) — *{resource.source}* · "
                    f"{resource.resource_type} · {resource.difficulty}"
                )


def _render_projects() -> None:
    st.title("Portfolio Project Suggestions")
    guidance = st.session_state.result.get("guidance")
    if guidance is None or not guidance.portfolio_projects:
        st.info("No project suggestions available.")
        return
    for project in guidance.portfolio_projects:
        with st.container(border=True):
            st.markdown(f"### {project.title}")
            st.write(project.summary)
            st.caption(
                f"Difficulty: {project.difficulty} · Estimated: {project.estimated_weeks} weeks · "
                f"Skills: {', '.join(project.skills)}"
            )
            st.caption(project.rationale)
            for resource in project.resources:
                st.markdown(f"- [{resource.title}]({resource.url}) — *{resource.source}*")


def _render_explainability() -> None:
    st.title("Explainability")
    profile = st.session_state.result["profile"]
    guidance = st.session_state.result.get("guidance")

    st.subheader("Confidence")
    st.metric("Profile Confidence", profile.confidence.level)

    st.subheader("Strengths")
    if profile.domains:
        strengths = [f"Strong {d.name} focus" for d in profile.domains[:3]]
        st.write(", ".join(strengths))
    st.write(f"Practices: {', '.join(p.name for p in profile.engineering_practices[:5]) or '—'}")

    if guidance is not None:
        st.subheader("Weaknesses (Skill Gaps)")
        st.write(", ".join(g.name for g in guidance.skill_gap.missing_skills[:5]) or "None")
        st.subheader("Why These Recommendations")
        st.write(guidance.explainability.summary)
        if guidance.explainability.grounded_resources:
            st.write("Every recommendation is grounded in retrieved learning resources:")
            st.write(
                ", ".join(r.title for r in guidance.explainability.grounded_resources[:8])
            )

    st.subheader("Evidence")
    st.caption("Every skill claim links back to a GitHub repository and source file.")
    if profile.evidence.items:
        st.write(f"{len(profile.evidence.items)} evidence items across your repositories.")


def _render_export() -> None:
    st.title("Export Report")
    markdown = build_markdown_report(st.session_state.username, st.session_state.result)
    st.download_button(
        "Download Markdown Report",
        data=markdown,
        file_name=f"{st.session_state.username}_career_report.md",
        mime="text/markdown",
        type="primary",
    )
    st.caption("PDF export is planned for a future release.")


# --- dashboard helpers -------------------------------------------------------


def _experience_level(profile) -> str:
    repos = len(profile.projects)
    if repos >= 8 and profile.quality_score >= 65:
        return "Senior"
    if repos >= 3:
        return "Mid-Level"
    return "Entry-Level"


def _bucket_libraries(libraries) -> tuple[list[str], list[str], list[str]]:
    databases, cloud, tools = [], [], []
    for item in libraries:
        if item.category == "database":
            databases.append(item.name)
        elif item.category == "devops_cloud":
            cloud.append(item.name)
        else:
            tools.append(item.name)
    return databases, cloud, tools


def _repository_quality_metrics(profile, report) -> dict[str, str]:
    practices = {p.name: p.repository_count for p in profile.engineering_practices}
    analyzed = len(report.repositories) if report else max(1, len(profile.projects))
    languages = {
        repo.primary_language for repo in report.repositories if repo.primary_language
    } if report else set()
    return {
        "README Coverage": f"{practices.get('readme', 0)}/{analyzed}",
        "Testing": f"{practices.get('testing', 0)}/{analyzed}",
        "CI/CD": f"{practices.get('ci_cd', 0)}/{analyzed}",
        "Documentation": f"{practices.get('documentation', 0)}/{analyzed}",
        "Project Diversity": str(len(languages)),
    }


def _quick_statistics(report, profile) -> dict[str, str]:
    repos = report.repositories if report else []
    public_repos = report.profile.public_repos if report else len(repos)
    original = sum(1 for repo in repos if not repo.is_fork)
    total_stars = sum(repo.stars for repo in repos)
    recent = max((repo.pushed_at for repo in repos if repo.pushed_at), default=None)
    recent_label = recent.strftime("%Y-%m-%d") if recent else "—"
    return {
        "Public Repositories": str(public_repos),
        "Original Projects": str(original),
        "Total Stars": str(total_stars),
        "Recent Activity": recent_label,
    }


if __name__ == "__main__":
    main()
