"""Tests for GitScope - tools, routing, and agent structure."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from unittest.mock import patch, MagicMock

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


class TestCheckRepoHealth:
    @patch("tools._github_get")
    def test_health_check(self, mock_get):
        def side_effect(endpoint):
            if "/repos?" in endpoint:
                return (200, [
                    {"name": "repo1", "description": "Has desc",
                     "license": {"spdx_id": "MIT"}, "topics": ["python"],
                     "fork": False},
                    {"name": "repo2", "description": None,
                     "license": None, "topics": [],
                     "fork": False},
                ])
            elif "/readme" in endpoint:
                if "repo1" in endpoint:
                    return (200, {})
                return (404, None)
            return (200, {})

        mock_get.side_effect = side_effect
        result = tools.check_repo_health.invoke({"username": "testuser"})
        assert "HEALTH CHECK" in result
        assert "repo2" in result  # should appear in missing lists


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


class TestSupervisorRouting:
    def test_routes_to_scout_first(self):
        state = {"user_tier": "", "report": "", "review_passed": False, "revision_count": 0}
        result = agent.supervisor(state)
        assert result["next_agent"] == "scout"

    def test_stops_on_not_found(self):
        state = {"user_tier": "not_found", "report": "", "review_passed": False, "revision_count": 0}
        result = agent.supervisor(state)
        assert result["next_agent"] == "FINISH"

    def test_routes_to_analyst_after_scout(self):
        state = {"user_tier": "active", "report": "", "review_passed": False, "revision_count": 0}
        result = agent.supervisor(state)
        assert result["next_agent"] == "analyst"

    def test_routes_to_reviewer_after_report(self):
        state = {"user_tier": "active", "report": '{"score": 7}', "review_passed": False, "revision_count": 0}
        result = agent.supervisor(state)
        assert result["next_agent"] == "reviewer"

    def test_finishes_after_review_passed(self):
        state = {"user_tier": "active", "report": '{"score": 7}', "review_passed": True, "revision_count": 0}
        result = agent.supervisor(state)
        assert result["next_agent"] == "FINISH"

    def test_finishes_after_max_revisions(self):
        state = {"user_tier": "active", "report": '{"score": 7}', "review_passed": False, "revision_count": agent.MAX_REVISIONS}
        result = agent.supervisor(state)
        assert result["next_agent"] == "FINISH"


class TestScoutAgent:
    @patch("tools._github_get")
    def test_scout_not_found(self, mock_get):
        mock_get.return_value = (404, None)
        state = {"username": "nonexistent", "trace": [], "raw_data": {}}
        result = agent.scout_agent(state)
        assert result["user_tier"] == "not_found"

    @patch("tools._github_get")
    def test_scout_new_user(self, mock_get):
        mock_get.return_value = (200, {
            "login": "newbie", "name": "Newbie", "bio": "", "location": "",
            "company": "", "followers": 2, "following": 5, "public_repos": 3,
            "created_at": "2025-01-01T00:00:00Z", "avatar_url": "",
            "blog": "", "twitter_username": "", "hireable": None,
        })
        state = {"username": "newbie", "trace": [], "raw_data": {}}
        result = agent.scout_agent(state)
        assert result["user_tier"] == "new"

    @patch("tools._github_get")
    def test_scout_active_user(self, mock_get):
        mock_get.return_value = (200, {
            "login": "pro", "name": "Pro Dev", "bio": "I code",
            "location": "SF", "company": "BigCo", "followers": 500,
            "following": 50, "public_repos": 45,
            "created_at": "2018-01-01T00:00:00Z", "avatar_url": "",
            "blog": "", "twitter_username": "", "hireable": True,
        })
        state = {"username": "pro", "trace": [], "raw_data": {}}
        result = agent.scout_agent(state)
        assert result["user_tier"] == "active"


class TestGraphStructure:
    def test_graph_builds(self):
        app = agent.build_agent()
        assert app is not None

    def test_graph_has_all_nodes(self):
        app = agent.build_agent()
        nodes = list(app.get_graph().nodes)
        assert "scout" in nodes
        assert "analyst" in nodes
        assert "reviewer" in nodes
        assert "supervisor" in nodes


class TestAnalysisState:
    def test_state_fields(self):
        annotations = agent.AnalysisState.__annotations__
        required = [
            "messages", "username", "user_tier", "profile_summary",
            "tools_called", "raw_data", "report",
            "review_passed", "review_feedback", "revision_count",
            "trace", "next_agent",
        ]
        for field in required:
            assert field in annotations, f"Missing: {field}"
