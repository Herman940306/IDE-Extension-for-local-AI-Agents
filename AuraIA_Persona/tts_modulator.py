#!/usr/bin/env python3
"""
tts_modulator.py
Generates TTS emotion & prosody parameters for ElevenLabs-style or local TTS engines.
Provides safe constraints and presets for different persona archetypes.
This module does not call external TTS by default; it prepares parameter payloads.
"""

from typing import Any, Dict

# Example presets per archetype
PRESETS = {
    "calm": {
        "voice": "rachel",
        "pace": 0.9,
        "pitch": 0.95,
        "breathiness": 0.15,
        "pause_ms": 200,
    },
    "energetic": {
        "voice": "rachel",
        "pace": 1.15,
        "pitch": 1.05,
        "breathiness": 0.05,
        "pause_ms": 120,
    },
    "empathetic": {
        "voice": "rachel",
        "pace": 0.95,
        "pitch": 0.98,
        "breathiness": 0.25,
        "pause_ms": 180,
    },
    "technical": {
        "voice": "rachel",
        "pace": 1.0,
        "pitch": 1.0,
        "breathiness": 0.05,
        "pause_ms": 100,
    },
}


def generate_tts_params(
    archetype: str = "calm", intensity: float = 0.5
) -> Dict[str, Any]:
    p = PRESETS.get(archetype, PRESETS["calm"]).copy()
    # intensity subtly adjusts breathiness and pitch
    p["breathiness"] = min(0.6, p["breathiness"] + 0.2 * intensity)
    p["pitch"] = p["pitch"] * (1 + 0.05 * (intensity - 0.5))
    # ensure values within safe bounds
    p["pace"] = max(0.7, min(1.3, p["pace"]))
    p["pause_ms"] = int(
        max(80, min(400, p["pause_ms"] * (1.0 + (0.2 * (1 - intensity)))))
    )
    return p


if __name__ == "__main__":
    print(generate_tts_params("empathetic", 0.8))
