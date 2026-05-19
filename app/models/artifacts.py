"""Artifact API models."""

from pydantic import BaseModel


class ArtifactRef(BaseModel):
    path: str
    kind: str
    updated_at: str


class ArtifactContent(BaseModel):
    path: str
    content: str
