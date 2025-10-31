#!/usr/bin/env python3
"""
persona_engine_v2.py
Enhanced selection heuristics for emoji usage and persona behavior.
Provides deterministic and diverse emoji selection strategies, cooldowns,
user-preference weighting, and contextual mapping.
"""

import json
import random
import time
from pathlib import Path
from typing import List, Optional

EMOJI_FILE = Path(__file__).parent / "emoji_library_expanded.json"


class EmojiSelector:
    def __init__(self, emoji_file: Path = EMOJI_FILE):
        data = json.loads(emoji_file.read_text(encoding="utf-8"))
        self.emojis = data.get("emojis", [])
        # maps sentiment -> curated indices (for speed)
        self.sentiment_map = {
            "neutral": [
                i
                for i, e in enumerate(self.emojis)
                if any(ch in e for ch in ["🙂", "🤖", "✨", "💡"])
            ],
            "friendly": [
                i
                for i, e in enumerate(self.emojis)
                if any(ch in e for ch in ["😊", "🤝", "🌟", "🙌"])
            ],
            "motivational": [
                i
                for i, e in enumerate(self.emojis)
                if any(ch in e for ch in ["🚀", "🔥", "💪", "🏆"])
            ],
            "thoughtful": [
                i
                for i, e in enumerate(self.emojis)
                if any(ch in e for ch in ["🤔", "💭", "🧠", "🔍"])
            ],
            "calm": [
                i
                for i, e in enumerate(self.emojis)
                if any(ch in e for ch in ["🌿", "💧", "🌙", "🕊️"])
            ],
            "error": [
                i
                for i, e in enumerate(self.emojis)
                if any(ch in e for ch in ["⚠️", "🛑", "🔧", "😓"])
            ],
            "success": [
                i
                for i, e in enumerate(self.emojis)
                if any(ch in e for ch in ["✅", "🎉", "🏅", "🌟"])
            ],
        }
        # cooldown tracking per user to avoid repetition
        self.user_cooldowns = {}  # username -> {emoji: last_used_ts}
        # user's preferred emojis override
        self.user_preferences = {}  # username -> list of emoji strings

    def set_user_preferences(self, username: str, emojis: List[str]):
        self.user_preferences[username] = [e for e in emojis if e in self.emojis]

    def _available_candidates(self, username: Optional[str], sentiment: str):
        indices = self.sentiment_map.get(sentiment, list(range(len(self.emojis))))
        # filter out recently used emojis for user (cooldown 60s)
        now = time.time()
        cooldown_map = self.user_cooldowns.get(username, {}) if username else {}
        candidates = []
        for idx in indices:
            e = self.emojis[idx]
            last = cooldown_map.get(e, 0)
            if now - last > 60:  # 60 second cooldown
                candidates.append(e)
        # if none available, relax cooldown
        if not candidates:
            candidates = [self.emojis[i] for i in indices]
        return candidates

    def pick(
        self,
        sentiment: str = "neutral",
        intensity: float = 0.5,
        username: Optional[str] = None,
        count: int = 1,
    ) -> List[str]:
        """
        Picks emoji(s) based on sentiment, intensity (0..1), user prefs and cooldowns.
        """
        # user preferences weighted
        prefs = self.user_preferences.get(username, [])
        candidates = self._available_candidates(username, sentiment)
        # weight prefs higher
        weighted = []
        for c in candidates:
            weight = 1.0
            if c in prefs:
                weight += 3.0
            # intensity bias: pick more emphatic ones if intensity high (heuristic using symbol count)
            emphatic_score = min(3, sum(1 for ch in c if ch in "✨🔥🚀💫🌟🎉✅"))
            weight += emphatic_score * intensity
            weighted.append((c, weight))
        # normalize and random choice
        total = sum(w for _, w in weighted) or 1.0
        probs = [w / total for _, w in weighted]
        choices = random.choices([c for c, _ in weighted], weights=probs, k=count)
        # register cooldowns
        now = time.time()
        if username:
            cd = self.user_cooldowns.setdefault(username, {})
            for ch in choices:
                cd[ch] = now
        return choices


# Example usage
if __name__ == "__main__":
    sel = EmojiSelector()
    print("Total emojis:", len(sel.emojis))
    print("Pick friendly:", sel.pick("friendly", 0.7, username="herman", count=2))
