"""Parsing gamepress data. Not in-game data."""
import typing

import bs4
import pydantic

__all__ = ["GamepressOperator", "TIERS", "get_gamepress_tierlist"]

TIERS: list[str] = [
    "EX",
    "S+",
    "S",
    "S-",
    "A+",
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "D+",
    "D",
    "D-",
    "E+",
    "E",
    "E-",
    "X",
]


class GamepressOperator(pydantic.BaseModel):
    """Gamepress operator with minimal data."""

    name: str
    """Operator name."""
    tier: str
    """Operator tier."""
    class_name: str
    """Operator class."""
    archetype_name: str
    """Operator archetype."""
    explanation: typing.Mapping[typing.Literal["summary", "positive", "negative"], typing.Sequence[str]]
    """Tier explanation."""

    operator_id: str = ""
    """Operator ID."""
    char: object | None = None
    """Operator data."""

    @property
    def tier_index(self) -> int:
        """Get the tier index."""
        return TIERS.index(self.tier)


def parse_raw_tierlist(text: str) -> typing.Any:
    """Get the tier list."""
    soup = bs4.BeautifulSoup(text, "html.parser")

    tierlist: list[typing.Any] = []
    for container in soup.find_all(class_="operator-tier-container"):
        category = {
            "gamepress_class_id": container["data-categorya"],
            "gamepress_archetype_id": container["data-categoryb"],
        }

        # category headers and such
        title_text = [x.string.strip() for x in container.h2.children if x.string and x.string.strip()]
        category["class_name"] = title_text[0]
        *other_archetype_names, archetype_name = title_text[1].split(" / ")
        category["archetype_name"] = archetype_name
        if other_archetype_names:
            category["archetype_gamepress_name"] = other_archetype_names[0]

        # category tiers
        category["tiers"] = []
        for tier_row in container.find_all("tr"):
            tier = {"tier": tier_row["data-tier"]}

            tier["operators"] = []
            for tier_cell in tier_row.find_all(class_="tier-list-cell-row"):
                # operator headers
                operator = {
                    "gamepress_rarity_id": tier_cell["data-categoryc"],
                    "ranged": tier_cell["data-position-range"],
                    "damage_type": tier_cell["data-damagetype"],
                }
                operator["gamepress_tags"] = [x.strip() for x in tier_cell["data-ability-tags"].split(",")]

                # operator data
                operator["rarity"] = len(tier_cell.find(class_="rarity-icon").find_all("img"))
                operator["name"] = tier_cell.find(class_="operator-title").string.strip()

                # explanation
                operator["explanation"] = {"summary": [], "positive": [], "negative": []}
                explanation = list(tier_cell.find(class_="tier-expl-container").children)[1].string.strip()

                raw_explanations = " ".join(explanation.split()).replace("<br >", "<br>").split("<br>")
                explanations = [bs4.BeautifulSoup(i, "html.parser").text.strip() for i in raw_explanations]
                # sometimes the period is on the start of the next line
                explanations = [i.lstrip(". ") for i in explanations if i]

                explanation_tagged = {"=": "summary", "+": "positive", "-": "negative"}
                for line in explanations:
                    operator["explanation"][explanation_tagged[line[0]]].append(line.lstrip("+-= "))  # type: ignore

                tier["operators"].append(operator)  # type: ignore

            category["tiers"].append(tier)  # type: ignore

        tierlist.append(category)

    return tierlist


async def get_gamepress_tierlist() -> list[GamepressOperator]:
    """Get the tier list."""
    import aiohttp

    url = "https://gamepress.gg/arknights/tier-list/arknights-operator-tier-list"
    async with aiohttp.ClientSession() as session, session.get(url) as resp:
        text = await resp.text()

    operators: list[GamepressOperator] = []

    for archetype in parse_raw_tierlist(text):
        for tier in archetype["tiers"]:
            for operator in tier["operators"]:
                operators.append(
                    GamepressOperator(
                        name=operator["name"],
                        tier=tier["tier"],
                        class_name=archetype["class_name"],
                        archetype_name=archetype["archetype_name"],
                        explanation=operator["explanation"],
                    ),
                )

    return operators
