from pathlib import Path


def test_persona_adapter_fallback_minimal_prompt(tmp_path: Path):
    # Import module under test
    from src.services import persona_adapter as pa

    # Point assets dir to empty temp folder and clear caches
    original_dir = pa.settings.persona_assets_dir
    try:
        pa.settings.persona_assets_dir = str(tmp_path)
        pa._load_engine_module.cache_clear()
        pa._load_module_from_path.cache_clear()

        prepared = pa.prepare_chat_prompts("Hello there")
        assert isinstance(prepared, dict)
        system = prepared.get("system_prompt", "")
        user = prepared.get("user_prompt", "")
        assert "collaborative, empathetic assistant" in system
        assert user == "Hello there"
    finally:
        # Restore
        pa.settings.persona_assets_dir = original_dir
        pa._load_engine_module.cache_clear()
        pa._load_module_from_path.cache_clear()
