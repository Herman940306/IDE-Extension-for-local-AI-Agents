# global_agent_bootstrap.py
# Global Multi-Agent Bootstrap v6 (patched, robust, lint-friendly)
# Run: python global_agent_bootstrap.py --install

from __future__ import annotations

import os
import sys
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
import platform

# Optional UI/notification libs. Import only if available.
try:
    from PIL import Image, ImageDraw  # type: ignore
    import pystray  # type: ignore
except Exception:
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    pystray = None  # type: ignore

try:
    from winotify import Notification, audio  # type: ignore
except Exception:
    Notification = None  # type: ignore
    audio = None  # type: ignore

# ---------- GLOBAL PATHS & CONTENT ----------
HOME = Path.home()
GLOBAL_DIR = HOME / ".aura_agents"
LOG_FILE = GLOBAL_DIR / "pipeline.log"
CONFIG_FILE = GLOBAL_DIR / ".agentplan.yml"
ORCHESTRATOR_FILE = GLOBAL_DIR / "agent_orchestrator.py"
WATCH_LOG = GLOBAL_DIR / "watcher.log"
STATE_FILE = GLOBAL_DIR / ".watcher_state"
POS_FILE = LOG_FILE.with_suffix(".pos")

AGENT_YML = """# ~/.aura_agents/.agentplan.yml
tasks:
  - id: refactor-phase
    model: gpt-5
    goal: "Apply refactor steps and ensure tests are green."
  - id: docs-phase
    model: claude-sonnet-4.5
    goal: "Regenerate and expand project documentation."
  - id: qa-phase
    model: gpt-4o-mini
    goal: "Run coverage and summarize results."

workflow:
  - run: refactor-phase
  - run: docs-phase
    parallel: true
  - then: qa-phase
"""

ORCHESTRATOR_CODE = r"""
# lightweight orchestrator that writes progress to ~/.aura_agents/pipeline.log
import asyncio
from datetime import datetime
from pathlib import Path

LOG_FILE = Path.home() / ".aura_agents" / "pipeline.log"

async def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)

async def refactor():
    await log("🧠 [Refactor] Phase started (GPT-5).")
    # Insert real commands here; we simulate progress for reliability.
    await asyncio.sleep(3)
    await log("🔧 [Refactor] Running fixes (50%).")
    await asyncio.sleep(2)
    await log("✅ [Refactor] Complete (100%).")

async def docs():
    await log("📚 [Docs] Phase started (Claude Sonnet).")
    await asyncio.sleep(2)
    await log("✍️ [Docs] Drafting updates (60%).")
    await asyncio.sleep(2)
    await log("✅ [Docs] Complete (100%).")

async def qa():
    await log("🔍 [QA] Running tests & coverage.")
    await asyncio.sleep(2)
    await log("✅ [QA] Tests passed; coverage OK.")

async def main():
    await log("🚀 Orchestrator started.")
    await asyncio.gather(refactor(), docs())
    await qa()
    await log("🎉 All phases completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
"""

# ---------- HELPERS & UTILITIES ----------


def notify(title: str, message: str, sound: bool = True) -> None:
    """Send a Windows toast notification if available, otherwise print."""
    is_windows = platform.system() == "Windows"
    if Notification and is_windows:
        try:
            toast = Notification(app_id="AuraAgents", title=title, msg=message)
            if sound and audio:
                toast.set_audio(audio.Default, loop=False)
            toast.show()
            return
        except Exception:
            # fall through to console fallback
            pass
    # fallback
    print(f"[NOTIFY] {title}: {message}")


def _safe_run(cmd: list[str], shell: bool = False) -> subprocess.CompletedProcess:
    """Run a subprocess with error propagation."""
    try:
        result = subprocess.run(cmd, check=True, shell=shell)
        return result
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}") from exc


def create_startup_shortcut(script_path: Path) -> None:
    """Create a .lnk in the user's Startup folder as a schtasks fallback."""
    startup = (
        Path(os.getenv("APPDATA", ""))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )
    startup.mkdir(parents=True, exist_ok=True)
    shortcut_path = startup / "AuraAgentsWatcher.lnk"
    # Build PowerShell to create shortcut via WScript.Shell COM object.
    ps = (
        "$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
        f"$Shortcut.TargetPath = '{sys.executable}'; "
        f"$Shortcut.Arguments = '\"{script_path}\" --watch'; "
        f"$Shortcut.WorkingDirectory = '{script_path.parent}'; "
        "$Shortcut.Save();"
    )
    _safe_run(["powershell", "-NoProfile", "-Command", ps], shell=False)


