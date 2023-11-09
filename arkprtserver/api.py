"""Server app."""
from __future__ import annotations

import datetime
import re
import typing

import aiohttp
import aiohttp.web
import arkprts

from . import app as app_module

__all__ = ("api_routes",)

api_routes = aiohttp.web.RouteTableDef()


def format_blackboard(string: str, blackboard: typing.Mapping[str, object]) -> str:
    """Format an object that uses arknight's 'blackboard' templating."""

    def replacer(match: re.Match[str]) -> str:
        key, frm = match[1], match[2]
        value = str(blackboard.get(key, "0"))
        if value.replace(".", "").isnumeric() and float(value).is_integer():
            value = str(int(float(value)))
        if frm and "%" in frm:
            value = str(round(float(value) * 100)) + "%"

        return value

    string = re.sub(r"{(.+?)(?:\:(.+?))?}", replacer, string)
    return re.sub(r"<([@$].+?|/)>", "", string)


@api_routes.get("/api/raw/search")
async def search_raw(request: aiohttp.web.Request) -> aiohttp.web.StreamResponse:
    """Search for users."""
    client: arkprts.Client = request.app["client"]

    server = request.query.get("server", "en")
    if server not in ("en", "jp", "kr"):
        return aiohttp.web.json_response({"message": "Unsupported server"}, status=400)

    nickname, nicknumber = request.query.get("nickname"), request.query.get("nicknumber", "")
    if not nickname:
        return aiohttp.web.json_response({"message": "Missing 'nickname' param"}, status=400)
    if "#" in nickname:
        nickname, nicknumber = nickname.split("#", 1)

    uid_data = await client.search_raw_player_ids(nickname, nicknumber, server=server)
    data = await client.get_raw_friend_info([uid["uid"] for uid in uid_data["result"]], server=server)
    users = data["friends"]

    return aiohttp.web.json_response(users)


