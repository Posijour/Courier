import asyncio
import importlib
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import ModuleType
from typing import Callable


def load_start_bot() -> Callable[[], object]:
    """Load start_bot from common project layouts."""
    candidates = ("app.bot", "bot")

    for module_name in candidates:
        try:
            module: ModuleType = importlib.import_module(module_name)
        except ModuleNotFoundError:
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
    start_bot = load_start_bot()

    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