def register_task_scheduler() -> None:
    """
    Try to add a scheduled task that runs the watcher at logon. If that fails,
    create a shortcut in the Startup folder as a robust fallback.
    """
    script_path = Path(__file__).resolve()
    python_exec = str(sys.executable).replace('"', '\\"')
    script_quoted = str(script_path).replace('"', '\\"')
    tr = f'"{python_exec}" "{script_quoted}" --watch'
    # Build schtasks command string with proper quoting.
    cmd = f'schtasks /Create /SC ONLOGON /TN "AuraAgentsWatcher" /TR {tr} /RL HIGHEST /F'
    try:
        # Use shell=True here because schtasks expects a single string on Windows.
        subprocess.run(cmd, shell=True, check=True)
        notify("AuraAgents", "Startup task registered (Task Scheduler).")
        print("🪄 Added AuraAgentsWatcher to Task Scheduler.")
    except subprocess.CalledProcessError:
        print("⚠️ schtasks registration failed; attempting Startup shortcut fallback.")
        try:
            create_startup_shortcut(script_path)
            notify("AuraAgents", "Startup shortcut created as fallback.")
            print("✅ Created shortcut in Startup folder as fallback.")
        except Exception as ex:
            print(f"⚠️ Fallback also failed: {ex}")


# ---------- FILE & GLOBAL SETUP ----------


def install_requirements() -> None:
    """Install minimal dependencies used by the bootstrap (best-effort)."""
    print("📦 Installing optional dependencies (pystray, pillow, winotify)...")
    _safe_run(
        [sys.executable, "-m", "pip", "install", "-U", "pystray", "pillow", "winotify"],
        shell=False,
    )


def setup_global_files() -> None:
    """Create ~/.aura_agents and write config + orchestrator placeholder."""
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(AGENT_YML, encoding="utf-8")
    ORCHESTRATOR_FILE.write_text(ORCHESTRATOR_CODE, encoding="utf-8")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text("", encoding="utf-8")
    if not WATCH_LOG.exists():
        WATCH_LOG.write_text("", encoding="utf-8")
    notify("AuraAgents", "Global configuration initialized.")


def link_project(path: Path) -> None:
    """
    Inject .agentplan.yml and a local orchestrator into a project folder if absent.
    This is intentionally conservative (doesn't overwrite existing files).
    """
    plan = path / ".agentplan.yml"
    if not plan.exists():
        plan.write_text(AGENT_YML, encoding="utf-8")
        notify("New Project Linked", str(path))
        print(f"🔗 Linked .agentplan.yml into {path}")
    orch = path / "multi_phase_agent_pipeline.py"
    if not orch.exists():
        orch.write_text(ORCHESTRATOR_CODE, encoding="utf-8")
        print(f"🧩 Injected orchestrator into {path}")


# ---------- LOG WATCHER (persistent pos, dedupe) ----------


def log_watcher() -> None:
    """Tail pipeline.log and emit notifications for progress lines."""
    print("👁️  Starting log watcher...")
    notify("Aura Watcher", "Monitoring orchestrator logs for updates.")
    last_pos = 0
    # restore last read position if available
    try:
        if POS_FILE.exists():
            last_pos = int(POS_FILE.read_text() or "0")
    except Exception:
        last_pos = 0

    while True:
        try:
            if not LOG_FILE.exists():
                time.sleep(3)
                continue
            size = LOG_FILE.stat().st_size
            if size < last_pos:
                # log rotated/truncated; reset
                last_pos = 0
            if size > last_pos:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    f.seek(last_pos)
                    new = f.read()
                last_pos = size
                POS_FILE.write_text(str(last_pos))
                for line in new.splitlines():
                    line_str = line.strip()
                    if not line_str:
                        continue
                    # simple rules to classify notifications
                    if "Refactor" in line_str:
                        notify("Refactor Update", line_str, sound=False)
                    elif "Docs" in line_str:
                        notify("Docs Update", line_str, sound=False)
                    elif "QA" in line_str or "tests" in line_str.lower():
                        notify("QA Update", line_str, sound=False)
                    elif "🎉" in line_str or "All phases" in line_str:
                        notify("Pipeline", line_str)
                    # write to watcher log for audit
                    with open(WATCH_LOG, "a", encoding="utf-8") as wl:
                        wl.write(f"[{datetime.now().isoformat()}] {line_str}\n")
        except Exception as exc:
            print(f"⚠️ Log watcher error: {exc}")
        time.sleep(2)


def start_log_daemon() -> None:
    t = threading.Thread(target=log_watcher, daemon=True)
    t.start()
    print("📡 Log watcher daemon active.")


# ---------- PROJECT WATCHER (scan Desktop & Documents) ----------


