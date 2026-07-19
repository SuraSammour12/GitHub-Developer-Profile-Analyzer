"""
agent.py - DevPulse: Developer Activity Analyzer (ReAct Agent)

A LangGraph ReAct agent that analyzes GitHub developer profiles
using real API data and provides actionable improvement tips.
"""

import os
import json
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

from tools import all_tools

load_dotenv()


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")

llm = ChatGroq(
    model=MODEL_NAME,
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)

llm_with_tools = llm.bind_tools(all_tools)


SYSTEM_PROMPT = """You are DevPulse, a GitHub developer profile analyzer.

You analyze developers using real GitHub API data and provide detailed insights
with actionable improvement tips.

TOOLS (call them in this order for a complete analysis):
1. get_user_profile(username): Basic profile info - ALWAYS call this first
2. get_repos(username): List of repositories with stats
3. analyze_languages(username): Language distribution and diversity
4. get_activity_stats(username): Recent activity patterns
5. get_top_repos_details(username): Deep dive into best repos

WORKFLOW:
1. Start with get_user_profile to get the basics.
2. Then call get_repos, analyze_languages, get_activity_stats, and get_top_repos_details.
3. After gathering ALL data, provide a comprehensive analysis.

YOUR FINAL REPORT MUST INCLUDE:
1. PROFILE OVERVIEW: Who is this developer?
2. REPOSITORY ANALYSIS: What do they build? Quality assessment.
3. LANGUAGE SKILLS: What technologies do they use? Strengths and gaps.
4. ACTIVITY PATTERNS: How active are they? Consistency assessment.
5. STRENGTHS: What they do well (be specific, cite data).
6. IMPROVEMENT TIPS: 3-5 actionable suggestions based on the data.
7. OVERALL SCORE: Rate 1-10 with justification.

RULES:
- Always use tools first. Never guess or assume data.
- Call ALL 5 tools before writing the report.
- Be specific: "Add READMEs to your 12 repos that lack them" not "improve documentation".
- Base every observation on actual data from the tools.
- Format the report clearly with sections."""


def agent_node(state: AgentState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


def build_agent():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(all_tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile()


def analyze_developer(username: str) -> dict:
    """Run the full analysis for a GitHub username."""
    agent = build_agent()
    result = agent.invoke({
        "messages": [HumanMessage(content=f"Analyze the GitHub developer: {username}")],
    })
    return result


if __name__ == "__main__":
    import sys
    username = sys.argv[1] if len(sys.argv) > 1 else "torvalds"
    print(f"Analyzing {username}...")
    result = analyze_developer(username)
    print(result["messages"][-1].content)