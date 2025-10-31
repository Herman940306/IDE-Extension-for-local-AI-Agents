"""
Multi-Agent Orchestrator for VS Code Copilot

This script coordinates GPT-5 (refactor/testing) and Claude Sonnet 4.5 (documentation)
to work concurrently without touching the same files. Designed for VS Code Copilot.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import aiofiles
import anthropic
import openai
from filelock import FileLock

# === CONFIG ===
WORK_ROOT = Path("work")
REFACTOR_DIR = WORK_ROOT / "refactor"
DOCS_DIR = WORK_ROOT / "docs"
LOCK_FILE = WORK_ROOT / "repo.lock"
TEST_RESULTS = REFACTOR_DIR / "results.json"

# Replace with your API keys (optional if managed by Copilot/VSCode)
openai.api_key = os.getenv("OPENAI_API_KEY", "your-gpt5-key")
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", "your-claude-key"))


async def run_pytest():
    """Run pytest and export results."""
    print("🧪 [Refactor Agent] Running pytest...")
    REFACTOR_DIR.mkdir(parents=True, exist_ok=True)
    if not (REFACTOR_DIR / ".git").exists():
        subprocess.run(["git", "worktree", "add", str(REFACTOR_DIR), "main"], check=False)

    # Use the current Python interpreter to invoke pytest for Windows PATH reliability
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--json-report",
        "--json-report-file",
        str(TEST_RESULTS),
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, cwd=REFACTOR_DIR)
    await proc.wait()

    if TEST_RESULTS.exists():
        print(f"✅ [Refactor Agent] Test results ready: {TEST_RESULTS}")
    else:
        print("⚠️ [Refactor Agent] No results found.")


async def fix_failures_with_gpt5():
    """Use GPT-5 to repair failed tests."""
    while not TEST_RESULTS.exists():
        print("🕒 Waiting for test results...")
        await asyncio.sleep(3)

    print("📄 Reading results...")
    async with aiofiles.open(TEST_RESULTS, "r") as f:
        results = json.loads(await f.read())

    failing = [
        t.get("nodeid", "").split("::")[0]
        for t in results.get("tests", [])
        if t.get("outcome") == "failed"
    ]
    failing = list(set(failing))
    if not failing:
        print("🎉 All tests passed, no fixes needed.")
        return

    print(f"🔧 Found {len(failing)} failing files: {failing}")

    with FileLock(str(LOCK_FILE)):
        for file in failing:
            file_path = REFACTOR_DIR / file
            if not file_path.exists():
                continue

            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()

            print(f"🤖 [GPT-5] Refactoring {file}...")
            response = openai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "You are a senior Python engineer."},
                    {
                        "role": "user",
                        "content": f"Fix any errors in this file so that tests pass:\n\n{content}",
                    },
                ],
            )

            fixed_code = response.choices[0].message.content
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(fixed_code)

    print("✅ [GPT-5] Refactor complete, rerun pytest to verify.")


async def update_docs_with_claude():
    """Use Claude Sonnet 4.5 to rewrite docs."""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if not (DOCS_DIR / ".git").exists():
        # Create a detached worktree to avoid branch conflicts with the refactor worktree
        subprocess.run(["git", "worktree", "add", "--detach", str(DOCS_DIR)], check=False)

    print("📚 [Claude Agent] Updating documentation...")

    with FileLock(str(LOCK_FILE)):
        files_to_update = list(Path(".").glob("docs/**/*.md"))
        if not files_to_update:
            print("ℹ️ No docs found, skipping.")
            return

        for doc in files_to_update:
            try:
                async with aiofiles.open(doc, "r", encoding="utf-8") as f:
                    text = await f.read()

                print(f"📝 [Claude] Rewriting {doc.name}...")
                message = anthropic_client.messages.create(
                    model="claude-3.5-sonnet",
                    max_tokens=2000,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Rewrite this documentation clearly "
                                "with up-to-date architecture:\n\n"
                                f"{text}"
                            ),
                        }
                    ],
                )
                updated = message.content[0].text
                target = DOCS_DIR / doc.name
                target.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(target, "w", encoding="utf-8") as f:
                    await f.write(updated)
            except Exception as e:
                print(f"⚠️ [Claude Agent] Skipping {doc.name} due to error: {e}")

    print("✅ [Claude] Documentation rewrite finished.")


async def orchestrate():
    """Run refactor/tests first; only then update docs."""
    print("🚀 Starting multi-agent orchestration...\n")

    # Phase 1: Test-and-fix loop until green
    while True:
        await run_pytest()
        if not TEST_RESULTS.exists():
            print("⚠️ No test results found; cannot proceed with refactor loop.")
            break

        try:
            with open(TEST_RESULTS, "r", encoding="utf-8") as f:
                results = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to read test results: {e}")
            break

        failing = list(
            {
                t.get("nodeid", "").split("::")[0]
                for t in results.get("tests", [])
                if t.get("outcome") == "failed"
            }
        )

        if failing:
            print(f"🔁 Tests failing in {len(failing)} file(s); attempting automated refactor...")
            await fix_failures_with_gpt5()
            # Loop will rerun pytest and re-evaluate
            continue
        else:
            print("✅ All tests are green. Proceeding to documentation phase.")
            break

    # Phase 2: Documentation updates (runs after tests are stable)
    await update_docs_with_claude()

    print("\n✅ Multi-Agent workflow finished successfully.")


if __name__ == "__main__":
    try:
        asyncio.run(orchestrate())
    except KeyboardInterrupt:
        print("🛑 Stopped by user.")
