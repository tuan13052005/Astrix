import json
import os
import time
from typing import Any


# =========================================================
# ĐƯỜNG DẪN FILE DỮ LIỆU
# =========================================================

DATA_DIR = "data"
GUILD_SETTINGS_FILE = os.path.join(DATA_DIR, "guild_settings.json")
WARNINGS_FILE = os.path.join(DATA_DIR, "warnings.json")
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")
GIVEAWAYS_FILE = os.path.join(DATA_DIR, "giveaways.json")


# =========================================================
# HÀM DÙNG CHUNG: ĐỌC / GHI JSON
# =========================================================

def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(path: str) -> dict:
    _ensure_data_dir()

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_json(path: str, data: dict) -> None:
    _ensure_data_dir()

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# =========================================================
# GUILD SETTINGS (VD: KÊNH LOG)
# =========================================================

def get_guild_settings(guild_id: int) -> dict:
    data = _load_json(GUILD_SETTINGS_FILE)
    return data.get(str(guild_id), {})


def set_guild_setting(guild_id: int, key: str, value: Any) -> None:
    data = _load_json(GUILD_SETTINGS_FILE)
    guild_data = data.setdefault(str(guild_id), {})
    guild_data[key] = value
    _save_json(GUILD_SETTINGS_FILE, data)


def get_log_channel_id(guild_id: int) -> int | None:
    return get_guild_settings(guild_id).get("log_channel_id")


# ---------------------------------------------------------
# WELCOME / GOODBYE / AUTOROLE
# ---------------------------------------------------------

def set_welcome(guild_id: int, channel_id: int, message: str) -> None:
    settings = get_guild_settings(guild_id)
    settings["welcome"] = {"channel_id": channel_id, "message": message}
    data = _load_json(GUILD_SETTINGS_FILE)
    data[str(guild_id)] = settings
    _save_json(GUILD_SETTINGS_FILE, data)


def disable_welcome(guild_id: int) -> None:
    settings = get_guild_settings(guild_id)
    settings.pop("welcome", None)
    data = _load_json(GUILD_SETTINGS_FILE)
    data[str(guild_id)] = settings
    _save_json(GUILD_SETTINGS_FILE, data)


def set_goodbye(guild_id: int, channel_id: int, message: str) -> None:
    settings = get_guild_settings(guild_id)
    settings["goodbye"] = {"channel_id": channel_id, "message": message}
    data = _load_json(GUILD_SETTINGS_FILE)
    data[str(guild_id)] = settings
    _save_json(GUILD_SETTINGS_FILE, data)


def disable_goodbye(guild_id: int) -> None:
    settings = get_guild_settings(guild_id)
    settings.pop("goodbye", None)
    data = _load_json(GUILD_SETTINGS_FILE)
    data[str(guild_id)] = settings
    _save_json(GUILD_SETTINGS_FILE, data)


def set_autorole(guild_id: int, role_id: int) -> None:
    set_guild_setting(guild_id, "autorole_id", role_id)


def disable_autorole(guild_id: int) -> None:
    settings = get_guild_settings(guild_id)
    settings.pop("autorole_id", None)
    data = _load_json(GUILD_SETTINGS_FILE)
    data[str(guild_id)] = settings
    _save_json(GUILD_SETTINGS_FILE, data)


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
    data = _load_json(GUILD_SETTINGS_FILE)
    data[str(guild_id)] = settings
    _save_json(GUILD_SETTINGS_FILE, data)


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
# HỆ THỐNG CẢNH CÁO (WARNINGS)
# =========================================================

def add_warning(
    guild_id: int,
    member_id: int,
    moderator_id: int,
    reason: str
) -> dict:
    """Thêm một cảnh cáo mới và trả về entry vừa tạo."""

    data = _load_json(WARNINGS_FILE)
    guild_data = data.setdefault(str(guild_id), {})
    member_warns = guild_data.setdefault(str(member_id), [])

    next_id = (
        max(entry["id"] for entry in member_warns) + 1
        if member_warns else 1
    )

    entry = {
        "id": next_id,
        "moderator_id": moderator_id,
        "reason": reason,
        "timestamp": time.time()
    }

    member_warns.append(entry)
    _save_json(WARNINGS_FILE, data)

    return entry


