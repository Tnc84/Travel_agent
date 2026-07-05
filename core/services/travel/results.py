from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from core.graph.state import NodeErrorKind, make_error
from core.location import LocationResult

T = TypeVar("T")


class ServiceErrorKind(str, Enum):
    NON_RETRYABLE = "non_retryable"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


@dataclass(frozen=True)
class ServiceError:
    kind: ServiceErrorKind
    message: str
    provider: Optional[str] = None


@dataclass
class ServiceResult(Generic[T]):
    ok: bool
    data: Optional[T] = None
    error: Optional[ServiceError] = None

    @classmethod
    def success(cls, data: T) -> "ServiceResult[T]":
        return cls(ok=True, data=data)

    @classmethod
    def failure(cls, error: ServiceError) -> "ServiceResult[T]":
        return cls(ok=False, error=error)


@dataclass
class ResolveLocationData:
    resolved: Optional[LocationResult]
    clarification: Optional[str]
    needs_clarification: bool


@dataclass
class PoiData:
    hotels: List[Dict[str, Any]] = field(default_factory=list)
    restaurants: List[Dict[str, Any]] = field(default_factory=list)
    attractions: List[Dict[str, Any]] = field(default_factory=list)
    fallback_errors: Dict[str, ServiceError] = field(default_factory=dict)


def service_error_to_node_error(node: str, error: ServiceError) -> Dict[str, Any]:
    kind_map = {
        ServiceErrorKind.NON_RETRYABLE: NodeErrorKind.NON_RETRYABLE,
        ServiceErrorKind.TIMEOUT: NodeErrorKind.TIMEOUT,
        ServiceErrorKind.PROVIDER_UNAVAILABLE: NodeErrorKind.PROVIDER_UNAVAILABLE,
    }
    return make_error(
        node,
        kind_map[error.kind],
        error.message,
        provider=error.provider,
    )
