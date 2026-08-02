"""
agent.py - GitScope: Multi-Agent GitHub Analyzer (v2)

Real multi-agent system where each agent makes genuine decisions:

1. Scout Agent    - fetches profile, decides user_tier (not_found / new / active)
2. Analyst Agent  - calls appropriate tools based on tier, writes report
3. Reviewer Agent - validates report quality, can request rewrite

The Scout makes a real routing decision: a new user (< 5 repos) gets a
lighter analysis than an active user (30+ repos). A not-found user stops
immediately instead of calling 4 more tools pointlessly.
"""

import os
import json
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

from tools import scout_tools, analysis_tools, all_tools

load_dotenv()


# ── Structured State ──────────────────────────────────────

class AnalysisState(TypedDict):
    messages: Annotated[list, add_messages]
    username: str
    # Scout results
    user_tier: str            # "not_found", "new", "active"
    profile_summary: str      # raw profile text
    # Analyst results
    tools_called: list        # which tools were used
    raw_data: dict            # tool name -> raw output
    report: str               # JSON report string
    # Reviewer
    review_passed: bool
    review_feedback: str
    revision_count: int
    # Trace for UI
    trace: list               # [{"agent": "...", "action": "...", "detail": "..."}, ...]
    # Routing
    next_agent: str
    last_agent: str


MAX_REVISIONS = 1
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
FALLBACK_MODEL = "llama-3.1-8b-instant"


def _get_llm(model: str | None = None) -> ChatGroq:
    return ChatGroq(
        model=model or MODEL_NAME,
        temperature=0.3,
        api_key=os.getenv("GROQ_API_KEY"),
    )


def _call_llm(messages, fallback=True):
    llm = _get_llm()
    try:
        return llm.invoke(messages)
    except Exception as e:
        if fallback and ("429" in str(e) or "rate_limit" in str(e).lower()):
            return _get_llm(FALLBACK_MODEL).invoke(messages)
        raise


def _add_trace(state, agent, action, detail=""):
    trace = list(state.get("trace", []) or [])
    trace.append({"agent": agent, "action": action, "detail": detail})
    return trace


# ═══════════════════════════════════════════════════════════
#  SUPERVISOR - routes based on structured state
# ═══════════════════════════════════════════════════════════

def supervisor(state: AnalysisState):
    user_tier = state.get("user_tier", "")
    has_report = bool(state.get("report", ""))
    review_passed = state.get("review_passed", False)
    revision_count = state.get("revision_count", 0)

    # Step 1: no tier yet → scout first
    if not user_tier:
        return {"next_agent": "scout"}

    # Step 2: user not found → stop
    if user_tier == "not_found":
        return {"next_agent": "FINISH"}

    # Step 3: no report yet → analyst
    if not has_report:
        return {"next_agent": "analyst"}

    # Step 4: report exists but not reviewed
    if has_report and not review_passed:
        if revision_count >= MAX_REVISIONS:
            return {"next_agent": "FINISH"}
        return {"next_agent": "reviewer"}

    # Step 5: done
    return {"next_agent": "FINISH"}


# ═══════════════════════════════════════════════════════════
#  SCOUT AGENT - fetches profile, decides tier
# ═══════════════════════════════════════════════════════════

def scout_agent(state: AnalysisState):
    username = state.get("username", "")
    from tools import get_user_profile

    profile_raw = get_user_profile.invoke({"username": username})

    trace = _add_trace(state, "Scout", "Fetched profile", f"@{username}")

    # Decide tier based on profile data
    if "not found" in profile_raw.lower():
        trace = _add_trace(
            {"trace": trace}, "Scout", "User not found",
            f"@{username} does not exist - stopping analysis",
        )
        return {
            "user_tier": "not_found",
            "profile_summary": profile_raw,
            "trace": trace,
            "messages": [AIMessage(content=f"Scout: User '{username}' not found.")],
        }

    # Parse repo count
    repo_count = 0
    for line in profile_raw.split("\n"):
        if "Public Repos:" in line:
            try:
                repo_count = int(line.split(":")[1].strip())
            except (ValueError, IndexError):
                pass

    if repo_count < 5:
        tier = "new"
        tier_detail = f"{repo_count} repos - lightweight analysis path"
    else:
        tier = "active"
        tier_detail = f"{repo_count} repos - full analysis with health check"

    trace = _add_trace(
        {"trace": trace}, "Scout", f"Tier: {tier.upper()}",
        tier_detail,
    )

    return {
        "user_tier": tier,
        "profile_summary": profile_raw,
        "trace": trace,
        "raw_data": {"profile": profile_raw},
        "messages": [AIMessage(content=f"Scout: {tier} user with {repo_count} repos.")],
    }


