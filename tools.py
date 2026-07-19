"""
tools.py - DevPulse: GitHub Developer Activity Analysis Tools

Each tool queries the real GitHub API (api.github.com) to analyze
a developer's profile, repositories, languages, and activity patterns.

All endpoints are public and free (60 requests/hour without auth).
"""

import urllib.request
import urllib.error
import json
from datetime import datetime, timezone
from langchain_core.tools import tool


def _github_get(endpoint: str) -> tuple[int, dict | list | None]:
    """Make a GET request to the GitHub API. Returns (status, parsed_json)."""
    url = f"https://api.github.com{endpoint}"
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "DevPulse/1.0",
            "Accept": "application/vnd.github.v3+json",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return resp.status, data
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, None


def _time_ago(date_str: str) -> str:
    """Convert an ISO date string to a human-readable 'time ago' format."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = now - dt
        days = diff.days
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        if days < 30:
            return f"{days} days ago"
        if days < 365:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    except Exception:
        return date_str


@tool
def get_user_profile(username: str) -> str:
    """Get a GitHub user's profile information.
    Use this FIRST when analyzing a developer.
    Returns: name, bio, location, followers, following, public repos count, and account age.
    """
    status, data = _github_get(f"/users/{username}")

    if status == 404:
        return f"User '{username}' not found on GitHub."
    if status != 200 or not data:
        return f"Error fetching profile for '{username}' (HTTP {status})."

    name = data.get("name") or username
    bio = data.get("bio") or "No bio"
    location = data.get("location") or "Not specified"
    company = data.get("company") or "Not specified"
    followers = data.get("followers", 0)
    following = data.get("following", 0)
    public_repos = data.get("public_repos", 0)
    created = data.get("created_at", "")
    avatar = data.get("avatar_url", "")
    blog = data.get("blog") or "None"
    twitter = data.get("twitter_username") or "None"
    hireable = data.get("hireable")

    account_age = _time_ago(created) if created else "Unknown"

    lines = [
        "GITHUB PROFILE",
        "=" * 40,
        f"Username: {username}",
        f"Name: {name}",
        f"Bio: {bio}",
        f"Location: {location}",
        f"Company: {company}",
        f"Blog: {blog}",
        f"Twitter: {twitter}",
        f"Hireable: {'Yes' if hireable else 'No' if hireable is False else 'Not specified'}",
        "",
        f"Followers: {followers}",
        f"Following: {following}",
        f"Public Repos: {public_repos}",
        f"Account Created: {created[:10] if created else 'Unknown'} ({account_age})",
        f"Avatar: {avatar}",
    ]

    return "\n".join(lines)


@tool
def get_repos(username: str) -> str:
    """Get a user's public repositories sorted by most recently updated.
    Returns: repo names, descriptions, stars, forks, language, and last update.
    Limited to the 30 most recently updated repos.
    """
    status, data = _github_get(f"/users/{username}/repos?sort=updated&per_page=30")

    if status == 404:
        return f"User '{username}' not found."
    if status != 200 or not data:
        return f"Error fetching repos for '{username}' (HTTP {status})."
    if not data:
        return f"User '{username}' has no public repositories."

    total_stars = sum(r.get("stargazers_count", 0) for r in data)
    total_forks = sum(r.get("forks_count", 0) for r in data)
    forked_count = sum(1 for r in data if r.get("fork", False))
    original_count = len(data) - forked_count

    lines = [
        f"REPOSITORIES FOR {username}",
        "=" * 40,
        f"Showing: {len(data)} repos (sorted by last updated)",
        f"Total Stars: {total_stars} | Total Forks: {total_forks}",
        f"Original: {original_count} | Forked: {forked_count}",
        "",
    ]

    for r in data:
        name = r.get("name", "")
        desc = r.get("description") or "No description"
        stars = r.get("stargazers_count", 0)
        forks = r.get("forks_count", 0)
        lang = r.get("language") or "Not specified"
        updated = r.get("updated_at", "")
        is_fork = r.get("fork", False)
        topics = r.get("topics", [])

        lines.append(f"  {name} {'[FORK]' if is_fork else ''}")
        lines.append(f"    {desc[:80]}")
        lines.append(f"    Language: {lang} | Stars: {stars} | Forks: {forks}")
        lines.append(f"    Updated: {_time_ago(updated)}")
        if topics:
            lines.append(f"    Topics: {', '.join(topics[:5])}")
        lines.append("")

    return "\n".join(lines)


@tool
def analyze_languages(username: str) -> str:
    """Analyze the programming languages used across all of a user's repos.
    Returns: language distribution (percentage), primary language, and diversity score.
    """
    status, repos = _github_get(f"/users/{username}/repos?per_page=100")

    if status != 200 or not repos:
        return f"Error fetching repos for '{username}'."

    lang_count = {}
    lang_bytes = {}
    repos_with_lang = 0

    for r in repos:
        lang = r.get("language")
        if lang:
            repos_with_lang += 1
            lang_count[lang] = lang_count.get(lang, 0) + 1
            size = r.get("size", 0)
            lang_bytes[lang] = lang_bytes.get(lang, 0) + size

    if not lang_count:
        return f"No language data found for '{username}'."

    total_repos = len(repos)
    total_bytes = sum(lang_bytes.values())

    sorted_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)

    lines = [
        f"LANGUAGE ANALYSIS FOR {username}",
        "=" * 40,
        f"Total Repos Analyzed: {total_repos}",
        f"Repos with Language Data: {repos_with_lang}",
        f"Unique Languages: {len(lang_count)}",
        "",
        "LANGUAGE DISTRIBUTION:",
        "",
    ]

    for lang, bytes_val in sorted_langs:
        pct = (bytes_val / total_bytes * 100) if total_bytes > 0 else 0
        repo_count = lang_count.get(lang, 0)
        bar = "#" * int(pct / 2)
        lines.append(f"  {lang:<15} {pct:5.1f}%  {bar}  ({repo_count} repos)")

    primary = sorted_langs[0][0] if sorted_langs else "None"
    diversity = len(lang_count)

    lines.append("")
    lines.append(f"Primary Language: {primary}")

    if diversity >= 7:
        lines.append(f"Diversity Score: HIGH ({diversity} languages) - Full-stack / polyglot developer")
    elif diversity >= 4:
        lines.append(f"Diversity Score: MEDIUM ({diversity} languages) - Versatile developer")
    else:
        lines.append(f"Diversity Score: LOW ({diversity} languages) - Specialized developer")

    return "\n".join(lines)


@tool
def get_activity_stats(username: str) -> str:
    """Get recent activity and contribution patterns for a GitHub user.
    Analyzes: recent events, active days, event types, and activity level.
    """
    status, events = _github_get(f"/users/{username}/events/public?per_page=100")

    if status != 200 or not events:
        return f"No recent activity found for '{username}' (or API error)."

    event_types = {}
    active_days = set()
    repos_active = set()
    push_count = 0
    pr_count = 0
    issue_count = 0
    total_commits = 0

    for e in events:
        etype = e.get("type", "Unknown")
        event_types[etype] = event_types.get(etype, 0) + 1

        created = e.get("created_at", "")
        if created:
            day = created[:10]
            active_days.add(day)

        repo = e.get("repo", {}).get("name", "")
        if repo:
            repos_active.add(repo)

        if etype == "PushEvent":
            push_count += 1
            commits = e.get("payload", {}).get("commits", [])
            total_commits += len(commits)
        elif etype == "PullRequestEvent":
            pr_count += 1
        elif etype == "IssuesEvent":
            issue_count += 1

    sorted_days = sorted(active_days)
    date_range = f"{sorted_days[0]} to {sorted_days[-1]}" if sorted_days else "N/A"

    lines = [
        f"ACTIVITY STATS FOR {username}",
        "=" * 40,
        f"Period: {date_range}",
        f"Total Events: {len(events)}",
        f"Active Days: {len(active_days)}",
        f"Repos Active In: {len(repos_active)}",
        "",
        "ACTIVITY BREAKDOWN:",
        f"  Push Events: {push_count} ({total_commits} commits)",
        f"  Pull Requests: {pr_count}",
        f"  Issues: {issue_count}",
        "",
        "EVENT TYPES:",
    ]

    for etype, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {etype}: {count}")

    lines.append("")
    lines.append("RECENTLY ACTIVE REPOS:")
    for repo in list(repos_active)[:10]:
        lines.append(f"  {repo}")

    lines.append("")
    if len(active_days) >= 20:
        lines.append("Activity Level: VERY HIGH - Active almost daily")
    elif len(active_days) >= 10:
        lines.append("Activity Level: HIGH - Regular contributor")
    elif len(active_days) >= 5:
        lines.append("Activity Level: MODERATE - Occasional contributor")
    else:
        lines.append("Activity Level: LOW - Infrequent activity")

    return "\n".join(lines)


@tool
def get_top_repos_details(username: str) -> str:
    """Get detailed stats for a user's top repositories (by stars).
    Returns: stars, forks, open issues, license, creation date, and recent activity.
    Use this after get_repos to dive deeper into the most popular projects.
    """
    status, repos = _github_get(f"/users/{username}/repos?sort=stars&per_page=10&direction=desc")

    if status != 200 or not repos:
        return f"Error fetching top repos for '{username}'."

    starred = [r for r in repos if r.get("stargazers_count", 0) > 0]
    if not starred:
        starred = repos[:5]

    lines = [
        f"TOP REPOSITORIES FOR {username}",
        "=" * 40,
    ]

    for r in starred[:5]:
        name = r.get("name", "")
        desc = r.get("description") or "No description"
        stars = r.get("stargazers_count", 0)
        forks = r.get("forks_count", 0)
        issues = r.get("open_issues_count", 0)
        lang = r.get("language") or "N/A"
        license_info = r.get("license")
        license_name = license_info.get("spdx_id", "None") if license_info else "None"
        created = r.get("created_at", "")[:10]
        updated = r.get("updated_at", "")
        is_fork = r.get("fork", False)
        watchers = r.get("watchers_count", 0)
        default_branch = r.get("default_branch", "main")

        lines.append("")
        lines.append(f"  {name} {'[FORK]' if is_fork else ''}")
        lines.append(f"    {desc[:100]}")
        lines.append(f"    Stars: {stars} | Forks: {forks} | Watchers: {watchers}")
        lines.append(f"    Open Issues: {issues} | License: {license_name}")
        lines.append(f"    Language: {lang} | Branch: {default_branch}")
        lines.append(f"    Created: {created} | Updated: {_time_ago(updated)}")

    return "\n".join(lines)


all_tools = [get_user_profile, get_repos, analyze_languages, get_activity_stats, get_top_repos_details]