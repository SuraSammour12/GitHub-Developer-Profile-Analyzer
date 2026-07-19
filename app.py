"""
app.py - GitScope: Streamlit UI

Elegant developer profile analyzer with real GitHub data.
Run: streamlit run app.py
"""

import streamlit as st
import json
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="GitScope",
    page_icon="👾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from tools import (
    get_user_profile,
    get_repos,
    analyze_languages,
    get_activity_stats,
    get_top_repos_details,
)


# ============================================================
#  CUSTOM CSS
# ============================================================

st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Kill ALL top spacing */
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
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f0f6fc;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-sub {
        color: #8b949e;
        font-size: 1rem;
        margin-top: 0.4rem;
        line-height: 1.5;
    }
    .hero-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    .card {
        background: #ffffff;
        border: 1px solid #e8e8e8;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.8rem;
    }

    .profile-card {
        background: linear-gradient(135deg, #f8fafc, #f0f4f8);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
    }
    .profile-avatar {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        border: 3px solid #e2e8f0;
        margin: 0 auto 1rem;
    }
    .profile-name {
        font-size: 1.4rem;
        font-weight: 700;
        color: #1a202c;
        margin: 0;
    }
    .profile-username { color: #718096; font-size: 0.95rem; }
    .profile-bio {
        color: #4a5568;
        font-size: 0.9rem;
        margin: 0.8rem 0;
        font-style: italic;
    }

    .stat-row {
        display: flex;
        justify-content: center;
        gap: 1.2rem;
        margin-top: 1rem;
        flex-wrap: wrap;
    }
    .stat-box {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.7rem 1.2rem;
        text-align: center;
        min-width: 80px;
    }
    .stat-num { font-size: 1.3rem; font-weight: 700; color: #2d3748; }
    .stat-label {
        font-size: 0.7rem;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .score-container { text-align: center; padding: 1.5rem; }
    .score-circle {
        width: 100px; height: 100px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 2.2rem;
        font-weight: 800;
        color: white;
        margin-bottom: 0.8rem;
    }
    .score-high { background: linear-gradient(135deg, #22c55e, #16a34a); }
    .score-mid { background: linear-gradient(135deg, #f59e0b, #d97706); }
    .score-low { background: linear-gradient(135deg, #ef4444, #dc2626); }

    .lang-bar-container { margin: 0.4rem 0; }
    .lang-bar-label {
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        margin-bottom: 2px;
    }
    .lang-bar-bg {
        background: #f1f5f9;
        border-radius: 6px;
        height: 8px;
        overflow: hidden;
    }
    .lang-bar-fill {
        height: 100%;
        border-radius: 6px;
        transition: width 0.5s ease;
    }

    .tip-item {
        background: #f0fdf4;
        border-left: 3px solid #22c55e;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
        color: #166534;
    }

    .strength-item {
        background: #eff6ff;
        border-left: 3px solid #3b82f6;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
        color: #1e40af;
    }

    .status-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.3px;
    }
    .badge-green { background: #dcfce7; color: #166534; }
    .badge-yellow { background: #fef3c7; color: #92400e; }
    .badge-blue { background: #dbeafe; color: #1e40af; }

    .repo-card {
        background: #fafbfc;
        border: 1px solid #e8e8e8;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
    }
    .repo-name { font-weight: 600; color: #0969da; font-size: 0.95rem; }
    .repo-meta { font-size: 0.75rem; color: #8b949e; }

    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 1px solid #d1d5db;
        padding: 0.7rem 1rem;
        font-size: 1rem;
    }
    .stButton > button {
        background: #0d1117;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.65rem 2rem;
        font-weight: 600;
        font-size: 0.95rem;
        width: 100%;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background: #30363d;
        color: white;
    }
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
    "Jupyter Notebook": "#DA5B0B", "Vue": "#41b883", "Scala": "#c22d40",
}


def get_lang_color(lang):
    return LANG_COLORS.get(lang, "#6e7781")


def parse_profile_data(raw: str) -> dict:
    data = {}
    for line in raw.split("\n"):
        if ": " in line and not line.startswith("="):
            key, val = line.split(": ", 1)
            data[key.strip()] = val.strip()
    return data


def parse_language_data(raw: str) -> list[tuple[str, float, int]]:
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


def parse_repos_data(raw: str) -> list[dict]:
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
                    try:
                        current["stars"] = int(p.replace("Stars:", "").strip())
                    except ValueError:
                        current["stars"] = 0
                elif p.startswith("Forks:"):
                    try:
                        current["forks"] = int(p.replace("Forks:", "").strip())
                    except ValueError:
                        current["forks"] = 0
        elif stripped.startswith("Updated:"):
            current["updated"] = stripped.replace("Updated:", "").strip()
        elif stripped.startswith("Topics:"):
            pass
        elif not stripped.startswith("Language:") and not stripped.startswith("Updated:"):
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


def parse_activity_data(raw: str) -> dict:
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
    icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
    icon_html = ""
    if os.path.exists(icon_path):
        import base64
        with open(icon_path, "rb") as f:
            icon_b64 = base64.b64encode(f.read()).decode()
        icon_html = f'<img src="data:image/png;base64,{icon_b64}" style="width:48px; height:48px; border-radius:10px; margin-bottom:0.5rem;">'
    else:
        icon_html = '<div style="font-size:2rem; margin-bottom:0.3rem;">&#x1F47E;</div>'

    st.markdown(f"""
    <div class="hero-banner">
        {icon_html}
        <p class="hero-title">GitScope</p>
        <p class="hero-sub">
            Analyze any GitHub developer's profile, repositories, languages, and activity patterns.
            Get actionable insights and improvement tips backed by real data.
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_profile_card(profile: dict):
    avatar = profile.get("Avatar", "")
    name = profile.get("Name", profile.get("Username", ""))
    username = profile.get("Username", "")
    bio = profile.get("Bio", "No bio")
    location = profile.get("Location", "")
    company = profile.get("Company", "")
    followers = profile.get("Followers", "0")
    following = profile.get("Following", "0")
    repos = profile.get("Public Repos", "0")
    created = profile.get("Account Created", "")

    loc_html = f"&#x1F4CD; {location}" if location and location != "Not specified" else ""
    comp_html = f" &#x1F3E2; {company}" if company and company != "Not specified" else ""

    html = f"""<div class="profile-card">
<img src="{avatar}" class="profile-avatar" alt="avatar">
<div class="profile-name">{name}</div>
<div class="profile-username">@{username}</div>
<div class="profile-bio">"{bio}"</div>
<div style="font-size:0.85rem; color:#718096;">{loc_html}{comp_html}</div>
<div style="font-size:0.8rem; color:#a0aec0; margin-top:0.3rem;">Member since {created}</div>
<div class="stat-row">
<div class="stat-box"><div class="stat-num">{repos}</div><div class="stat-label">Repos</div></div>
<div class="stat-box"><div class="stat-num">{followers}</div><div class="stat-label">Followers</div></div>
<div class="stat-box"><div class="stat-num">{following}</div><div class="stat-label">Following</div></div>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


def render_languages(langs):
    st.markdown('<div class="card-title">Language Distribution</div>', unsafe_allow_html=True)
    if not langs:
        st.info("No language data found.")
        return
    for lang, pct, count in langs[:8]:
        color = get_lang_color(lang)
        st.markdown(f"""
        <div class="lang-bar-container">
            <div class="lang-bar-label">
                <span><span style="color:{color};">&#9679;</span> {lang}</span>
                <span>{pct:.1f}% ({count} repos)</span>
            </div>
            <div class="lang-bar-bg">
                <div class="lang-bar-fill" style="width:{min(pct, 100)}%; background:{color};"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_score(score, reason):
    if score >= 7:
        css_class = "score-high"
    elif score >= 4:
        css_class = "score-mid"
    else:
        css_class = "score-low"
    st.markdown(f"""
    <div class="score-container">
        <div class="score-circle {css_class}">{score}</div>
        <p style="font-size:0.85rem; color:#64748b; max-width:280px; margin:0 auto;">{reason}</p>
    </div>
    """, unsafe_allow_html=True)


def render_tips(tips):
    st.markdown('<div class="card-title">Improvement Tips</div>', unsafe_allow_html=True)
    for tip in tips:
        st.markdown(f'<div class="tip-item">{tip}</div>', unsafe_allow_html=True)


def render_strengths(strengths):
    st.markdown('<div class="card-title">Strengths</div>', unsafe_allow_html=True)
    for s in strengths:
        st.markdown(f'<div class="strength-item">{s}</div>', unsafe_allow_html=True)


def render_repos(repos_raw):
    repos = parse_repos_data(repos_raw)
    st.markdown('<div class="card-title">Recent Repositories</div>', unsafe_allow_html=True)
    for r in repos[:6]:
        lang = r.get("language", "N/A")
        stars = r.get("stars", 0)
        forks = r.get("forks", 0)
        updated = r.get("updated", "")
        color = get_lang_color(lang)
        fork_badge = '<span class="status-badge badge-yellow">Fork</span> ' if r.get("fork") else ""
        st.markdown(f"""
        <div class="repo-card">
            <span class="repo-name">{r['name']}</span> {fork_badge}
            <div class="repo-meta" style="margin-top:0.4rem;">
                <span style="color:{color};">&#9679;</span> {lang}
                &nbsp;&nbsp;&#11088; {stars}
                &nbsp;&nbsp;&#x1F500; {forks}
                &nbsp;&nbsp;&#x1F552; {updated}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_activity(activity):
    st.markdown('<div class="card-title">Activity Summary</div>', unsafe_allow_html=True)
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

    level_short = level.split(" - ")[0] if " - " in level else level

    st.markdown(f"""
    <div style="margin-bottom:1rem;">
        <span class="status-badge {badge_class}">{level_short}</span>
    </div>
    <div class="stat-row" style="justify-content:flex-start;">
        <div class="stat-box">
            <div class="stat-num">{events}</div>
            <div class="stat-label">Events</div>
        </div>
        <div class="stat-box">
            <div class="stat-num">{days}</div>
            <div class="stat-label">Active Days</div>
        </div>
        <div class="stat-box">
            <div class="stat-num">{repos_active}</div>
            <div class="stat-label">Active Repos</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
#  MAIN APP
# ============================================================

def run_analysis(username):
    results = {}

    with st.status("Analyzing developer profile...", expanded=True) as status:
        st.write("Fetching profile...")
        results["profile_raw"] = get_user_profile.invoke({"username": username})
        if "not found" in results["profile_raw"]:
            st.error(f"User '{username}' not found on GitHub.")
            return None

        st.write("Fetching repositories...")
        results["repos_raw"] = get_repos.invoke({"username": username})

        st.write("Analyzing languages...")
        results["languages_raw"] = analyze_languages.invoke({"username": username})

        st.write("Checking activity patterns...")
        results["activity_raw"] = get_activity_stats.invoke({"username": username})

        st.write("Getting top repo details...")
        results["top_repos_raw"] = get_top_repos_details.invoke({"username": username})

        st.write("Generating AI analysis...")
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage

        analysis_llm = ChatGroq(
            model=os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=0.3,
            api_key=os.getenv("GROQ_API_KEY"),
        )

        prompt = f"""Analyze this GitHub developer and return a JSON report.

PROFILE:
{results['profile_raw']}

REPOSITORIES:
{results['repos_raw']}

LANGUAGES:
{results['languages_raw']}

ACTIVITY:
{results['activity_raw']}

TOP REPOS:
{results['top_repos_raw']}

Return ONLY a valid JSON object with these keys:
- "strengths": list of 3-5 specific strengths (based on the data)
- "tips": list of 3-5 actionable improvement tips (specific, cite numbers)
- "score": integer 1-10
- "score_reason": one sentence explaining the score
- "summary": 2-3 sentence overview of this developer

No markdown, no backticks, just pure JSON."""

        try:
            response = analysis_llm.invoke([HumanMessage(content=prompt)])
            text = response.content.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            results["analysis"] = json.loads(text)
        except Exception:
            results["analysis"] = {
                "strengths": ["Active GitHub presence", "Multiple repositories"],
                "tips": ["Add more README documentation", "Contribute to open source projects"],
                "score": 5,
                "score_reason": "Analysis could not be generated automatically.",
                "summary": "Developer profile analyzed from GitHub data.",
            }

        status.update(label="Analysis complete!", state="complete")

    return results


def main():
    render_hero()

    col_input, _ = st.columns([3, 1])
    with col_input:
        username = st.text_input(
            "GitHub Username",
            placeholder="e.g. torvalds, gaearon, sindresorhus",
            label_visibility="collapsed",
        )

    col_btn, col_reset = st.columns(2)
    with col_btn:
        analyze = st.button("Analyze Developer", use_container_width=True)
    with col_reset:
        if st.button("Start Over", use_container_width=True):
            st.rerun()

    if analyze and username:
        username = username.strip().lstrip("@")
        results = run_analysis(username)

        if results is None:
            return

        profile = parse_profile_data(results["profile_raw"])
        langs = parse_language_data(results["languages_raw"])
        activity = parse_activity_data(results["activity_raw"])
        analysis = results.get("analysis", {})

        st.markdown("---")

        col1, col2 = st.columns([2, 1])
        with col1:
            render_profile_card(profile)
        with col2:
            score_val = analysis.get("score", 5)
            score_reason = analysis.get("score_reason", "")
            summary = analysis.get("summary", "")
            if score_val >= 7:
                sc_class = "score-high"
            elif score_val >= 4:
                sc_class = "score-mid"
            else:
                sc_class = "score-low"
            score_html = f"""<div class="card" style="text-align:center; padding:1.5rem;">
<div class="score-circle {sc_class}">{score_val}</div>
<div style="font-size:0.85rem; color:#64748b; max-width:280px; margin:0.5rem auto;">{score_reason}</div>
<div style="font-size:0.85rem; color:#64748b; padding:0.5rem 1rem;">{summary}</div>
</div>"""
            st.markdown(score_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        with col3:
            render_languages(langs)
        with col4:
            render_activity(activity)

        st.markdown("<br>", unsafe_allow_html=True)

        col5, col6 = st.columns(2)
        with col5:
            render_strengths(analysis.get("strengths", []))
        with col6:
            render_tips(analysis.get("tips", []))

        st.markdown("<br>", unsafe_allow_html=True)

        render_repos(results["repos_raw"])


if __name__ == "__main__":
    main()