def get_warnings(guild_id: int, member_id: int) -> list:
    data = _load_json(WARNINGS_FILE)
    return data.get(str(guild_id), {}).get(str(member_id), [])


def remove_warning(guild_id: int, member_id: int, warn_id: int) -> bool:
    """Xóa một cảnh cáo theo ID. Trả về True nếu xóa thành công."""

    data = _load_json(WARNINGS_FILE)
    guild_data = data.get(str(guild_id), {})
    member_warns = guild_data.get(str(member_id), [])

    for index, entry in enumerate(member_warns):
        if entry["id"] == warn_id:
            member_warns.pop(index)
            _save_json(WARNINGS_FILE, data)
            return True

    return False


def clear_warnings(guild_id: int, member_id: int) -> None:
    data = _load_json(WARNINGS_FILE)
    guild_data = data.get(str(guild_id), {})

    if str(member_id) in guild_data:
        guild_data[str(member_id)] = []
        _save_json(WARNINGS_FILE, data)


# =========================================================
# NHẮC NHỞ (REMINDERS)
# =========================================================

def add_reminder(
    guild_id: int | None,
    channel_id: int,
    user_id: int,
    remind_at: float,
    message: str
) -> dict:
    data = _load_json(REMINDERS_FILE)
    reminders = data.setdefault("reminders", [])

    next_id = (
        max(entry["id"] for entry in reminders) + 1
        if reminders else 1
    )

    entry = {
        "id": next_id,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "user_id": user_id,
        "remind_at": remind_at,
        "message": message
    }

    reminders.append(entry)
    _save_json(REMINDERS_FILE, data)

    return entry


def get_due_reminders(now: float) -> list:
    data = _load_json(REMINDERS_FILE)
    reminders = data.get("reminders", [])
    return [entry for entry in reminders if entry["remind_at"] <= now]


def get_user_reminders(user_id: int) -> list:
    data = _load_json(REMINDERS_FILE)
    reminders = data.get("reminders", [])
    return [entry for entry in reminders if entry["user_id"] == user_id]


def remove_reminder(reminder_id: int) -> bool:
    data = _load_json(REMINDERS_FILE)
    reminders = data.get("reminders", [])

    for index, entry in enumerate(reminders):
        if entry["id"] == reminder_id:
            reminders.pop(index)
            _save_json(REMINDERS_FILE, data)
            return True

    return False


# =========================================================
# GIVEAWAY
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
    data = _load_json(GIVEAWAYS_FILE)
    giveaways = data.setdefault("giveaways", [])

    entry = {
        "id": message_id,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "message_id": message_id,
        "host_id": host_id,
        "prize": prize,
        "winners_count": winners_count,
        "end_time": end_time,
        "participants": [],
        "ended": False
    }

    giveaways.append(entry)
    _save_json(GIVEAWAYS_FILE, data)

    return entry


def get_giveaway(message_id: int) -> dict | None:
    data = _load_json(GIVEAWAYS_FILE)
    for entry in data.get("giveaways", []):
        if entry["message_id"] == message_id:
            return entry
    return None


def get_active_giveaways() -> list:
    data = _load_json(GIVEAWAYS_FILE)
    return [
        entry for entry in data.get("giveaways", [])
        if not entry["ended"]
    ]


def get_due_giveaways(now: float) -> list:
    return [
        entry for entry in get_active_giveaways()
        if entry["end_time"] <= now
    ]


def add_giveaway_participant(message_id: int, user_id: int) -> bool:
    """Trả về True nếu vừa thêm mới, False nếu đã tham gia rồi."""

    data = _load_json(GIVEAWAYS_FILE)

    for entry in data.get("giveaways", []):
        if entry["message_id"] == message_id:
            if user_id in entry["participants"]:
                return False

            entry["participants"].append(user_id)
            _save_json(GIVEAWAYS_FILE, data)
            return True

    return False


def mark_giveaway_ended(message_id: int) -> None:
    data = _load_json(GIVEAWAYS_FILE)

    for entry in data.get("giveaways", []):
        if entry["message_id"] == message_id:
            entry["ended"] = True
            _save_json(GIVEAWAYS_FILE, data)
            return


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
    data = _load_json(GUILD_SETTINGS_FILE)
    data[str(guild_id)] = settings
    _save_json(GUILD_SETTINGS_FILE, data)
