"""
test_tools.py - Tests for DevPulse GitHub analysis tools.
Unit tests (mocked) + Live API tests.
"""

import pytest
from unittest.mock import patch, MagicMock
from langgraph.graph import END

import tools
import agent


class TestGetUserProfile:
    @patch("tools._github_get")
    def test_valid_user(self, mock_get):
        mock_get.return_value = (200, {
            "login": "testuser", "name": "Test User",
            "bio": "A developer", "location": "NYC",
            "company": "TestCo", "followers": 100,
            "following": 50, "public_repos": 30,
            "created_at": "2020-01-15T00:00:00Z",
            "avatar_url": "https://example.com/avatar.jpg",
            "blog": "https://test.com",
            "twitter_username": "testuser", "hireable": True,
        })
        result = tools.get_user_profile.invoke({"username": "testuser"})
        assert "testuser" in result
        assert "Test User" in result

    @patch("tools._github_get")
    def test_user_not_found(self, mock_get):
        mock_get.return_value = (404, None)
        result = tools.get_user_profile.invoke({"username": "nonexistent"})
        assert "not found" in result


class TestGetRepos:
    @patch("tools._github_get")
    def test_returns_repos(self, mock_get):
        mock_get.return_value = (200, [
            {"name": "my-project", "description": "A cool project",
             "stargazers_count": 42, "forks_count": 10,
             "language": "Python", "updated_at": "2025-06-01T00:00:00Z",
             "fork": False, "topics": ["ai"]},
        ])
        result = tools.get_repos.invoke({"username": "testuser"})
        assert "my-project" in result
        assert "Python" in result


class TestAnalyzeLanguages:
    @patch("tools._github_get")
    def test_language_distribution(self, mock_get):
        mock_get.return_value = (200, [
            {"language": "Python", "size": 5000},
            {"language": "JavaScript", "size": 2000},
        ])
        result = tools.analyze_languages.invoke({"username": "testuser"})
        assert "Python" in result
        assert "JavaScript" in result


class TestGetActivityStats:
    @patch("tools._github_get")
    def test_activity_summary(self, mock_get):
        mock_get.return_value = (200, [
            {"type": "PushEvent", "created_at": "2025-06-15T10:00:00Z",
             "repo": {"name": "user/repo1"},
             "payload": {"commits": [{"sha": "abc"}]}},
        ])
        result = tools.get_activity_stats.invoke({"username": "testuser"})
        assert "Push Events: 1" in result


class TestAgentRouting:
    def test_tool_calls_continue(self):
        mock_msg = MagicMock()
        mock_msg.tool_calls = [{"name": "get_user_profile"}]
        state = {"messages": [mock_msg]}
        assert agent.should_continue(state) == "tools"

    def test_no_tool_calls_ends(self):
        mock_msg = MagicMock()
        mock_msg.tool_calls = []
        state = {"messages": [mock_msg]}
        assert agent.should_continue(state) == END

    def test_graph_compiles(self):
        app = agent.build_agent()
        assert app is not None


class TestLiveGitHubAPI:
    """Real API tests. Skip with: pytest -k 'not Live' """

    def test_live_profile_torvalds(self):
        result = tools.get_user_profile.invoke({"username": "torvalds"})
        assert "torvalds" in result

    def test_live_profile_not_found(self):
        result = tools.get_user_profile.invoke({"username": "zzzxxx999notreal888"})
        assert "not found" in result