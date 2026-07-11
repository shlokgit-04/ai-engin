from datetime import datetime


def validate_required(data: dict, fields: list[str]) -> tuple[bool, str | None]:
    for field in fields:
        if field not in data or data[field] is None:
            return False, f"{field.replace('_', ' ').title()} is required."
    return True, None


def validate_not_empty(value: str | None, name: str) -> tuple[bool, str | None]:
    if not value or not value.strip():
        return False, f"{name} cannot be empty."
    return True, None


def validate_date(date_str: str | None) -> tuple[bool, str | None]:
    if date_str is None:
        return True, None
    valid_keywords = {"today", "tomorrow"}
    if isinstance(date_str, str) and date_str.lower() in valid_keywords:
        return True, None
    try:
        datetime.strptime(str(date_str), "%Y-%m-%d")
        return True, None
    except ValueError:
        return False, f"'{date_str}' is not a valid date. Please use YYYY-MM-DD format."


def validate_priority(priority: str | None) -> tuple[bool, str | None]:
    if priority is None:
        return True, None
    if priority.lower() not in ("high", "medium", "normal", "low"):
        return False, f"'{priority}' is not a valid priority. Use high, medium, normal, or low."
    return True, None
