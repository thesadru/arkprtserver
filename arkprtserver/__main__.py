"""Entry-point."""
import logging
import os

import aiohttp.web

import arkprtserver.app


def main() -> None:
    """Entry-point."""
    handler = logging.StreamHandler()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    aiohttp.web.run_app(  # pyright: ignore[reportUnknownMemberType]
        arkprtserver.app.app,
        host=os.environ.get("HOST"),
        port=int(os.environ.get("PORT", "8080")),
    )


if __name__ == "__main__":
    main()
