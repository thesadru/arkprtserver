"""Entry-point."""
import logging
import sys

import aiohttp.web

import arkprtserver.app


def main(argv: list[str] = sys.argv) -> None:
    """Entry-point."""
    formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    aiohttp.web.run_app(arkprtserver.app.app)  # pyright: ignore[reportUnknownMemberType]


if __name__ == "__main__":
    main()
