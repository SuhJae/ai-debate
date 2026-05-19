from llms import ToolMode

from app.core.tool_modes import resolve_tool_mode


def test_probe_without_file_read_resolves_to_text_only():
    assert resolve_tool_mode(False, True) == ToolMode.TEXT_ONLY


def test_probe_with_file_read_resolves_to_probe():
    assert resolve_tool_mode(True, True) == ToolMode.PROBE
