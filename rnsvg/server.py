"""RNSVG aiohttp server entry point."""

from __future__ import annotations

import argparse
import sys
import webbrowser

from aiohttp import web
from aiohttp.web_runner import GracefulExit

from rnsvg.config import AppConfig
from rnsvg.rns_transport import RNSTransport
from rnsvg.router import AppState, create_app, public_dir_path, wire_messaging_events
from rnsvg.version import __version__


def build_application(config: AppConfig) -> web.Application:
    config.ensure_data_dir()
    transport = RNSTransport(config)
    transport.start()

    state = AppState(
        config=config,
        transport=transport,
        public_dir=public_dir_path(),
    )
    wire_messaging_events(state)
    return create_app(state)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RNSVG stub backend")
    parser.add_argument(
        "--host",
        default=None,
        help="Web server listen address (default: 127.0.0.1 or RNSVG_HOST)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Web server listen port (default: 8000 or RNSVG_PORT)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Do not open a browser tab on startup",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = AppConfig.from_env(web_host=args.host, web_port=args.port)
    config.headless = args.headless

    app = build_application(config)
    url = f"http://{config.web_host}:{config.web_port}"
    public_dir = public_dir_path()

    print(f"RNSVG {__version__}")
    print(f"Starting web server at {url}")
    if not public_dir.is_dir():
        print(
            f"Warning: frontend bundle not found at {public_dir} "
            "(run pnpm run build-frontend)",
        )

    if not config.headless:
        try:
            webbrowser.open(url)
        except Exception as exc:
            print(f"Warning: could not open browser: {exc}")

    try:
        web.run_app(app, host=config.web_host, port=config.web_port, print=None)
    except (KeyboardInterrupt, GracefulExit):
        return 0
    except OSError as exc:
        print(f"Failed to start server: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())