@api_routes.get("/api/search")
async def search(request: aiohttp.web.Request) -> aiohttp.web.StreamResponse:  # noqa: PLR0912, PLR0915, C901
    """Search for players but with data."""
    # help this is way too damn complex
    client: arkprts.Client = request.app["client"]

    server = request.query.get("server", "en")
    if server not in ("en", "jp", "kr"):
        return aiohttp.web.json_response({"message": "Unsupported server"}, status=400)

    lang = request.query.get("lang", server)
    if lang not in ("en", "jp", "kr", "cn"):
        return aiohttp.web.json_response({"message": "Unsupported language"}, status=400)

    nickname, nicknumber = request.query.get("nickname"), request.query.get("nicknumber", "")
    if not nickname:
        return aiohttp.web.json_response({"message": "Missing 'nickname' param"}, status=400)

    users = await client.search_players(nickname, nicknumber, server=server)

    return_data: typing.Any = []
    for user in users:
        user_data: typing.Any = {
            "nickname": user.nickname,
            "nicknumber": user.nick_number,
            "uid": user.uid,
            "server": user.server_name,
            "level": user.level,
            "avatar": ...,
            "supports": ...,
            "last_online": user.last_online_time.astimezone(datetime.timezone.utc).isoformat(),
            "medals": ...,
            "registration": user.register_ts.astimezone(datetime.timezone.utc).isoformat(),
            "progression": ...,
            "characters": user.char_cnt,
            "furniture": user.furn_cnt,
            "assistant": ...,
            "bio": user.resume,
            "factions": ...,
            "clues": ...,
        }

        if user.avatar:
            user_data["avatar"] = {
                "type": user.avatar.type,
                "id": user.avatar.id,
                "asset": None,
            }
            if user.avatar.type == "ASSISTANT":
                user_data["avatar"]["asset"] = app_module.get_avatar(user.secretary, user.secretary_skin_id)
        else:
            user_data["avatar"] = {"type": "DEFAULT", "id": None, "asset": None}

        user_data["supports"] = []
        for char in user.assist_char_list or []:
            if not char:
                continue

            char_data = client.assets.get_operator(char.char_id, server=lang)

            en_class_name = {
                "WARRIOR": "Guard",
                "SNIPER": "Sniper",
                "TANK": "Defender",
                "MEDIC": "Medic",
                "SUPPORT": "Supporter",
                "CASTER": "Caster",
                "SPECIAL": "Specialist",
                "PIONEER": "Vanguard",
            }[char_data.profession]

            team = client.assets.get_excel("handbook_team_table", server=lang)
            support: typing.Any = {
                "id": char.char_id,
                "name": char_data.name,
                "nation": team[char_data.nation_id].power_name if char_data.get("nation_id") else None,
                "team": team[char_data.team_id].power_name if char_data.get("team_id") else None,
                "number": char_data.display_number,
                "tags": list(char_data.tag_list),
                "rarity": char_data.rarity[-1],
                "class": {
                    "id": char_data.profession,
                    "name": en_class_name,
                    "asset": app_module.get_image("classes", "class_" + en_class_name.lower()),
                },
                "archetype": {
                    "id": char_data.sub_profession_id,
                    "name": client.assets.get_excel("uniequip_table", server=lang)
                    .sub_prof_dict[char_data.sub_profession_id]
                    .sub_profession_name,
                    "asset": app_module.get_image("ui/subclass", "sub_" + char_data.sub_profession_id + "_icon"),
                },
                "skin": {
                    "id": char.skin_id,
                    "asset": app_module.get_avatar(char.char_id, char.skin_id),
                },
                "skills": {
                    "level": char.main_skill_lvl,
                    "selected": char.skill_index if char.skill_index != -1 else None,
                    "skills": [],
                },
                "elite": char.evolve_phase,
                "trust": {
                    "points": char.favor_point,
                    "percent": char.trust,
                },
                "potential": char.potential_rank,
                "level": char.level,
                "contingency": dict(char.crisis_record),
                "modules": {
                    "selected": list(char.equip.keys()).index(char.current_equip) if char.current_equip else None,
                    "modules": [],
                },
                "talents": [],
            }

            for index, skill in enumerate(char.skills):
                lv = char.main_skill_lvl + skill.specialize_level - 1
                skill_data = client.assets.get_excel("skill_table", server=lang)[skill.skill_id]["levels"][lv]
                skill = {
                    "id": skill.skill_id,
                    "name": skill_data.name,
                    "description": format_blackboard(skill_data.description, skill_data.blackboard),
                    "sp": {
                        "type": skill_data.sp_data.sp_type,
                        "cost": skill_data.sp_data.sp_cost,
                        "initial": skill_data.sp_data.init_sp,
                        "charges": skill_data.sp_data.max_charge_time,
                    },
                    "asset": app_module.get_image(
                        "skills",
                        "skill_icon_" + (skill.static.get("icon_id") or skill.skill_id),
                    ),
                    "unlocked": skill.unlock,
                    "level": char.main_skill_lvl,
                    "mastery": skill.specialize_level,
                    "selected": index == char.skill_index,
                }
                support["skills"]["skills"].append(skill)

            for module_id, module in char.equip.items():
                module_data = client.assets.get_module(module_id, server=lang)
                module = {
                    "id": module_id,
                    "name": module_data.uni_equip_name,
                    "level": module.level,
                    "type": {
                        "name": module_data.type_icon.upper(),
                        "name1": module_data.type_name1,
                        "name2": module_data.get("type_name2"),
                        "asset": app_module.get_image("equip/type", module_data.type_icon),
                    },
                    "asset": app_module.get_image("equip/icon", module_id),
                    "hidden": module.hide,
                    "locked": module.locked,
                    "selected": module_id == char.current_equip,
                }
                support["modules"]["modules"].append(module)

            for talent_c in char_data.talents:
                candidate = next(
                    (
                        candidate
                        for candidate in reversed(talent_c.candidates)
                        if candidate.required_potential_rank <= char.potential_rank
                        and int(candidate.unlock_condition.phase[-1]) <= char.evolve_phase
                    ),
                    None,
                )
                if candidate is None:
                    continue

                talent = {
                    "name": candidate.name,
                    "description": format_blackboard(candidate.description, candidate.blackboard),
                    "requirements": {
                        "elite": int(candidate.unlock_condition.phase[-1]),
                        "potential": candidate.required_potential_rank,
                    },
                }
                support["talents"].append(talent)

            user_data["supports"].append(support)

        if user.medal_board.custom:
            user_data["medals"] = {
                "type": user.medal_board.type,
                "template": None,
                "medals": [],
            }
            for medal in user.medal_board.custom.layout:
                # static_medal = client.assets.get_medal(medal.id, server=lang)
                static_medal = next(
                    m for m in client.assets.get_excel("medal_table", server=lang).medal_list if m.medal_id == medal.id
                )
                user_data["medals"]["medals"].append(
                    {
                        "id": medal.id,
                        "pos": medal.pos,
                        "asset": app_module.get_image("ui/medalicon", medal.id),
                        "name": static_medal.medal_name,
                        "description": static_medal.get("description"),
                        "method": static_medal.get("get_method"),
                    },
                )
        elif user.medal_board.template:
            medal_group = next(
                medal_group
                for groups in client.assets.get_excel("medal_table", server=lang).medal_type_data.values()
                for medal_group in groups.group_data
                if medal_group.group_id == user.medal_board.template.group_id
            )
            user_data["medals"] = {
                "type": user.medal_board.type,
                "template": {
                    "id": user.medal_board.template.group_id,
                    "name": medal_group.group_name,
                    "description": medal_group.group_desc,
                    "medals": list(medal_group.medal_id),
                },
                "medals": [],
            }
            for medal in user.medal_board.template.medal_list:
                static_medal = next(
                    m for m in client.assets.get_excel("medal_table", server=lang).medal_list if m.medal_id == medal
                )
                user_data["medals"]["medals"].append(
                    {
                        "id": medal,
                        "pos": None,
                        "asset": app_module.get_image("ui/medalicon", medal),
                        "name": static_medal.medal_name,
                        "description": static_medal.get("description"),
                        "method": static_medal.get("get_method"),
                    },
                )
        else:
            user_data["medals"] = {
                "type": user.medal_board.type,
                "template": None,
                "medals": [],
            }

        if user.main_stage_progress:
            stage = client.assets.get_excel("stage_table", server=lang).stages[user.main_stage_progress]
            user_data["progression"] = {
                "id": user.main_stage_progress,
                "code": stage.code,
                "name": stage.name,
                "description": stage.description,
                "level": stage.danger_level,
            }
        else:
            user_data["progression"] = {"id": None, "code": None, "name": None, "description": None, "level": None}

        assistant = client.assets.get_operator(user.secretary, server=lang)
        if assistant:  # null for new accounts
            user_data["assistant"] = {
                "id": user.secretary,
                "name": assistant.name,
                "skin": {
                    "id": user.secretary_skin_id,
                    "asset": app_module.get_avatar(user.secretary, user.secretary_skin_id),
                },
            }
        else:
            user_data["assistant"] = {"id": None, "name": None, "skin": {"id": None, "asset": None}}

        user_data["factions"] = []
        for team, count in user.team_v2.items():
            faction = client.assets.get_excel("handbook_team_table", server=lang)[team]
            user_data["factions"].append(
                {
                    "id": team,
                    "name": faction.power_name,
                    "code": faction.power_code,
                    "asset": app_module.get_image("factions", "logo_" + team),
                    "operators": count,
                },
            )

        user_data["clues"] = []
        for board in user.board:
            clue = next(i for i in client.assets.get_excel("clue_data", server=lang).clues if i.clue_type == board)
            clue_type = next(
                i for i in client.assets.get_excel("clue_data", server=lang).clue_types if i.clue_type == board
            )
            user_data["clues"].append(
                {
                    "id": board,
                    "number": clue_type.clue_number,
                    "name": clue.clue_name,
                },
            )

        return_data.append(user_data)

    return aiohttp.web.json_response(return_data)