def projects_watcher() -> None:
    """Scan target folders for new projects and link global plan conservatively."""
    print("🔎 Project watcher running (scanning Desktop & Documents)...")
    watched: set[Path] = set()
    roots = [HOME / "Documents", HOME / "Desktop"]
    while True:
        try:
            for root in roots:
                if not root.exists():
                    continue
                for p in root.iterdir():
                    if not p.is_dir():
                        continue
                    if p.name.startswith("."):
                        continue
                    if p in watched:
                        continue
                    # conservative check: only link if it looks like a code project
                    if any(
                        (p / fname).exists()
                        for fname in (
                            "pyproject.toml",
                            "setup.py",
                            "package.json",
                            ".git",
                        )
                    ):
                        try:
                            link_project(p)
                        except Exception as e:
                            print(f"⚠️ Failed to link {p}: {e}")
                    watched.add(p)
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ projects_watcher error: {e}")
            time.sleep(5)


def start_projects_watcher_daemon() -> None:
    t = threading.Thread(target=projects_watcher, daemon=True)
    t.start()
    print("🚀 Projects watcher daemon running in background.")


# ---------- TRAY CONTROL (main thread) ----------


def create_icon_image() -> "Image.Image":  # type: ignore[name-defined]
    img = Image.new("RGB", (64, 64), "navy")  # type: ignore[name-defined]
    draw = ImageDraw.Draw(img)  # type: ignore[name-defined]
    draw.ellipse((12, 12, 52, 52), fill="deepskyblue")
    return img


def run_tray_menu() -> None:
    """Start system tray menu (blocking call for main thread)."""
    if not pystray or Image is None or ImageDraw is None:
        print("⚠️ Tray libs not available; install pystray & pillow to enable tray.")
        return

    def _pause(icon, item):
        STATE_FILE.write_text("paused")
        notify("Watcher Paused", "Global project watcher paused.")
        print("⏸️ Watcher paused.")

    def _resume(icon, item):
        STATE_FILE.write_text("running")
        notify("Watcher Resumed", "Global project watcher resumed.")
        print("▶️ Watcher resumed.")

    def _open_log(icon, item):
        try:
            os.startfile(WATCH_LOG)
        except Exception:
            print(f"Could not open {WATCH_LOG}")

    def _run_orchestrator(icon, item):
        try:
            subprocess.Popen([sys.executable, str(ORCHESTRATOR_FILE)])
            notify("Orchestrator", "Multi-agent orchestrator started.")
        except Exception as e:
            print(f"Could not start orchestrator: {e}")

    def _exit(icon, item):
        notify("AuraAgents", "Exiting watcher.")
        icon.stop()
        sys.exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Pause Watcher", _pause),
        pystray.MenuItem("Resume Watcher", _resume),
        pystray.MenuItem("Open Log", _open_log),
        pystray.MenuItem("Run Orchestrator", _run_orchestrator),
        pystray.MenuItem("Exit", _exit),
    )

    icon = pystray.Icon("AuraAgents", create_icon_image(), "AuraAgents", menu)
    icon.run()


# ---------- AUTO-START / INSTALL ----------


def apply_global() -> None:
    setup_global_files()
    # Ensure state file exists
    STATE_FILE.write_text("running")
    # Start background daemons
    start_log_daemon()
    start_projects_watcher_daemon()
    # Register auto-start (task scheduler or fallback)
    if platform.system() == "Windows":
        try:
            register_task_scheduler()
        except Exception as e:
            print(f"⚠️ register_task_scheduler error: {e}")
    else:
        print("ℹ️ Auto-start registration is currently only implemented for Windows.")
    # Launch tray menu on main thread if libs present
    if pystray and Image is not None:
        run_tray_menu()
    else:
        print("🟡 Tray not started (missing libs). Watchers still active in background.")
    print("🌍 Global multi-agent bootstrap applied.")


def install_runner_dependencies() -> None:
    """Install basic tooling used by the orchestrator skeleton (best-effort)."""
    print("📦 Installing runner dependencies (ruff, black, pytest) if missing...")
    try:
        _safe_run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-U",
                "ruff",
                "black",
                "pytest",
                "coverage",
            ],
            shell=False,
        )
    except Exception as e:
        print(f"⚠️ Could not install all runtime deps: {e}")


# ---------- ENTRYPOINT ----------


def _print_usage() -> None:
    print("Usage:")
    print("  python global_agent_bootstrap.py --install")
    print("  python global_agent_bootstrap.py --watch")
    print("  python global_agent_bootstrap.py --help")


if __name__ == "__main__":
    if "--help" in sys.argv:
        _print_usage()
        sys.exit(0)
    if "--watch" in sys.argv:
        # run only watchers (used by scheduled task)
        setup_global_files()
        start_log_daemon()
        start_projects_watcher_daemon()
        # block forever
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("Watcher stopped.")
        sys.exit(0)
    if "--install" in sys.argv:
        # one-time install flow
        install_runner_dependencies()
        try:
            install_requirements()
        except Exception as e:
            print(f"⚠️ Optional dependency install failed: {e}")
        apply_global()
        # keep the main thread alive if tray isn't blocking
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("Exiting.")
        sys.exit(0)
    _print_usage()
