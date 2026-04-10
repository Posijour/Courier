import asyncio
import importlib
from importlib import util as importlib_util
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Callable


def configure_module_search_path() -> Path:
    """Ensure Python can import bot modules from common Render layouts."""
    cwd = Path.cwd().resolve()

    candidate_roots: list[Path] = [cwd, cwd / "src"]
    candidate_roots.extend(
        path for path in cwd.iterdir() if path.is_dir() and not path.name.startswith(".")
    )

    for root in candidate_roots:
        has_app_bot = (root / "app" / "bot.py").is_file()
        has_flat_bot = (root / "bot.py").is_file()
        if has_app_bot or has_flat_bot:
            root_str = str(root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            return root

    return cwd


def load_start_bot() -> Callable[[], object]:
    """Load start_bot from common project layouts."""
    candidates = ("app.bot", "bot")

    for module_name in candidates:
        try:
            module_spec = importlib_util.find_spec(module_name)
        except ModuleNotFoundError:
            # importlib can raise when a package prefix (e.g. "app" in "app.bot")
            # does not exist. Treat this as "module not found" and continue.
            continue

        if module_spec is None:
            continue

        try:
            module: ModuleType = importlib.import_module(module_name)
        except ModuleNotFoundError:
            # If import fails due to a missing dependency, keep probing other
            # layout candidates before failing with a clear aggregate message.
            continue

        start_bot = getattr(module, "start_bot", None)
        if callable(start_bot):
            return start_bot

    searched = ", ".join(candidates)
    raise ModuleNotFoundError(
        f"Cannot find callable start_bot in modules: {searched}. "
        "Make sure the bot package is included in the deploy bundle."
    )


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return

        body = b"ok\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_HEAD(self) -> None:
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def run_health_server() -> None:
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


def main() -> None:
    project_root = configure_module_search_path()
    print(f"[startup] project root for imports: {project_root}")

    start_bot = load_start_bot()

    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
