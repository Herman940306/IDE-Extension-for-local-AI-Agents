import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure emoji logging does not explode on Windows consoles
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from httpx import AsyncClient  # noqa: E402
from src import main as backend_main  # noqa: E402
from src.core.container import Container  # noqa: E402


async def main() -> None:
    backend_main.container = Container()
    backend_main.llm_router = backend_main.container.llm_router()

    embeddings_service = backend_main.container.embeddings_service()
    if not getattr(embeddings_service, "is_initialized", False):
        await embeddings_service.initialize()

    async with AsyncClient(app=backend_main.app, base_url="http://test") as client:
        resp = await client.get(
            "/debug/embed",
            params={"sample": "def hello():\n    return 'hi'"},
        )
        print(resp.status_code)
        print(json.dumps(resp.json(), indent=2)[:1000])


if __name__ == "__main__":
    asyncio.run(main())
