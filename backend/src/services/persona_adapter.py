"""
Persona Adapter
Bridges external AuraIA_Persona assets into the backend without copying files.
Dynamically loads persona_engine_v2.py and prepares system/user prompts.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict, Optional

from src.config.settings import get_settings

settings = get_settings()


@lru_cache(maxsize=2)
def _load_module_from_path(module_name: str, file_path: Path):
    spec = spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    mod = module_from_spec(spec)
    # type: ignore[attr-defined]
    spec.loader.exec_module(mod)
    return mod


@lru_cache(maxsize=1)
def _load_engine_module():
    assets_dir = Path(settings.persona_assets_dir).resolve()
    v2_path = assets_dir / "persona_engine_v2.py"
    primary_path = v2_path if v2_path.exists() else assets_dir / "persona_engine.py"
    return _load_module_from_path("auraia_persona_engine", primary_path)


def prepare_chat_prompts(
    user_message: str,
    persona_name: Optional[str] = None,
    sentiment: str = "neutral",
    empathy: float = 0.5,
    archetype_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Returns dict with keys: system_prompt, user_prompt, meta
    """
    try:
        mod = _load_engine_module()
    except Exception:
        # Assets missing or failed to load: return minimal safe fallback
        return {
            "system_prompt": (
                "You are a collaborative, empathetic assistant. " "Be concise and helpful."
            ),
            "user_prompt": user_message,
            "meta": {"persona": persona_name or "default", "engine": "fallback"},
        }
    # Use persona_engine_v2 if available, else persona_engine
    if hasattr(mod, "EmojiSelector"):
        # persona_engine_v2 present; try to also load persona_engine.py for prompt
        try:
            assets_dir = Path(settings.persona_assets_dir).resolve()
            legacy_mod = _load_module_from_path(
                "auraia_persona_engine_legacy", assets_dir / "persona_engine.py"
            )
            engine_cls = getattr(legacy_mod, "PersonaEngine", None)
            engine = engine_cls() if engine_cls else None
        except (OSError, FileNotFoundError, ImportError, AttributeError):
            engine = None
    else:
        engine_cls = getattr(mod, "PersonaEngine", None)
        engine = engine_cls() if engine_cls else None

    if engine is None:
        # Minimal fallback
        return {
            "system_prompt": (
                "You are a collaborative, empathetic assistant. " "Be concise and helpful."
            ),
            "user_prompt": user_message,
            "meta": {"persona": persona_name or "default"},
        }

    prepared = engine.prepare_llm_input(
        user_message=user_message,
        persona_name=persona_name,
        sentiment=sentiment,
        empathy=empathy,
        archetype_weights=archetype_weights,
    )
    return prepared