# ═══════════════════════════════════════════════════════════
#  ANALYST AGENT - calls tools based on tier, writes report
# ═══════════════════════════════════════════════════════════

def analyst_agent(state: AnalysisState):
    username = state.get("username", "")
    user_tier = state.get("user_tier", "active")
    raw_data = dict(state.get("raw_data", {}) or {})
    review_feedback = state.get("review_feedback", "")
    revision_count = state.get("revision_count", 0)

    from tools import (get_repos, analyze_languages, get_activity_stats,
                       get_top_repos_details, check_repo_health)

    trace = list(state.get("trace", []) or [])
    tools_called = list(state.get("tools_called", []) or [])

    # Only fetch data on first run (not on revision)
    if revision_count == 0:
        # Always call these
        trace.append({"agent": "Analyst", "action": "Fetching repositories", "detail": ""})
        raw_data["repos"] = get_repos.invoke({"username": username})
        tools_called.append("get_repos")

        trace.append({"agent": "Analyst", "action": "Analyzing languages", "detail": ""})
        raw_data["languages"] = analyze_languages.invoke({"username": username})
        tools_called.append("analyze_languages")

        trace.append({"agent": "Analyst", "action": "Checking activity", "detail": ""})
        raw_data["activity"] = get_activity_stats.invoke({"username": username})
        tools_called.append("get_activity_stats")

        # Only for active users: deep dive + health check
        if user_tier == "active":
            trace.append({"agent": "Analyst", "action": "Deep dive into top repos", "detail": "Active user path"})
            raw_data["top_repos"] = get_top_repos_details.invoke({"username": username})
            tools_called.append("get_top_repos_details")

            trace.append({"agent": "Analyst", "action": "Running health check", "detail": "Checking README, LICENSE, topics"})
            raw_data["health"] = check_repo_health.invoke({"username": username})
            tools_called.append("check_repo_health")
        else:
            trace.append({"agent": "Analyst", "action": "Skipped deep dive", "detail": "New user - not enough repos"})

    # Build LLM prompt
    system = (
        "You are a GitHub developer analyst. Based on the data below, write a JSON report.\n\n"
        "Return ONLY a valid JSON object with these keys:\n"
        '- "strengths": list of 3-5 specific strengths (cite actual data: repo names, numbers)\n'
        '- "tips": list of 3-5 actionable tips (be specific: name repos, give numbers)\n'
        '- "score": integer 1-10\n'
        '- "score_reason": one sentence explaining the score\n'
        '- "summary": 2-3 sentence overview\n\n'
        "RULES:\n"
        "- Every strength must reference specific data (repo names, star counts, etc.)\n"
        "- Every tip must be actionable and specific (name which repos need what)\n"
        "- Score must reflect the actual data, not be generous\n"
        "- No markdown, no backticks, just pure JSON\n"
    )

    data_sections = []
    for key in ["profile", "repos", "languages", "activity", "top_repos", "health"]:
        if key in raw_data:
            data_sections.append(raw_data[key])

    prompt = "\n\n".join(data_sections)

    if review_feedback and revision_count > 0:
        prompt += (
            f"\n\n--- REVISION REQUEST ---\n"
            f"Your previous report was rejected. Fix these issues:\n"
            f"{review_feedback}\n"
            f"Write a COMPLETELY REVISED report addressing ALL feedback.\n"
        )

    response = _call_llm([
        SystemMessage(content=system),
        HumanMessage(content=prompt),
    ])

    report_text = response.content.strip()
    if "```" in report_text:
        report_text = report_text.split("```")[1]
        if report_text.startswith("json"):
            report_text = report_text[4:]
        report_text = report_text.strip()

    action = "Revised report" if revision_count > 0 else "Generated report"
    trace.append({"agent": "Analyst", "action": action, "detail": f"Tools used: {len(tools_called)}"})

    return {
        "raw_data": raw_data,
        "tools_called": tools_called,
        "report": report_text,
        "review_passed": False,
        "trace": trace,
        "messages": [AIMessage(content=f"Analyst: Report {'revised' if revision_count > 0 else 'generated'}.")],
    }


