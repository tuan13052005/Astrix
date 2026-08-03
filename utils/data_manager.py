"""
Lớp truy xuất dữ liệu bền vững của Astrix — bản dùng Supabase (Postgres).

QUAN TRỌNG: mọi hàm public trong file này giữ ĐÚNG tên và kiểu dữ liệu
trả về như bản cũ (dùng file JSON trong data/). Nhờ vậy commands/*.py,
utils/logger.py, utils/checks.py... không cần sửa gì cả — chỉ file này
và utils/db.py thay đổi.

Xem schema tương ứng tại supabase/schema.sql.
"""

from datetime import datetime
from typing import Any

from utils.db import get_client


# =========================================================
# HÀM PHỤ: CHUYỂN TIMESTAMP ISO (SUPABASE) -> EPOCH FLOAT
# (Code cũ dùng time.time() nên các nơi khác — vd commands/moderation.py
# — vẫn gọi datetime.fromtimestamp(entry["timestamp"], tz=timezone.utc))
# =========================================================

def _to_epoch(iso_str: str) -> float:
    return datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp()


# =========================================================
# GUILD SETTINGS (LƯU DƯỚI 1 CỘT JSONB "data" MỖI GUILD)
# =========================================================

def get_guild_settings(guild_id: int) -> dict:
    client = get_client()

    res = (
        client.table("guild_settings")
        .select("data")
        .eq("guild_id", guild_id)
        .maybe_single()
        .execute()
    )

    if res is None or res.data is None:
        return {}

    return res.data.get("data") or {}


def _save_guild_settings(guild_id: int, settings: dict) -> None:
    client = get_client()

    client.table("guild_settings").upsert(
        {"guild_id": guild_id, "data": settings}
    ).execute()


def set_guild_setting(guild_id: int, key: str, value: Any) -> None:
    settings = get_guild_settings(guild_id)
    settings[key] = value
    _save_guild_settings(guild_id, settings)


def get_log_channel_id(guild_id: int) -> int | None:
    return get_guild_settings(guild_id).get("log_channel_id")


# ---------------------------------------------------------
# WELCOME / GOODBYE / AUTOROLE
# ---------------------------------------------------------

def set_welcome(guild_id: int, channel_id: int, message: str) -> None:
    settings = get_guild_settings(guild_id)
    settings["welcome"] = {"channel_id": channel_id, "message": message}
    _save_guild_settings(guild_id, settings)


def disable_welcome(guild_id: int) -> None:
    settings = get_guild_settings(guild_id)
    settings.pop("welcome", None)
    _save_guild_settings(guild_id, settings)


def set_goodbye(guild_id: int, channel_id: int, message: str) -> None:
    settings = get_guild_settings(guild_id)
    settings["goodbye"] = {"channel_id": channel_id, "message": message}
    _save_guild_settings(guild_id, settings)


def disable_goodbye(guild_id: int) -> None:
    settings = get_guild_settings(guild_id)
    settings.pop("goodbye", None)
    _save_guild_settings(guild_id, settings)


def set_autorole(guild_id: int, role_id: int) -> None:
    set_guild_setting(guild_id, "autorole_id", role_id)


def disable_autorole(guild_id: int) -> None:
    settings = get_guild_settings(guild_id)
    settings.pop("autorole_id", None)
    _save_guild_settings(guild_id, settings)


# ---------------------------------------------------------
# AUTO-MODERATION
# ---------------------------------------------------------

DEFAULT_AUTOMOD = {
    "enabled": False,
    "block_links": False,
    "banned_words": []
}


def get_automod_settings(guild_id: int) -> dict:
    settings = get_guild_settings(guild_id)
    return {**DEFAULT_AUTOMOD, **settings.get("automod", {})}


def _save_automod_settings(guild_id: int, automod: dict) -> None:
    settings = get_guild_settings(guild_id)
    settings["automod"] = automod
    _save_guild_settings(guild_id, settings)


def set_automod_enabled(guild_id: int, enabled: bool) -> None:
    automod = get_automod_settings(guild_id)
    automod["enabled"] = enabled
    _save_automod_settings(guild_id, automod)


def set_automod_block_links(guild_id: int, block: bool) -> None:
    automod = get_automod_settings(guild_id)
    automod["block_links"] = block
    _save_automod_settings(guild_id, automod)


def add_banned_word(guild_id: int, word: str) -> bool:
    automod = get_automod_settings(guild_id)
    word = word.lower().strip()

    if word in automod["banned_words"]:
        return False

    automod["banned_words"].append(word)
    _save_automod_settings(guild_id, automod)
    return True


def remove_banned_word(guild_id: int, word: str) -> bool:
    automod = get_automod_settings(guild_id)
    word = word.lower().strip()

    if word not in automod["banned_words"]:
        return False

    automod["banned_words"].remove(word)
    _save_automod_settings(guild_id, automod)
    return True


# =========================================================
# HỆ THỐNG CẢNH CÁO (WARNINGS) — BẢNG "warnings"
# =========================================================

