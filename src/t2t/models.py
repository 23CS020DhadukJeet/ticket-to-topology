"""Data models for route information, neighbors, route maps, and verification checks."""

from typing import Any

from pydantic import BaseModel, Field


class NextHop(BaseModel):
    """Next hop routing descriptor."""

    ip: str
    interface: str
    from_ip: str


class RouteDetail(BaseModel):
    """Detailed routing table entry parsed from 'show ip route PREFIX MASK'."""

    prefix: str
    known_via: str
    protocol: str
    distance: int
    metric: int
    route_type: str = ""
    tag: int | None = None
    next_hops: list[NextHop] = Field(default_factory=list)
    advertised_by: list[str] = Field(default_factory=list)


class Neighbor(BaseModel):
    """Routing protocol adjacency neighbor record."""

    address: str
    interface: str
    state: str = ""


class RouteMapClause(BaseModel):
    """Route-map sequence clause."""

    name: str
    action: str  # permit | deny
    seq: int
    match: dict[str, str] = Field(default_factory=dict)
    set: dict[str, str] = Field(default_factory=dict)


class Check(BaseModel):
    """Verification check specification."""

    id: str
    kind: str
    router: str
    prefix: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    desc: str = ""


class CheckResult(BaseModel):
    """Result of executing a verification check."""

    check_id: str
    passed: bool
    expected: str
    observed: str
    message: str = ""
