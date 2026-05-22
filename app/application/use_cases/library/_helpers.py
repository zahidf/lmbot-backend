from typing import Optional


def normalize_library_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    return normalized[:-1] if normalized.endswith("s") else normalized


def type_matches(actual: str, requested: Optional[str]) -> bool:
    normalized_requested = normalize_library_type(requested)
    if normalized_requested is None:
        return True
    normalized_actual = normalize_library_type(actual)
    return normalized_actual == normalized_requested


def clean_name(name: str, field_name: str = "name") -> str:
    cleaned = name.strip()
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned
