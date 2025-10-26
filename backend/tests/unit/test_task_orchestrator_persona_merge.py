from types import SimpleNamespace


def test_build_system_prompt_merges_persona(monkeypatch):
    # Arrange: stub persona_adapter.prepare_chat_prompts
    from src.services import task_orchestrator as to
    from src.models.task import TaskType

    # Ensure persona is enabled
    to.settings.enable_omni_persona = True
    to.settings.persona_assets_dir = "/nonexistent/path"  # value doesn't matter when stubbed

    calls = SimpleNamespace(count=0)

    def _stub_prepare_chat_prompts(**kwargs):  # type: ignore[no-untyped-def]
        calls.count += 1
        return {
            "system_prompt": "PERSONA_RULES",
            "user_prompt": kwargs.get("user_message", ""),
            "meta": {"persona": "AuraIA OmniDev"},
        }

    # Monkeypatch module function used by orchestrator
    import src.services.persona_adapter as pa

    monkeypatch.setattr(pa, "prepare_chat_prompts", _stub_prepare_chat_prompts)

    orch = to.TaskOrchestrator()

    # Act
    result = orch._build_system_prompt(
        TaskType.GENERAL, description="Help me quick", content="Make it short"
    )

    # Assert: persona rules come first, then adaptive base prompt
    assert isinstance(result, str)
    assert result.startswith("PERSONA_RULES")
    # Contains adaptive base prompt phrase
    assert "supportive engineering partner" in result
    assert calls.count == 1
