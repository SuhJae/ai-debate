"""Provider-neutral tool mode resolution."""

from llms import ToolMode


def resolve_tool_mode(allow_file_read: bool, allow_probe_commands: bool) -> ToolMode:
    """
    false,false -> TEXT_ONLY
    true,false -> READ_ONLY
    true,true -> PROBE
    false,true -> TEXT_ONLY
    """
    if allow_file_read and allow_probe_commands:
        return ToolMode.PROBE
    if allow_file_read:
        return ToolMode.READ_ONLY
    return ToolMode.TEXT_ONLY
