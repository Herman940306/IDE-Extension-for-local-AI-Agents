from src.services.task_orchestrator import TaskOrchestrator


def test_analyze_user_style_brevity_and_formality():
    orch = TaskOrchestrator()
    style = orch._analyze_user_style(
        description="Quick help please", content="fix bug fast. no extra text."
    )
    # Expect high brevity (short ask), low detail, neutral or stressed mood inference
    assert 0 <= style["brevity"] <= 10
    assert 0 <= style["formality"] <= 10
    assert 0 <= style["detail_level"] <= 10
    assert isinstance(style.get("needs_support"), bool)


def test_emoji_policy_respects_no_emoji_phrase():
    orch = TaskOrchestrator()
    style = {
        "formality": 5,
        "detail_level": 5,
        "contains_emoji": False,
        "explicit_no_emoji": True,
    }
    cfg = orch._emoji_policy(style)
    assert cfg["allow"] is False
    assert cfg["max"] == 0


def test_build_adaptive_chat_prompt_contains_traits_and_rules():
    orch = TaskOrchestrator()
    style = {
        "brevity": 6,
        "formality": 5,
        "detail_level": 6,
        "mood": "neutral",
        "needs_support": False,
        "contains_emoji": False,
        "explicit_no_emoji": False,
    }
    prompt = orch._build_adaptive_chat_prompt(style)
    assert "supportive engineering partner" in prompt
    assert "Traits: warm, clear, collaborative" in prompt
