"""
app.py - GitScope: Streamlit UI with Agent Trace (v2)

Shows the multi-agent workflow: Scout → Analyst → Reviewer with full trace.
Run: streamlit run app.py
"""

import os
from dotenv import load_dotenv

# CRITICAL: Load .env FIRST with explicit path + override before any imports
_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_dir, ".env"), override=True)

import streamlit as st
import json

st.set_page_config(
    page_title="GitScope",
    page_icon="👾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
#  CSS
# ============================================================

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp > header { display: none; }
    .main .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .hero-banner {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 40%, #1a3a4a 100%);
        border-radius: 16px;
        padding: 2.5rem 2.5rem 2rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(88,166,255,0.12) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-title { font-size: 2.2rem; font-weight: 700; color: #f0f6fc; margin: 0; }
    .hero-sub { color: #8b949e; font-size: 1rem; margin-top: 0.4rem; }

    .card {
        background: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card-title { font-size: 1.1rem; font-weight: 700; color: #1f2937; margin-bottom: 0.8rem; }

    .profile-card {
        background: linear-gradient(135deg, #f8fafc, #f0f4f8);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
    }
    .profile-avatar { width: 100px; height: 100px; border-radius: 50%; border: 3px solid #e2e8f0; margin: 0 auto 1rem; }
    .profile-name { font-size: 1.4rem; font-weight: 700; color: #1a202c; margin: 0; }
    .profile-username { color: #718096; font-size: 0.95rem; }
    .profile-bio { color: #4a5568; font-size: 0.9rem; margin: 0.8rem 0; font-style: italic; }

    .stat-row { display: flex; justify-content: center; gap: 1.2rem; margin-top: 1rem; flex-wrap: wrap; }
    .stat-box { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.7rem 1.2rem; text-align: center; min-width: 80px; }
    .stat-num { font-size: 1.3rem; font-weight: 700; color: #2d3748; }
    .stat-label { font-size: 0.7rem; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.5px; }

    .score-circle {
        width: 100px; height: 100px; border-radius: 50%;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 2.2rem; font-weight: 800; color: white; margin-bottom: 0.8rem;
    }
    .score-high { background: linear-gradient(135deg, #22c55e, #16a34a); }
    .score-mid { background: linear-gradient(135deg, #f59e0b, #d97706); }
    .score-low { background: linear-gradient(135deg, #ef4444, #dc2626); }

    .lang-bar-container { margin: 0.4rem 0; }
    .lang-bar-label { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 2px; }
    .lang-bar-bg { background: #f1f5f9; border-radius: 6px; height: 8px; overflow: hidden; }
    .lang-bar-fill { height: 100%; border-radius: 6px; }

    .tip-item { background: #f0fdf4; border-left: 3px solid #22c55e; padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 0 8px 8px 0; font-size: 0.9rem; color: #166534; }
    .strength-item { background: #eff6ff; border-left: 3px solid #3b82f6; padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 0 8px 8px 0; font-size: 0.9rem; color: #1e40af; }

    .status-badge { display: inline-block; padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .badge-green { background: #dcfce7; color: #166534; }
    .badge-yellow { background: #fef3c7; color: #92400e; }
    .badge-blue { background: #dbeafe; color: #1e40af; }

    .repo-card { background: #fafbfc; border: 1px solid #e8e8e8; border-radius: 10px; padding: 1rem 1.2rem; margin: 0.5rem 0; }
    .repo-name { font-weight: 600; color: #0969da; font-size: 0.95rem; }
    .repo-meta { font-size: 0.75rem; color: #8b949e; }

    /* TRACE PANEL */
    .trace-box {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 1rem 0;
        font-family: 'SF Mono', 'Fira Code', monospace;
    }
    .trace-header { font-weight: 700; font-size: 0.9rem; color: #58a6ff; margin-bottom: 0.8rem; }
    .trace-line { font-size: 0.8rem; color: #c9d1d9; padding: 0.25rem 0; }
    .trace-agent { color: #f0883e; font-weight: 600; }
    .trace-action { color: #7ee787; }
    .trace-detail { color: #8b949e; }
    .trace-rejected { color: #f85149; font-weight: 600; }
    .trace-approved { color: #3fb950; font-weight: 600; }

    .stTextInput > div > div > input { border-radius: 10px; border: 1px solid #d1d5db; padding: 0.7rem 1rem; font-size: 1rem; }
    .stButton > button {
        background: #0d1117; color: white; border: none; border-radius: 10px;
        padding: 0.65rem 2rem; font-weight: 600; font-size: 0.95rem; width: 100%;
    }
    .stButton > button:hover { background: #30363d; color: white; }
</style>
""", unsafe_allow_html=True)


# ============================================================
#  HELPERS
# ============================================================

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "C#": "#178600",
    "Go": "#00ADD8", "Rust": "#dea584", "Ruby": "#701516", "PHP": "#4F5D95",
    "Swift": "#F05138", "Kotlin": "#A97BFF", "Dart": "#00B4AB",
    "HTML": "#e34c26", "CSS": "#563d7c", "Shell": "#89e051",
    "Jupyter Notebook": "#DA5B0B", "Lua": "#000080",
}


def get_lang_color(lang):
    return LANG_COLORS.get(lang, "#6e7781")


def parse_profile_data(raw):
    data = {}
    for line in raw.split("\n"):
        if ": " in line and not line.startswith("="):
            key, val = line.split(": ", 1)
            data[key.strip()] = val.strip()
    return data


def parse_language_data(raw):
    langs = []
    for line in raw.split("\n"):
        line = line.strip()
        if line and "%" in line and "#" in line:
            parts = line.split()
            if len(parts) >= 2:
                lang_name = parts[0]
                try:
                    pct = float(parts[1].replace("%", ""))
                    repo_count = 1
                    if "(" in line:
                        rc = line.split("(")[1].split(" ")[0]
                        repo_count = int(rc)
                    langs.append((lang_name, pct, repo_count))
                except (ValueError, IndexError):
                    pass
    return langs


def parse_repos_data(raw):
    repos = []
    current = {}
    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("=") or stripped.startswith("Showing") or stripped.startswith("Total") or stripped.startswith("Original") or stripped.startswith("REPOSITORIES"):
            continue
        if stripped.startswith("Language:"):
            parts = stripped.split("|")
            for p in parts:
                p = p.strip()
                if p.startswith("Language:"):
                    current["language"] = p.replace("Language:", "").strip()
                elif p.startswith("Stars:"):
                    try: current["stars"] = int(p.replace("Stars:", "").strip())
                    except ValueError: current["stars"] = 0
                elif p.startswith("Forks:"):
                    try: current["forks"] = int(p.replace("Forks:", "").strip())
                    except ValueError: current["forks"] = 0
        elif stripped.startswith("Created:"):
            current["created"] = stripped.replace("Created:", "").strip()
        elif stripped.startswith("Last Push:") or stripped.startswith("Updated:"):
            current["updated"] = stripped.replace("Last Push:", "").replace("Updated:", "").strip()
        elif not stripped.startswith("Topics:"):
            if "    " not in line and stripped:
                if current and "name" in current:
                    repos.append(current)
                name = stripped.replace("[FORK]", "").strip()
                current = {"name": name, "fork": "[FORK]" in stripped}
            elif current and "name" in current and "desc" not in current:
                current["desc"] = stripped[:80]
    if current and "name" in current:
        repos.append(current)
    return repos[:10]


def parse_activity_data(raw):
    data = {}
    for line in raw.split("\n"):
        if ": " in line and not line.startswith("=") and not line.startswith("ACTIVITY") and not line.startswith("EVENT") and not line.startswith("RECENTLY"):
            key, val = line.strip().split(": ", 1)
            data[key.strip()] = val.strip()
    return data


# ============================================================
#  UI COMPONENTS
# ============================================================

def render_hero():
    st.markdown("""
    <div class="hero-banner">
        <div style="font-size:2rem; margin-bottom:0.3rem;">👾</div>
        <p class="hero-title">GitScope</p>
        <p class="hero-sub">Analyze any GitHub developer's profile with AI-powered multi-agent analysis</p>
    </div>
    """, unsafe_allow_html=True)


def render_profile_card(profile):
    avatar = profile.get("Avatar", "")
    name = profile.get("Name", profile.get("Username", ""))
    username = profile.get("Username", "")
    bio = profile.get("Bio", "No bio")
    location = profile.get("Location", "")
    followers = profile.get("Followers", "0")
    following = profile.get("Following", "0")
    repos = profile.get("Public Repos", "0")
    created = profile.get("Account Created", "")

    loc_html = f"📍 {location}" if location and location != "Not specified" else ""

    st.markdown(f"""<div class="profile-card">
<img src="{avatar}" class="profile-avatar" alt="avatar">
<div class="profile-name">{name}</div>
<div class="profile-username">@{username}</div>
<div class="profile-bio">"{bio}"</div>
<div style="font-size:0.85rem; color:#718096;">{loc_html}</div>
<div style="font-size:0.8rem; color:#a0aec0; margin-top:0.3rem;">Member since {created}</div>
<div class="stat-row">
<div class="stat-box"><div class="stat-num">{repos}</div><div class="stat-label">Repos</div></div>
<div class="stat-box"><div class="stat-num">{followers}</div><div class="stat-label">Followers</div></div>
<div class="stat-box"><div class="stat-num">{following}</div><div class="stat-label">Following</div></div>
</div>
</div>""", unsafe_allow_html=True)


def render_languages(langs):
    st.markdown('<div class="card-title">Language Distribution</div>', unsafe_allow_html=True)
    if not langs:
        st.info("No language data found.")
        return
    for lang, pct, count in langs[:8]:
        color = get_lang_color(lang)
        st.markdown(f"""<div class="lang-bar-container">
<div class="lang-bar-label"><span><span style="color:{color};">●</span> {lang}</span><span>{pct:.1f}% ({count} repos)</span></div>
<div class="lang-bar-bg"><div class="lang-bar-fill" style="width:{min(pct, 100)}%; background:{color};"></div></div>
</div>""", unsafe_allow_html=True)


def render_activity(activity):
    st.markdown('<div class="card-title">Activity Summary</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.8rem; color:#94a3b8; margin-bottom:0.8rem;">Personal activity only (last ~90 days)</div>', unsafe_allow_html=True)

    events = activity.get("Total Events", "0")
    days = activity.get("Active Days", "0")
    repos_active = activity.get("Repos Active In", "0")
    level = ""
    for key in activity:
        if "Activity Level" in key:
            level = activity[key]
            break

    if "VERY HIGH" in level:
        badge_class = "badge-green"
    elif "HIGH" in level:
        badge_class = "badge-blue"
    else:
        badge_class = "badge-yellow"

    st.markdown(f"""<div style="margin-bottom:1rem;">
<span class="status-badge {badge_class}">{level}</span></div>
<div class="stat-row" style="justify-content:flex-start;">
<div class="stat-box"><div class="stat-num">{events}</div><div class="stat-label">Actions</div></div>
<div class="stat-box"><div class="stat-num">{days}</div><div class="stat-label">Active Days</div></div>
<div class="stat-box"><div class="stat-num">{repos_active}</div><div class="stat-label">Repos Worked On</div></div>
</div>
<div style="margin-top:0.8rem; font-size:0.78rem; color:#94a3b8; line-height:1.8;">
📊 <strong>Actions</strong>: pushes, PRs, issues, comments by this developer<br>
📅 <strong>Active Days</strong>: days with at least one action<br>
📁 <strong>Repos Worked On</strong>: repos they personally contributed to
</div>""", unsafe_allow_html=True)


def render_repos(repos_raw):
    repos = parse_repos_data(repos_raw)
    st.markdown('<div class="card-title">Recent Repositories</div>', unsafe_allow_html=True)
    for r in repos[:6]:
        lang = r.get("language", "N/A")
        stars = r.get("stars", 0)
        forks = r.get("forks", 0)
        last_push = r.get("updated", "")
        created = r.get("created", "")
        color = get_lang_color(lang)
        fork_badge = '<span class="status-badge badge-yellow">Fork</span> ' if r.get("fork") else ""

        dates_html = ""
        if created and last_push:
            dates_html = f'<div class="repo-meta" style="margin-top:0.25rem;">📅 Created: {created} &nbsp;&nbsp;🔄 Last push (any contributor): {last_push}</div>'
        elif last_push:
            dates_html = f'<div class="repo-meta" style="margin-top:0.25rem;">🔄 Last push (any contributor): {last_push}</div>'
        elif created:
            dates_html = f'<div class="repo-meta" style="margin-top:0.25rem;">📅 Created: {created}</div>'

        st.markdown(f"""<div class="repo-card">
<span class="repo-name">{r['name']}</span> {fork_badge}
<div class="repo-meta" style="margin-top:0.4rem;">
<span style="color:{color};">●</span> {lang} &nbsp;&nbsp;⭐ {stars} &nbsp;&nbsp;🔀 {forks}
</div>{dates_html}
</div>""", unsafe_allow_html=True)


def render_agent_trace(trace, tools_called, user_tier):
    """Render the agent workflow trace panel."""
    html = ['<div class="trace-box">', '<div class="trace-header">🤖 Agent Workflow Trace</div>']

    # Tier badge
    tier_color = "#f85149" if user_tier == "not_found" else "#f0883e" if user_tier == "new" else "#3fb950"
    html.append(f'<div class="trace-line">User tier: <span style="color:{tier_color}; font-weight:700;">{user_tier.upper()}</span></div>')

    if tools_called:
        html.append(f'<div class="trace-line">Tools called: <span class="trace-detail">{len(tools_called)} ({", ".join(tools_called)})</span></div>')

    html.append('<div style="border-top:1px solid #30363d; margin:0.6rem 0;"></div>')

    for entry in trace:
        agent_name = entry.get("agent", "")
        action = entry.get("action", "")
        detail = entry.get("detail", "")

        if "REJECTED" in action:
            action_html = f'<span class="trace-rejected">{action}</span>'
        elif "APPROVED" in action:
            action_html = f'<span class="trace-approved">{action}</span>'
        else:
            action_html = f'<span class="trace-action">{action}</span>'

        detail_html = f' <span class="trace-detail">- {detail}</span>' if detail else ""

        html.append(f'<div class="trace-line"><span class="trace-agent">[{agent_name}]</span> {action_html}{detail_html}</div>')

    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


# ============================================================
#  MAIN
# ============================================================

def run_analysis(username):
    with st.status("Analyzing developer profile...", expanded=True) as status:
        st.write("🔍 Scout Agent checking profile...")

        from agent import analyze_developer
        result = analyze_developer(username)

        user_tier = result.get("user_tier", "")
        if user_tier == "not_found":
            st.error(f"User '{username}' not found on GitHub.")
            status.update(label="User not found", state="error")
            return {"not_found": True, "trace": result.get("trace", [])}

        st.write(f"📊 User tier: {user_tier.upper()}")
        tools_called = result.get("tools_called", [])
        for t in tools_called:
            st.write(f"🔧 {t}")

        revision_count = result.get("revision_count", 0)
        if revision_count > 0:
            st.write(f"🔄 Reviewer requested {revision_count} revision(s)")

        review_passed = result.get("review_passed", False)
        if review_passed:
            st.write("✅ Reviewer approved the report")

        status.update(label="Analysis complete!", state="complete")

    # Parse results
    raw_data = result.get("raw_data", {})
    report_text = result.get("report", "{}")

    try:
        analysis = json.loads(report_text)
    except json.JSONDecodeError:
        analysis = {
            "strengths": ["Active GitHub presence"],
            "tips": ["Add more documentation"],
            "score": 5,
            "score_reason": "Analysis could not be parsed.",
            "summary": "Developer profile analyzed.",
        }

    return {
        "profile_raw": raw_data.get("profile", ""),
        "repos_raw": raw_data.get("repos", ""),
        "languages_raw": raw_data.get("languages", ""),
        "activity_raw": raw_data.get("activity", ""),
        "analysis": analysis,
        "trace": result.get("trace", []),
        "tools_called": result.get("tools_called", []),
        "user_tier": user_tier,
        "revision_count": revision_count,
        "review_passed": review_passed,
    }


def main():
    render_hero()

    col_input, _ = st.columns([3, 1])
    with col_input:
        username = st.text_input(
            "GitHub Username",
            placeholder="e.g. torvalds, karpathy, sindresorhus",
            label_visibility="collapsed",
        )

    col_btn, col_reset = st.columns(2)
    with col_btn:
        analyze = st.button("🔍 Analyze Developer", use_container_width=True)
    with col_reset:
        if st.button("Start Over", use_container_width=True):
            st.rerun()

    if analyze and username:
        username = username.strip().lstrip("@")
        results = run_analysis(username)

        if results.get("not_found"):
            render_agent_trace(results.get("trace", []), [], "not_found")
            return

        profile = parse_profile_data(results["profile_raw"])
        langs = parse_language_data(results["languages_raw"])
        activity = parse_activity_data(results["activity_raw"])
        analysis = results.get("analysis", {})

        st.markdown("---")

        # Agent trace
        render_agent_trace(
            results.get("trace", []),
            results.get("tools_called", []),
            results.get("user_tier", ""),
        )

        st.markdown("---")

        # Profile + Score
        col1, col2 = st.columns([2, 1])
        with col1:
            render_profile_card(profile)
        with col2:
            score_val = analysis.get("score", 5)
            score_reason = analysis.get("score_reason", "")
            summary = analysis.get("summary", "")
            sc_class = "score-high" if score_val >= 7 else "score-mid" if score_val >= 4 else "score-low"
            st.markdown(f"""<div class="card" style="text-align:center; padding:1.5rem;">
<div class="score-circle {sc_class}">{score_val}</div>
<div style="font-size:0.85rem; color:#64748b; max-width:280px; margin:0.5rem auto;">{score_reason}</div>
<div style="font-size:0.85rem; color:#64748b; padding:0.5rem 1rem;">{summary}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Languages + Activity
        col3, col4 = st.columns(2)
        with col3:
            render_languages(langs)
        with col4:
            render_activity(activity)

        st.markdown("<br>", unsafe_allow_html=True)

        # Strengths + Tips
        col5, col6 = st.columns(2)
        with col5:
            st.markdown('<div class="card-title">Strengths</div>', unsafe_allow_html=True)
            for s in analysis.get("strengths", []):
                st.markdown(f'<div class="strength-item">{s}</div>', unsafe_allow_html=True)
        with col6:
            st.markdown('<div class="card-title">Improvement Tips</div>', unsafe_allow_html=True)
            for tip in analysis.get("tips", []):
                st.markdown(f'<div class="tip-item">{tip}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if results.get("repos_raw"):
            render_repos(results["repos_raw"])


if __name__ == "__main__":
    main()
