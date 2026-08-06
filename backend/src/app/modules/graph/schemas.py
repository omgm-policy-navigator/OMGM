from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphNodeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str
    label: str
    data: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: str
    source: str
    target: str
    data: dict[str, Any] = Field(default_factory=dict)


class SessionGraphResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    node_count: int = Field(alias="nodeCount")
    edge_count: int = Field(alias="edgeCount")
    truncated: bool