"""Export user data to various services."""

import typing
import urllib.parse

import arkprts.models
import typing_extensions

T = typing.TypeVar("T")

KroosterOperators = typing.Mapping[
    str,
    typing.TypedDict(
        "Operator",
        {
            "id": str,
            "name": str,
            "favorite": bool,
            "rarity": int,
            "class": str,
            "potential": int,
            "promotion": int,
            "owned": bool,
            "level": int,
            "skillLevel": int,
            "mastery": list[typing.Optional[int]],
            "module": list[typing.Optional[int]],
            "skin": typing_extensions.NotRequired[str],
        },
    ),
]


def get_krooster_skin(skin: str, char_id: str) -> str:
    """Turn skin and char id into an aceship skin id."""
    if "@" in skin:  # shop skin
        return skin.replace("@", "_")
    if skin.endswith("#1"):  # default skin
        return char_id
    # E2 skin
    return skin.replace("#", "_")


def export_krooster_operators(user: arkprts.models.User) -> KroosterOperators:
    """Export characters to krooster."""
    data: KroosterOperators = {}
    for char in user.troop.chars.values():
        # anything for amiya, even code repetition <3
        if char.tmpl:
            for char_id, tmpl in char.tmpl.items():
                data[char_id] = {
                    "id": char_id,
                    "name": "Amiya",
                    "favorite": char.star_mark,
                    "rarity": 5,
                    "class": {
                        "char_002_amiya": "Caster",
                        "char_1001_amiya2": "Guard",
                    }.get(char_id, "Medic"),
                    "potential": char.potential_rank + 1,
                    "promotion": char.evolve_phase,
                    "owned": True,
                    "level": char.level,
                    "skillLevel": char.main_skill_lvl,
                    "mastery": [skill.specialize_level or None for skill in tmpl.skills],
                    "module": [module.level if not module.locked else None for module in tmpl.equip.values()][1:],
                    "skin": urllib.parse.quote(get_krooster_skin(tmpl.skin_id, char_id)),
                }
            continue

        data[char.char_id] = {
            "id": char.char_id,
            "name": char.static.name,
            "favorite": char.star_mark,
            "rarity": int(char.static.rarity[-1]),
            "class": {
                "WARRIOR": "Guard",
                "SNIPER": "Sniper",
                "TANK": "Defender",
                "MEDIC": "Medic",
                "SUPPORT": "Supporter",
                "CASTER": "Caster",
                "SPECIAL": "Specialist",
                "PIONEER": "Vanguard",
            }[char.static.profession],
            "potential": char.potential_rank + 1,
            "promotion": char.evolve_phase,
            "owned": True,
            "level": char.level,
            "skillLevel": char.main_skill_lvl,
            "mastery": [skill.specialize_level or None for skill in char.skills],
            "module": [module.level if not module.locked else None for module in char.equip.values()][1:],
            "skin": urllib.parse.quote(get_krooster_skin(char.skin, char.char_id)),
        }

    return data


def export_krooster_items(user: arkprts.models.User) -> str:
    """Export items to krooster as csv."""
    header = "itemId,owned\n"
    return header + "\n".join(f"{item_id},{count}" for item_id, count in user.inventory.items() if count > 0)


PenguinStatisticsItem = typing.TypedDict(  # noqa: UP013
    "PenguinStatisticsItem",
    {
        "id": str,
        "have": int,
        "need": int,
    },
)
PenguinStatisticsOption = typing.TypedDict(  # noqa: UP013
    "PenguinStatisticsOption",
    {
        "byProduct": bool,
        "requireExp": bool,
        "requireLmb": bool,
    },
)
PenguinStatistics = typing.TypedDict(
    "PenguinStatistics",
    {
        "@type": typing.Literal["@penguin-statistics/planner/config"],
        "items": list[PenguinStatisticsItem],
        "options": PenguinStatisticsOption,
        "excludes": list[str],
    },
)


def export_penguin_statistics(
    user: arkprts.models.User,
    previous: typing.Optional[PenguinStatistics] = None,
) -> PenguinStatistics:
    """Export items to penguin statistics."""
    data: PenguinStatistics = {
        "@type": "@penguin-statistics/planner/config",
        "items": [],
        "options": previous["options"] if previous else {"byProduct": False, "requireExp": False, "requireLmb": False},
        "excludes": previous["excludes"] if previous else [],
    }

    item_need: dict[str, int] = {}
    if previous is not None:
        for item in previous["items"]:
            item_need[item["id"]] = item["need"]

    for item_id, count in user.inventory.items():
        if count <= 0 and item_need.get(item_id, 0) <= 0:
            continue

        data["items"].append(
            {
                "id": item_id,
                "have": count,
                "need": item_need.get(item_id, 0),
            },
        )

    return data
