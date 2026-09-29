from __future__ import annotations

import os
from contextlib import contextmanager
from functools import wraps
from typing import Any

try:
    from langfuse import get_client, observe, propagate_attributes

    LANGFUSE_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - chỉ dùng khi chưa cài requirements
    LANGFUSE_SDK_AVAILABLE = False

    def observe(*args: Any, **kwargs: Any):
        def decorator(func):
            return func

        return decorator

    class _DummyClient:
        def update_current_span(self, **kwargs: Any) -> None:
            return None

        def update_current_generation(self, **kwargs: Any) -> None:
            return None

        @contextmanager
        def start_as_current_observation(self, **kwargs: Any):
            yield _NoopObservation()

    def get_client():
        return _DummyClient()

    @contextmanager
    def propagate_attributes(**kwargs: Any):
        yield


class _NoopObservation:
    def update(self, **kwargs: Any) -> "_NoopObservation":
        return self


class _OfflineClient:
    """Langfuse-compatible no-op client used until both credentials exist."""

    def update_current_span(self, **kwargs: Any) -> None:
        return None

    def update_current_generation(self, **kwargs: Any) -> None:
        return None

    @contextmanager
    def start_as_current_observation(self, **kwargs: Any):
        yield _NoopObservation()


@contextmanager
def start_observation(client: Any, **kwargs: Any):
    """Use the Langfuse v4 observation API while remaining test/offline safe."""
    starter = getattr(client, "start_as_current_observation", None)
    if not callable(starter):
        yield _NoopObservation()
        return
    with starter(**kwargs) as observation:
        yield observation


def get_langfuse_client():
    return get_client() if tracing_enabled() else _OfflineClient()


def observe_when_enabled(*decorator_args: Any, **decorator_kwargs: Any):
    """Run the real SDK decorator only when Langfuse credentials are configured."""
    sdk_decorator = observe(*decorator_args, **decorator_kwargs)

    def decorator(func):
        observed = sdk_decorator(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            if tracing_enabled():
                return observed(*args, **kwargs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def tracing_enabled() -> bool:
    return LANGFUSE_SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )
