# audio_components.py - (Legacy) High-level accessors for audio components
"""Legacy facade kept for backward compatibility.

WP001 introduced `audio_protocols.py` and `audio_factory.py` with a new
`ComponentFactory`. This module now simply proxies to the new factory so
existing import sites continue to work without refactor churn.
"""

from typing import Any, Optional, Dict
from app.core.audio.audio_factory import ComponentFactory

_legacy_factory: Optional[ComponentFactory] = None
_audio_aligner_cache: Dict[str, Any] = {}  # Cache para instâncias do AudioAligner

def _get_factory() -> ComponentFactory:
    global _legacy_factory
    if _legacy_factory is None:
        _legacy_factory = ComponentFactory()
    return _legacy_factory

def get_audio_aligner(**kwargs) -> Any:
    """Return an `AudioAligner` instance using the new ComponentFactory.

    Provided for backward compatibility with existing imports.
    Uses caching to prevent multiple instances and duplicate log messages.
    """
    # Usar uma chave simples já que a maioria das chamadas é sem parâmetros
    cache_key = "default"
    if kwargs:
        # Se há parâmetros, geramos uma chave baseada nos valores
        sorted_items = sorted(kwargs.items())
        cache_key = str(sorted_items)
    
    if cache_key in _audio_aligner_cache:
        return _audio_aligner_cache[cache_key]
    
    factory = _get_factory()
    # Allow caller to pass pre-built components
    if not kwargs.get("silence_detector"):
        kwargs["silence_detector"] = factory.silence_detector()
    if not kwargs.get("aligner") and not kwargs.get("forced_aligner"):
        kwargs["forced_aligner"] = factory.forced_aligner()
    if not kwargs.get("frame_synchronizer"):
        kwargs["frame_synchronizer"] = factory.frame_synchronizer()

    from app.core.audio.audio_aligner import AudioAligner  # Local import to avoid cycles
    aligner = AudioAligner(factory=factory, **kwargs)
    _audio_aligner_cache[cache_key] = aligner
    return aligner

# For prior code referencing `audio_factory.get_audio_aligner()`
class _Facade:
    def get_audio_aligner(self, **kwargs):
        return get_audio_aligner(**kwargs)

audio_factory = _Facade()

__all__ = ["audio_factory", "get_audio_aligner"]