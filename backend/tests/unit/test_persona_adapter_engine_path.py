from types import SimpleNamespace


def test_persona_adapter_engine_path(monkeypatch):
    from src.services import persona_adapter as pa

    class _DummyEngine:
        def prepare_llm_input(self, **kwargs):  # type: ignore[no-untyped-def]
            return {
                "system_prompt": "DUMMY_PERSONA_RULES",
                "user_prompt": kwargs.get("user_message", ""),
                "meta": {"persona": kwargs.get("persona_name", "dummy")},
            }

    dummy_mod = SimpleNamespace(PersonaEngine=lambda: _DummyEngine())

    # Force using else-path (no EmojiSelector in module)
    monkeypatch.setattr(pa, "_load_engine_module", lambda: dummy_mod)

    out = pa.prepare_chat_prompts("hello", persona_name="AuraIA OmniDev")
    assert out["system_prompt"] == "DUMMY_PERSONA_RULES"
    assert out["user_prompt"] == "hello"
