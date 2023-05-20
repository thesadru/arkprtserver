"""Server app."""
import bisect
import os
import sys
import urllib.parse

import aiohttp.web
import arkprts
import dotenv
import jinja2

__all__ = ("app",)

dotenv.load_dotenv()

app = aiohttp.web.Application()
routes = aiohttp.web.RouteTableDef()
env = jinja2.Environment(loader=jinja2.PackageLoader("arkprtserver"), autoescape=True)

client = arkprts.Client()

FAVOR_FRAMES: list[int] = []


def get_image(type: str, id: str) -> str:
    id = str(id)
    id = id.replace("@", "_") if "@" in id else id.replace("#", "_")
    id = urllib.parse.quote(id)

    return f"https://raw.githubusercontent.com/Aceship/Arknight-Images/main/{type}/{id}.png"


def calculate_trust(trust: int) -> int:
    """Calculate the percentage to display for certain trust points."""
    return bisect.bisect_left(FAVOR_FRAMES, trust)


env_globals = dict(
    get_image=get_image,
    calculate_trust=calculate_trust,
    client=client,
    gamedata=client.gamedata,
)
env.globals.update(env_globals)  # type: ignore


@app.on_startup.append
async def startup(app: aiohttp.web.Application) -> None:
    """Startup function."""
    await client.login_with_token(os.environ["CHANNEL_UID"], os.environ["YOSTAR_TOKEN"])

    global FAVOR_FRAMES  # noqa: 0603 # globals :(
    frames = client.gamedata._get_excel("favor_table").favor_frames
    FAVOR_FRAMES = [frame["data"].favor_point for frame in frames]  # pyright: ignore[reportConstantRedefinition]


@routes.get("/")
async def index(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Index page."""
    template = env.get_template("index.html.j2")
    if request.query.get("nickname"):
        users = await client.search_player(request.query["nickname"])
    else:
        users = []

    return aiohttp.web.Response(text=template.render(users=users), content_type="text/html")


app.router.add_static("/static", "arkprtserver/static", name="static")
app.add_routes(routes)


def entrypoint(argv: list[str] = sys.argv) -> aiohttp.web.Application:
    """Return app as dummy aiohttp entrypoint."""
    return app
