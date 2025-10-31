#!/usr/bin/env python3
"""
persona_engine.py
AuralA Persona Engine - advanced persona system for emotional, adaptive, and safe responses.
Features:
- Archetype blending (weights) to create hybrid personalities
- Sentiment-aware tone adaptation
- Emoji / icon selection with large library support
- Short-term memory for continuity (per-session)
- Safety filters to avoid inappropriate emotional manipulation
- Exportable prompt injection for LLM calls (system prompt + few-shot)
- Persistence of user preferences and persona tuning (JSON)
"""

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configuration paths
BASE_DIR = Path(__file__).parent
PERSONAS_DIR = BASE_DIR / "personas"
EMOJI_FILE = BASE_DIR / "emoji_library.json"
MEMORY_DIR = BASE_DIR / "memory"
MEMORY_DIR.mkdir(exist_ok=True)

# Safety: maximum allowed "empathy intensity" to prevent manipulative behavior
MAX_EMPATHY_INTENSITY = 0.9


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class PersonaEngine:
    def __init__(self, default_persona: str = "compassionate_innovator.json"):
        self.personas = {}
        self._load_personas()
        self.emoji_lib = load_json(EMOJI_FILE) or {}
        self.default_persona = default_persona
        self.session_memory = {}  # ephemeral per-run memory
        self.user_profiles = {}  # persisted if needed (username -> profile dict)

    def _load_personas(self):
        PERSONAS_DIR.mkdir(exist_ok=True)
        for p in PERSONAS_DIR.glob("*.json"):
            try:
                self.personas[p.name] = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                print("Failed to load persona", p, e)

    def list_personas(self) -> List[str]:
        return list(self.personas.keys())

    def get_persona(self, name: Optional[str] = None) -> Dict[str, Any]:
        name = name or self.default_persona
        return self.personas.get(name, {})

    def blend_personas(
        self, names: List[str], weights: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Blend several persona JSON profiles by weights (normalized). Return a merged persona.
        """
        if not names:
            return self.get_persona(self.default_persona)
        profiles = [self.get_persona(n) for n in names if self.get_persona(n)]
        if not profiles:
            return self.get_persona(self.default_persona)
        if weights is None:
            weights = [1.0] * len(profiles)
        # normalize
        s = sum(weights) or 1.0
        weights = [w / s for w in weights]
        blended = {}
        # simple strategy: pick strings from highest weight, merge lists and pick union
        keys = set().union(*[set(p.keys()) for p in profiles])
        for k in keys:
            vals = [p.get(k) for p in profiles]
            # if all are dicts -> merge keys recursively (simple average for numeric)
            if all(isinstance(v, dict) for v in vals if v is not None):
                merged = {}
                subkeys = set().union(
                    *[set(v.keys()) for v in vals if isinstance(v, dict)]
                )
                for sk in subkeys:
                    # collect numeric or lists
                    entries = [v.get(sk) for v in vals if isinstance(v, dict)]
                    if all(
                        isinstance(e, (int, float)) for e in entries if e is not None
                    ):
                        # weighted avg
                        total = sum(
                            (e or 0.0) * w
                            for e, w in zip(entries, weights, strict=False)
                        )
                        merged[sk] = total
                    else:
                        # union lists or prefer highest weight non-empty
                        res = []
                        for e in entries:
                            if isinstance(e, list):
                                res.extend(e)
                        merged[sk] = list(dict.fromkeys(res))
                blended[k] = merged
            elif all(isinstance(v, list) for v in vals if v is not None):
                # weighted union of lists
                res = []
                for v in vals:
                    if isinstance(v, list):
                        res.extend(v)
                blended[k] = list(dict.fromkeys(res))
            else:
                # choose highest-weight non-null value
                chosen = None
                for val, _w in sorted(
                    zip(vals, weights, strict=False), key=lambda x: -x[1]
                ):
                    if val:
                        chosen = val
                        break
                blended[k] = chosen
        return blended

    def select_emoji(
        self, sentiment: str = "neutral", intensity: float = 0.5, count: int = 1
    ) -> List[str]:
        """
        Choose emojis based on sentiment and intensity.
        intensity: 0.0..1.0 scales the "expressiveness"
        """
        lib = self.emoji_lib.get(sentiment) or self.emoji_lib.get("neutral", ["🙂"])
        # intensity influences whether we pick from more emphatic subset
        n = max(1, int(round(count * (1 + intensity))))
        picks = []
        for _ in range(n):
            e = random.choice(lib)
            picks.append(e)
        return picks

    def stylize_text(
        self,
        base_text: str,
        persona_name: Optional[str] = None,
        sentiment: str = "neutral",
        empathy: float = 0.5,
        use_emoji: bool = True,
    ) -> Dict[str, Any]:
        """
        Return a stylized text and metadata. Controls:
        - tone modifications (short/long sentences)
        - emoji attachment
        - small "micro-phrases" for humanlike feel
        """
        persona = self.get_persona(persona_name)
        # clamp empathy to safe range
        empathy = min(empathy, MAX_EMPATHY_INTENSITY)
        # base style cues
        persona.get("style", {})
        archetype = persona.get("archetype", "AuralA")
        # micro-phrases selection
        micro = random.choice(
            persona.get("micro_phrases", ["Got it.", "Understood.", "Right away."])
        )
        # punctuation & breathing pattern
        if sentiment in ("stressed", "urgent"):
            prefix = random.choice(
                persona.get("urgent_prefixes", ["Quick note:", "Heads up:"])
            )
            formatted = f"{prefix} {base_text}"
        elif sentiment in ("thoughtful", "curious"):
            formatted = f"{base_text} — {random.choice(persona.get('thoughtful_tail', ['Let’s explore that.','What do you think?']))}"
        else:
            formatted = base_text
        # emoji and closing
        emojis = self.select_emoji(sentiment, empathy, count=1) if use_emoji else []
        signature = (
            random.choice(persona.get("signoffs", ["— AuralA", "— Your AuralA"]))
            if persona.get("signoffs")
            else ""
        )
        final = f"{' '.join(emojis)} {formatted} {signature}".strip()
        # assemble metadata
        meta = {
            "persona": persona_name or self.default_persona,
            "archetype": archetype,
            "micro_phrase": micro,
            "empathy": empathy,
            "emojis": emojis,
        }
        return {"text": final, "meta": meta}

    def few_shot_system_prompt(
        self,
        persona_name: Optional[str] = None,
        archetype_weights: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Produce a system prompt to inject into the LLM with persona instructions and behavior constraints.
        """
        if archetype_weights:
            # blend explicit personas
            blended = self.blend_personas(
                list(archetype_weights.keys()), list(archetype_weights.values())
            )
        else:
            blended = self.get_persona(persona_name)
        # Safety-first system prompt
        rules = blended.get(
            "safety_rules",
            [
                "Be transparent that you are an AI assistant and avoid simulating human relationships."
            ],
        )
        style = blended.get("style", {})
        tone_examples = blended.get("tone_examples", [])
        prompt_lines = [
            "You are AuralA - a collaborative local-first AI assistant.",
            "Adopt the following style preferences and safety constraints exactly:",
            f"STYLE: {json.dumps(style)}",
            "SAFETY RULES:",
        ]
        for r in rules:
            prompt_lines.append(f"- {r}")
        if tone_examples:
            prompt_lines.append("EXAMPLES:")
            for ex in tone_examples[:6]:
                prompt_lines.append(f"- {ex}")
        prompt_lines.append(
            "When replying, keep answers helpful, concise, and emotionally aware; use emojis sparingly to support tone."
        )
        return "\\n".join(prompt_lines)

    # Simple session memory operations (ephemeral)
    def memory_set(self, username: str, key: str, value: Any):
        mfile = MEMORY_DIR / f"{username}.json"
        data = {}
        if mfile.exists():
            try:
                data = json.loads(mfile.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data[key] = value
        mfile.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def memory_get(self, username: str, key: str, default=None):
        mfile = MEMORY_DIR / f"{username}.json"
        if not mfile.exists():
            return default
        try:
            data = json.loads(mfile.read_text(encoding="utf-8"))
            return data.get(key, default)
        except Exception:
            return default

    # Simple adaptor for LLM prompt injection
    def prepare_llm_input(
        self,
        user_message: str,
        persona_name: Optional[str] = None,
        sentiment: str = "neutral",
        empathy: float = 0.5,
        archetype_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        sys_prompt = self.few_shot_system_prompt(persona_name, archetype_weights)
        stylized = self.stylize_text(user_message, persona_name, sentiment, empathy)
        # Return system prompt + user content
        return {
            "system_prompt": sys_prompt,
            "user_prompt": stylized["text"],
            "meta": stylized["meta"],
        }
