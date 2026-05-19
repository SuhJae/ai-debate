"""Global MCP server models."""

from enum import StrEnum

from pydantic import BaseModel, Field


class McpTransport(StrEnum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


class GlobalMcpServer(BaseModel):
    id: str
    name: str
    description: str = ""
    transport: McpTransport = McpTransport.STDIO
    command_or_url: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    trusted: bool = False
    created_at: str
    updated_at: str


class McpServerCreateRequest(BaseModel):
    name: str
    description: str = ""
    transport: McpTransport = McpTransport.STDIO
    command_or_url: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    trusted: bool = False


class McpServerUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    transport: McpTransport | None = None
    command_or_url: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    enabled: bool | None = None
    trusted: bool | None = None
