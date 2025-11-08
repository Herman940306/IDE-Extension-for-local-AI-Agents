# AuralA Human Experience Pack

This package contains the Persona Engine and supporting assets to add a rich, emotionally-aware, and safe persona layer to your AuraIA project.

## What’s included
- `persona_engine.py` - Core persona engine (backend)
- `personas/` - Four starter persona JSON profiles you can blend
- `emoji_library.json` - Starter emoji sets categorized by sentiment
- `AuralAAvatar.jsx` - React avatar component (Tailwind-ready)
- `README_Human_Experience.md` - this doc

## Quick Start (Backend)
1. Copy `persona_engine.py`, `personas/`, and `emoji_library.json` into your backend project (e.g., `src/persona/`).
2. Example usage:
```python
from persona_engine import PersonaEngine
p = PersonaEngine()
inp = p.prepare_llm_input('Help me refactor this function', persona_name='compassionate_innovator.json', sentiment='thoughtful', empathy=0.7)
system_prompt = inp['system_prompt']
user_prompt = inp['user_prompt']
# Send system_prompt as system-level LLM message, and user_prompt as the user message.
```

## Quick Start (Frontend)
- Use `AuralAAvatar.jsx` as a small UI touch to show the persona. It uses Tailwind for convenience.

## Safety & Ethics
- The persona engine explicitly includes safety rules in generated system prompts and limits empathy intensity.
- **Do not** use personas to simulate human relationships or provide professional advice without proper disclaimers.
- Always disclose the assistant is an AI.

## Extend
- Add more persona JSON files to `personas/` and reference them by filename.
- Expand `emoji_library.json` with more categories/emojis.
- Implement sentiment detection and pass `sentiment` into `prepare_llm_input` for adaptive tone.
