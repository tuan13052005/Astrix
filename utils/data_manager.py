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
