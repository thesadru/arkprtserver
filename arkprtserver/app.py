"""Server app."""
import asyncio
import bisect
import os
import sys
import typing
import urllib.parse

import aiohttp.web
import arkprts
import dotenv
import jinja2

from . import gamepress

__all__ = ("app",)

dotenv.load_dotenv()

app = aiohttp.web.Application()
routes = aiohttp.web.RouteTableDef()
env = jinja2.Environment(loader=jinja2.PackageLoader("arkprtserver"), autoescape=True)

# not actually pure, gamedata is just delayed
client = arkprts.Client(pure=True)

FAVOR_FRAMES: list[int] = []


def get_image(type: str, id: str) -> str:
    id = str(id)
    id = id.replace("@", "_") if "@" in id else id.replace("#", "_")
    id = urllib.parse.quote(id)

    return f"https://raw.githubusercontent.com/Aceship/Arknight-Images/main/{type}/{id}.png"


def calculate_trust(trust: int) -> int:
    """Calculate the percentage to display for certain trust points."""
    return bisect.bisect_left(FAVOR_FRAMES, trust)


async def get_gamepress_tierlist() -> dict[str, gamepress.GamepressOperator]:
    """Get gamepress tierlist."""
    operators = await gamepress.get_gamepress_tierlist()

    operator_names = {
        operator.name: id for id, operator in client.gamedata.character_table.items() if id.startswith("char_")
    }

    for operator in operators:
        # I'm not handling this, too annoying
        if operator.name == "Amiya (Guard)":
            continue
        if operator.name == "Rosa (Poca)":
            operator.name = "Rosa"

        operator.operator_id = operator_names[operator.name]

    return {operator.operator_id: operator for operator in operators if operator.operator_id}


def _get_client(pure: bool = False) -> arkprts.Client:
    """Get a client for a given channel uid and token."""
    subclient = arkprts.Client(pure=pure)
    subclient.config = client.config
    subclient.gamedata = client.gamedata

    return subclient


env_globals = dict(
    get_image=get_image,
    calculate_trust=calculate_trust,
    client=client,
    gamedata=client.gamedata,
)
env.globals.update(env_globals)  # type: ignore


async def startup(app: aiohttp.web.Application) -> None:
    """Startup function."""
    await client.login_with_token(os.environ["CHANNEL_UID"], os.environ["YOSTAR_TOKEN"])
    task = asyncio.create_task(startup_gamedata(app))
    task.add_done_callback(lambda _: None)  # little hack


app.on_startup.append(startup)


async def startup_gamedata(app: aiohttp.web.Application) -> None:
    """Load gamedata."""
    await client.gamedata.download_gamedata()

    global FAVOR_FRAMES  # noqa: PLW0603 # globals :(
    frames = client.gamedata.favor_table.favor_frames
    FAVOR_FRAMES = [frame["data"].favor_point for frame in frames]  # pyright: ignore[reportConstantRedefinition]

    env.globals["tierlist"] = await get_gamepress_tierlist()  # type: ignore


@aiohttp.web.middleware
async def startup_middleware(
    request: aiohttp.web.Request,
    handler: typing.Callable[[aiohttp.web.Request], typing.Awaitable[aiohttp.web.StreamResponse]],
) -> aiohttp.web.StreamResponse:
    """Startup middleware."""
    if not FAVOR_FRAMES:
        template = env.get_template("startup.html.j2")
        return aiohttp.web.Response(text=template.render(request=request), content_type="text/html")

    return await handler(request)


app.middlewares.append(startup_middleware)


@routes.get("/")
async def index(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Index page."""
    template = env.get_template("index.html.j2")
    return aiohttp.web.Response(text=template.render(request=request), content_type="text/html")


@routes.get("/search")
async def search(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Search for users."""
    users: typing.Sequence[arkprts.models.Player] = []
    if request.query.get("nickname"):
        users = await client.search_player(request.query["nickname"])

    if request.query.get("all") not in ("1", "true"):
        users = [user for user in users if user.level >= 10]

    template = env.get_template("search.html.j2")
    return aiohttp.web.Response(text=template.render(users=users, request=request), content_type="text/html")


@routes.get("/login")
async def login(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """Login."""
    user_client = _get_client(pure=True)
    template = env.get_template("login.html.j2")
    response = aiohttp.web.Response(text=template.render(request=request), content_type="text/html")

    if not request.query.get("email"):
        return response

    if not request.query.get("code"):
        try:
            await user_client._request_yostar_auth(request.query["email"])
        except arkprts.errors.BaseArkprtsError as e:
            return aiohttp.web.Response(text=template.render(request=request, error=str(e)), content_type="text/html")

        return response

    try:
        yostar_uid, yostar_token = await user_client._submit_yostar_auth(request.query["email"], request.query["code"])
        channel_uid, token = await user_client._get_yostar_token(request.query["email"], yostar_uid, yostar_token)
    except arkprts.errors.BaseArkprtsError as e:
        return aiohttp.web.Response(text=template.render(request=request, error=str(e)), content_type="text/html")

    response = aiohttp.web.HTTPTemporaryRedirect("/user")
    response.set_cookie("channel_uid", channel_uid)
    response.set_cookie("token", token)

    return response


@routes.get("/user")
async def user(request: aiohttp.web.Request) -> aiohttp.web.Response:
    """User."""
    if not request.cookies.get("channel_uid") or not request.cookies.get("token"):
        return aiohttp.web.HTTPTemporaryRedirect("/login")

    user_client = _get_client()
    try:
        await user_client.login_with_token(request.cookies["channel_uid"], request.cookies["token"])
    except arkprts.errors.BaseArkprtsError:
        response = aiohttp.web.HTTPTemporaryRedirect("/login")
        response.del_cookie("channel_uid")
        response.del_cookie("token")
        return response

    user = await user_client.get_data()

    template = env.get_template("user.html.j2")
    return aiohttp.web.Response(text=template.render(user=user, request=request), content_type="text/html")


app.router.add_static("/static", "arkprtserver/static", name="static")
app.add_routes(routes)


def entrypoint(argv: list[str] = sys.argv) -> aiohttp.web.Application:
    """Return app as dummy aiohttp entrypoint."""
    return app
