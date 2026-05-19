"""Shared pytest configuration.

Protocol tests originally needed a model fallback before backend models existed.
Keep that fallback conditional so backend tests can import the real app models.
"""

import importlib.util
import sys
from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if importlib.util.find_spec("app.models.agent") is None:
    mock_models = MagicMock()
    mock_agent = MagicMock()

    class DummyAgentId(str, Enum):
        CODEX = "codex"
        GEMINI = "gemini"
        CLAUDE = "claude"

    mock_agent.AgentId = DummyAgentId
    sys.modules["app.models"] = mock_models
    sys.modules["app.models.agent"] = mock_agent