def add_warning(
    guild_id: int,
    member_id: int,
    moderator_id: int,
    reason: str
) -> dict:
    """Thêm một cảnh cáo mới và trả về entry vừa tạo."""

    client = get_client()

    res = (
        client.table("warnings")
        .insert({
            "guild_id": guild_id,
            "member_id": member_id,
            "moderator_id": moderator_id,
            "reason": reason,
        })
        .execute()
    )

    row = res.data[0]

    return {
        "id": row["id"],
        "moderator_id": row["moderator_id"],
        "reason": row["reason"],
        "timestamp": _to_epoch(row["created_at"]),
    }


def get_warnings(guild_id: int, member_id: int) -> list:
    client = get_client()

    res = (
        client.table("warnings")
        .select("*")
        .eq("guild_id", guild_id)
        .eq("member_id", member_id)
        .order("id")
        .execute()
    )

    return [
        {
            "id": row["id"],
            "moderator_id": row["moderator_id"],
            "reason": row["reason"],
            "timestamp": _to_epoch(row["created_at"]),
        }
        for row in (res.data or [])
    ]


def remove_warning(guild_id: int, member_id: int, warn_id: int) -> bool:
    """Xóa một cảnh cáo theo ID. Trả về True nếu xóa thành công."""

    client = get_client()

    res = (
        client.table("warnings")
        .delete()
        .eq("guild_id", guild_id)
        .eq("member_id", member_id)
        .eq("id", warn_id)
        .execute()
    )

    return bool(res.data)


def clear_warnings(guild_id: int, member_id: int) -> None:
    client = get_client()

    client.table("warnings").delete().eq("guild_id", guild_id).eq(
        "member_id", member_id
    ).execute()


# =========================================================
# NHẮC NHỞ (REMINDERS) — BẢNG "reminders"
# =========================================================

def add_reminder(
    guild_id: int | None,
    channel_id: int,
    user_id: int,
    remind_at: float,
    message: str
) -> dict:
    client = get_client()

    res = (
        client.table("reminders")
        .insert({
            "guild_id": guild_id,
            "channel_id": channel_id,
            "user_id": user_id,
            "remind_at": remind_at,
            "message": message,
        })
        .execute()
    )

    return res.data[0]


def get_due_reminders(now: float) -> list:
    client = get_client()

    res = (
        client.table("reminders")
        .select("*")
        .lte("remind_at", now)
        .execute()
    )

    return res.data or []


def get_user_reminders(user_id: int) -> list:
    client = get_client()

    res = (
        client.table("reminders")
        .select("*")
        .eq("user_id", user_id)
        .order("remind_at")
        .execute()
    )

    return res.data or []


def remove_reminder(reminder_id: int) -> bool:
    client = get_client()

    res = client.table("reminders").delete().eq("id", reminder_id).execute()

    return bool(res.data)


# =========================================================
# GIVEAWAY — BẢNG "giveaways"
# =========================================================

def create_giveaway(
    guild_id: int,
    channel_id: int,
    message_id: int,
    host_id: int,
    prize: str,
    winners_count: int,
    end_time: float
) -> dict:
    client = get_client()

    entry = {
        "message_id": message_id,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "host_id": host_id,
        "prize": prize,
        "winners_count": winners_count,
        "end_time": end_time,
        "participants": [],
        "ended": False,
    }

    client.table("giveaways").insert(entry).execute()

    return entry


def get_giveaway(message_id: int) -> dict | None:
    client = get_client()

    res = (
        client.table("giveaways")
        .select("*")
        .eq("message_id", message_id)
        .maybe_single()
        .execute()
    )

    return res.data if res else None


def get_active_giveaways() -> list:
    client = get_client()

    res = (
        client.table("giveaways")
        .select("*")
        .eq("ended", False)
        .execute()
    )

    return res.data or []


def get_due_giveaways(now: float) -> list:
    return [
        entry for entry in get_active_giveaways()
        if entry["end_time"] <= now
    ]


def add_giveaway_participant(message_id: int, user_id: int) -> bool:
    """Trả về True nếu vừa thêm mới, False nếu đã tham gia rồi."""

    giveaway = get_giveaway(message_id)

    if giveaway is None:
        return False

    participants = giveaway.get("participants") or []

    if user_id in participants:
        return False

    participants.append(user_id)

    client = get_client()
    client.table("giveaways").update(
        {"participants": participants}
    ).eq("message_id", message_id).execute()

    return True


def mark_giveaway_ended(message_id: int) -> None:
    client = get_client()

    client.table("giveaways").update({"ended": True}).eq(
        "message_id", message_id
    ).execute()


# =========================================================
# DJ ROLE (GIỚI HẠN QUYỀN DÙNG LỆNH NHẠC)
# =========================================================

def get_dj_role_id(guild_id: int) -> int | None:
    return get_guild_settings(guild_id).get("dj_role_id")


def set_dj_role_id(guild_id: int, role_id: int) -> None:
    set_guild_setting(guild_id, "dj_role_id", role_id)


def disable_dj_role(guild_id: int) -> None:
    settings = get_guild_settings(guild_id)
    settings.pop("dj_role_id", None)
    _save_guild_settings(guild_id, settings)