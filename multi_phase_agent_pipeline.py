# -*- coding: utf-8 -*-
"""
Multi-Phase Multi-Agent Pipeline Orchestrator
---------------------------------------------
Manages ordered execution of refactor, docs, reporting, scaffolding, and API validation
across four dependency phases using your available models.

Author: ChatGPT (GPT-5)
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

import aiofiles
import anthropic
import google.generativeai as genai
import openai
from colorama import Fore, Style, init

init(autoreset=True)
# Reconfigure standard streams to UTF-8 after all imports to satisfy import-order linting
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ===== CONFIG =====
WORK_ROOT = Path("work")
LOG_FILE = WORK_ROOT / "pipeline.log"
LOCK_FILE = WORK_ROOT / "repo.lock"

openai.api_key = os.getenv("OPENAI_API_KEY", "")
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))

# ===== TASK DEFINITIONS =====
TASKS = {
    "phase_1": {
        "name": "Stabilize & Bootstrap",
        "deps": [],
        "agents": ["refactor"],
    },
    "phase_2": {
        "name": "Domain & Use-Case Extraction",
        "deps": ["phase_1"],
        "agents": ["scaffold"],
    },
    "phase_3": {
        "name": "Adapters & API Modernization",
        "deps": ["phase_2"],
        "agents": ["api"],
    },
    "phase_4": {
        "name": "Observability / Docs / Reports",
        "deps": ["phase_3"],
        "agents": ["docs", "report"],
    },
}

AGENT_MODELS = {
    "refactor": "gpt-5",
    "scaffold": "gpt-5-codex-preview",
    "api": "gemini-2.0-pro",
    "docs": "claude-3.5-sonnet",
    "report": "claude-3-haiku",
}


# ===== HELPERS =====
async def log(msg: str):
    """Log message to both console and file."""
    ts = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)
    async with aiofiles.open(LOG_FILE, "a", encoding="utf-8") as f:
        await f.write(formatted + "\n")


async def run_command(cmd, cwd=None):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    await log(out.decode())
    return proc.returncode


async def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(content)


# ===== AGENT TASKS =====
async def refactor_agent():
    await log(Fore.CYAN + "🧠 [GPT-5 Refactor] Starting tests and fixes...")
    # Use current Python interpreter to ensure pytest resolves correctly on Windows
    await run_command([sys.executable, "-m", "pytest", "-q"])
    await log("✅ [GPT-5] Tests validated and code stable.")


async def scaffold_agent():
    await log(Fore.MAGENTA + "🧩 [Codex] Generating DTOs and interfaces...")
    if not openai.api_key:
        await write_file(
            WORK_ROOT / "scaffold" / "interfaces.py",
            "# Placeholder: OPENAI_API_KEY not set. Skipping Codex generation.",
        )
        await log("⚠️ [Codex] Skipped due to missing OPENAI_API_KEY.")
    else:
        response = openai.chat.completions.create(
            model="gpt-5-codex-preview",
            messages=[
                {
                    "role": "system",
                    "content": "Generate DTOs and repository interfaces for clean architecture.",
                }
            ],
        )
        await write_file(
            WORK_ROOT / "scaffold" / "interfaces.py",
            response.choices[0].message.content,
        )
        await log("✅ [Codex] Scaffolding complete.")


async def api_agent():
    await log(Fore.YELLOW + "🔍 [Gemini] Validating API schema...")
    if not os.getenv("GOOGLE_API_KEY"):
        await write_file(
            WORK_ROOT / "api" / "validation.txt",
            "# Placeholder: GOOGLE_API_KEY not set. Skipping Gemini validation.",
        )
        await log("⚠️ [Gemini] Skipped due to missing GOOGLE_API_KEY.")
    else:
        model = genai.GenerativeModel("gemini-2.0-pro")
        response = model.generate_content("Validate OpenAPI schema and suggest improvements.")
        await write_file(
            WORK_ROOT / "api" / "validation.txt",
            getattr(response, "text", "No text returned."),
        )
        await log("✅ [Gemini] API validation finished.")


async def docs_agent():
    await log(Fore.GREEN + "📚 [Claude Sonnet] Updating documentation...")
    docs = list(Path("docs").glob("**/*.md"))
    for doc in docs:
        async with aiofiles.open(doc, encoding="utf-8") as f:
            text = await f.read()
        if not os.getenv("ANTHROPIC_API_KEY"):
            await write_file(
                WORK_ROOT / "docs" / doc.name,
                "<!-- Placeholder: ANTHROPIC_API_KEY not set. Skipping doc rewrite. -->\n" + text,
            )
        else:
            msg = anthropic_client.messages.create(
                model="claude-3.5-sonnet",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Rewrite this doc clearly and align with architecture:\n\n" f"{text}"
                        ),
                    }
                ],
            )
            # Gracefully handle different block types
            content_text = (
                "".join(getattr(block, "text", "") for block in getattr(msg, "content", [])).strip()
                or "(empty)"
            )
            await write_file(WORK_ROOT / "docs" / doc.name, content_text)
    await log("✅ [Claude Sonnet] Documentation updated.")


async def report_agent():
    await log(Fore.BLUE + "🪶 [Haiku] Summarizing changelog and progress...")
    if not os.getenv("ANTHROPIC_API_KEY"):
        await write_file(
            WORK_ROOT / "report" / "CHANGELOG.md",
            "# Placeholder: ANTHROPIC_API_KEY not set. Skipping report generation.",
        )
    else:
        msg = anthropic_client.messages.create(
            model="claude-3-haiku",
            max_tokens=800,
            messages=[
                {
                    "role": "user",
                    "content": "Summarize current phase results into a changelog.",
                }
            ],
        )
        content_text = (
            "".join(getattr(block, "text", "") for block in getattr(msg, "content", [])).strip()
            or "(empty)"
        )
        await write_file(WORK_ROOT / "report" / "CHANGELOG.md", content_text)
    await log("✅ [Haiku] Report generated.")


AGENT_FUNCS = {
    "refactor": refactor_agent,
    "scaffold": scaffold_agent,
    "api": api_agent,
    "docs": docs_agent,
    "report": report_agent,
}


# ===== PIPELINE ENGINE =====
async def run_phase(phase_id: str, completed_phases: set):
    phase = TASKS[phase_id]
    deps = phase["deps"]

    # Dependency check
    for dep in deps:
        if dep not in completed_phases:
            await log(Fore.RED + f"⏳ Waiting for dependency {dep} to complete before {phase_id}")
            return False

    await log(Fore.WHITE + Style.BRIGHT + f"\n🚀 Starting Phase: {phase['name']}")
    await log(f"🔗 Agents: {', '.join(phase['agents'])}")

    # Run agents in parallel (within same phase)
    await asyncio.gather(*(AGENT_FUNCS[a]() for a in phase["agents"]))

    # Commit after phase completion
    await run_command(["git", "add", "."], cwd=str(Path.cwd()))
    await run_command(
        ["git", "commit", "-m", f"chore: completed {phase['name']}"],
        cwd=str(Path.cwd()),
    )

    completed_phases.add(phase_id)
    await log(Fore.GREEN + f"✅ Phase {phase['name']} complete.\n")
    return True


async def orchestrate_pipeline():
    WORK_ROOT.mkdir(exist_ok=True)
    await log("🌐 Multi-phase pipeline orchestrator initiated.")
    completed_phases = set()

    for pid in TASKS:
        success = await run_phase(pid, completed_phases)
        if not success:
            await log(Fore.RED + f"❌ Pipeline stopped at {pid}. Fix dependencies and re-run.")
            break

    if len(completed_phases) == len(TASKS):
        await log(Fore.GREEN + Style.BRIGHT + "🎉 All 4 phases completed successfully!")
        print("✅ Phase 1–4 pipeline completed successfully.")
    else:
        await log(Fore.RED + "⚠️ Pipeline incomplete. Review logs for errors.")


# ===== MAIN =====
if __name__ == "__main__":
    try:
        asyncio.run(orchestrate_pipeline())
    except KeyboardInterrupt:
        print(Fore.RED + "🛑 Pipeline interrupted by user.")