# ═══════════════════════════════════════════════════════════
#  REVIEWER AGENT - validates report quality
# ═══════════════════════════════════════════════════════════

def reviewer_agent(state: AnalysisState):
    report = state.get("report", "")
    revision_count = state.get("revision_count", 0)
    user_tier = state.get("user_tier", "")
    trace = list(state.get("trace", []) or [])

    # First validate JSON
    try:
        parsed = json.loads(report)
    except json.JSONDecodeError:
        trace.append({"agent": "Reviewer", "action": "REJECTED", "detail": "Invalid JSON format"})
        return {
            "review_passed": False,
            "review_feedback": "Report is not valid JSON. Return ONLY a JSON object.",
            "revision_count": revision_count + 1,
            "trace": trace,
            "messages": [AIMessage(content="Reviewer: REJECTED - invalid JSON")],
        }

    # Check required keys
    required = ["strengths", "tips", "score", "score_reason", "summary"]
    missing = [k for k in required if k not in parsed]
    if missing:
        feedback = f"Missing required keys: {', '.join(missing)}"
        trace.append({"agent": "Reviewer", "action": "REJECTED", "detail": feedback})
        return {
            "review_passed": False,
            "review_feedback": feedback,
            "revision_count": revision_count + 1,
            "trace": trace,
            "messages": [AIMessage(content=f"Reviewer: REJECTED - {feedback}")],
        }

    # Use LLM for quality check
    system = (
        "You are a quality reviewer for GitHub developer analysis reports.\n"
        "Check if the report meets these criteria:\n\n"
        "1. SPECIFICITY: Do strengths cite actual data (repo names, numbers)?\n"
        "   Bad: 'Active developer' - Good: 'nanochat has 56,388 stars'\n"
        "2. ACTIONABLE TIPS: Are tips specific enough to act on?\n"
        "   Bad: 'Improve documentation' - Good: 'Add README to repo-x and repo-y'\n"
        "3. SCORE ACCURACY: Does the score match the data?\n"
        "4. NO HALLUCINATION: Are all mentioned repos/numbers real?\n\n"
        "Respond in JSON: {\"verdict\": \"PASS\" or \"REVISE\", \"feedback\": \"...\"}\n"
    )

    response = _call_llm([
        SystemMessage(content=system),
        HumanMessage(content=f"Review this report:\n{report}"),
    ])

    raw = response.content.strip()
    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)
        verdict = result.get("verdict", "PASS").upper()
        feedback = result.get("feedback", "")
    except (json.JSONDecodeError, IndexError):
        verdict = "PASS"
        feedback = "Report meets quality standards."

    passed = verdict == "PASS"

    if passed:
        trace.append({"agent": "Reviewer", "action": "APPROVED", "detail": feedback[:100]})
    else:
        trace.append({"agent": "Reviewer", "action": "REJECTED", "detail": feedback[:100]})

    return {
        "review_passed": passed,
        "review_feedback": feedback if not passed else "",
        "revision_count": revision_count + (0 if passed else 1),
        "trace": trace,
        "messages": [AIMessage(content=f"Reviewer: {verdict} - {feedback[:80]}")],
    }


# ═══════════════════════════════════════════════════════════
#  ROUTING
# ═══════════════════════════════════════════════════════════

def route_supervisor(state: AnalysisState) -> str:
    nxt = state.get("next_agent", "FINISH")
    if nxt in ("scout", "analyst", "reviewer"):
        return nxt
    return END


# ═══════════════════════════════════════════════════════════
#  BUILD GRAPH
# ═══════════════════════════════════════════════════════════

def build_agent():
    graph = StateGraph(AnalysisState)

    graph.add_node("supervisor", supervisor)
    graph.add_node("scout", scout_agent)
    graph.add_node("analyst", analyst_agent)
    graph.add_node("reviewer", reviewer_agent)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", route_supervisor)
    graph.add_edge("scout", "supervisor")
    graph.add_edge("analyst", "supervisor")
    graph.add_edge("reviewer", "supervisor")

    return graph.compile()


def analyze_developer(username: str) -> dict:
    agent = build_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"Analyze: {username}")],
        "username": username,
        "user_tier": "",
        "profile_summary": "",
        "tools_called": [],
        "raw_data": {},
        "report": "",
        "review_passed": False,
        "review_feedback": "",
        "revision_count": 0,
        "trace": [],
        "next_agent": "",
        "last_agent": "",
    })
    return result
