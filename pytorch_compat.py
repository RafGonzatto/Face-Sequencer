"""pytorch_compat.py
Centralized PyTorch compatibility helpers.

Goals:
- Avoid scattered monkey-patching of torch.load.
- Provide explicit, opt-in safe loading utilities.
- Handle PyTorch 2.6+ default weights_only=True change gracefully.
- Support temporary patching via context manager without global side-effects leaking.

Public API:
- is_problematic_version() -> bool
- safe_load(path_or_file, *args, **kwargs)  # function wrapper (forces weights_only=False when needed)
- safe_torch_load(...)  # alias
- patched_load_context(): context manager yielding original torch.load while temporarily patching
- ensure_whisperx_safe_globals(): idempotent registration of omegaconf classes for safe unpickling

Design:
We DO NOT permanently override torch.load on import. Call sites should import and use safe_load,
or use the context manager if third-party code internally calls torch.load.
"""
from __future__ import annotations
import contextlib
import importlib
import warnings
from typing import Any, Iterator, Iterable

try:
    import torch  # type: ignore
except Exception as e:  # pragma: no cover - torch may not be installed in light envs
    torch = None  # type: ignore
    _torch_import_error = e
else:
    _torch_import_error = None

_OMEGACONF_CLASSES_ADDED = False


def is_problematic_version() -> bool:
    """Return True if running on a PyTorch version that defaults to weights_only=True (2.6+).
    Conservative: if version parsing fails we return False (avoid unexpected behavior).
    """
    if torch is None:
        return False
    try:
        major, minor = map(int, torch.__version__.split(".")[:2])
        return (major > 2) or (major == 2 and minor >= 6)
    except Exception:  # pragma: no cover - defensive
        return False


def ensure_whisperx_safe_globals() -> None:
    """Register omegaconf classes with torch.serialization.add_safe_globals when available.
    Idempotent: runs at most once.
    """
    global _OMEGACONF_CLASSES_ADDED
    if _OMEGACONF_CLASSES_ADDED or torch is None:
        return
    try:
        omegaconf = importlib.import_module("omegaconf")
        ListConfig = getattr(omegaconf, "ListConfig", None)
        DictConfig = getattr(omegaconf, "DictConfig", None)
        OmegaConf = getattr(omegaconf, "OmegaConf", None)
        # Some internal classes (best-effort; if unavailable we skip silently)
        try:
            base_mod = importlib.import_module("omegaconf.base")
            ContainerMetadata = getattr(base_mod, "ContainerMetadata", None)
            Node = getattr(base_mod, "Node", None)
        except Exception:  # pragma: no cover - optional
            ContainerMetadata = None
            Node = None
        classes: Iterable[Any] = [c for c in [ListConfig, DictConfig, OmegaConf, ContainerMetadata, Node] if c is not None]
        if classes:
            try:
                torch.serialization.add_safe_globals(list(classes))  # type: ignore[attr-defined]
            except Exception as e:  # pragma: no cover - API differences
                warnings.warn(f"Failed to add safe globals for WhisperX: {e}")
        # PyTorch internal flag for allowing weights_only False (guarded)
        try:  # pragma: no cover - internal
            getattr(torch._C, "_set_default_weights_only_false_is_allowed", lambda *_: None)(True)
        except Exception:
            pass
        _OMEGACONF_CLASSES_ADDED = True
    except Exception as e:  # pragma: no cover - optional dependency missing
        warnings.warn(f"omegaconf not available for WhisperX safe globals: {e}")


def safe_load(f, *args, **kwargs):
    """Wrapper around torch.load applying compatibility fixes when needed.

    Behavior:
    - On PyTorch < 2.6: delegate directly.
    - On PyTorch >= 2.6: ensure weights_only=False (unless explicitly True from caller which we override).
    - Adds WhisperX safe globals once (lazy) to avoid repeated side effects.
    """
    if torch is None:
        raise RuntimeError(f"PyTorch not available: {_torch_import_error}")
    if is_problematic_version():
        ensure_whisperx_safe_globals()
        # Remove any provided weights_only to avoid duplicate arg warnings
        kwargs = {k: v for k, v in kwargs.items() if k != "weights_only"}
        kwargs["weights_only"] = False
    return torch.load(f, *args, **kwargs)

# Alias for clarity in some modules
safe_torch_load = safe_load


@contextlib.contextmanager
def patched_load_context() -> Iterator[None]:
    """Temporarily patch torch.load globally (for third-party libs invoking it internally).

    Use only when we cannot directly call safe_load (e.g., inside a library function that we don't control)
    and we want to ensure weights_only=False behavior.
    """
    if torch is None:
        yield
        return
    if not is_problematic_version():
        yield
        return
    original = torch.load

    def _patched(f, *args, **kwargs):  # pragma: no cover - thin shim
        kwargs = {k: v for k, v in kwargs.items() if k != "weights_only"}
        kwargs["weights_only"] = False
        return original(f, *args, **kwargs)

    torch.load = _patched  # type: ignore
    try:
        yield
    finally:
        torch.load = original  # type: ignore


# Convenience context name for user-friendly API
safe_load_context = patched_load_context

# Backwards/ergonomic alias: some specs may expect a context manager named like safe_load()
# We cannot overload the function name, but we offer safe_load_cm for "with" usage.
safe_load_cm = patched_load_context

__all__ = [
    "is_problematic_version",
    "ensure_whisperx_safe_globals",
    "safe_load",
    "safe_torch_load",
    "patched_load_context",
    "safe_load_context",
    "safe_load_cm",
]
