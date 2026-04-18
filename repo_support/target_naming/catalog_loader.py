from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast


def mapping_value(loaded: Mapping[object, object], key: str) -> dict[object, object]:
    value = loaded.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a mapping")
    return dict(cast(Mapping[object, object], value))


def mapping_mapping(
    loaded: Mapping[object, object],
) -> dict[str, dict[object, object]]:
    result: dict[str, dict[object, object]] = {}
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, Mapping):
            raise ValueError("expected a mapping of string keys to mappings")
        result[key] = dict(cast(Mapping[object, object], value))
    return result


def string_mapping(loaded: Mapping[object, object]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in loaded.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("expected a mapping of string keys to string values")
        result[key] = value
    return result


def mapping_sequence(
    loaded: Mapping[object, object],
) -> dict[str, tuple[object, ...]]:
    result: dict[str, tuple[object, ...]] = {}
    for key, value in loaded.items():
        if (
            not isinstance(key, str)
            or not isinstance(value, Sequence)
            or isinstance(value, (str, bytes))
        ):
            raise ValueError("expected a mapping of string keys to sequences")
        result[key] = tuple(cast(Sequence[object], value))
    return result


def sequence_value(loaded: Mapping[object, object], key: str) -> tuple[object, ...]:
    value = loaded.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a sequence")
    return tuple(cast(Sequence[object], value))


def mapping_sequence_value(
    loaded: Mapping[object, object],
    key: str,
) -> tuple[dict[object, object], ...]:
    values = sequence_value(loaded, key)
    result: list[dict[object, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError(f"{key} must contain mappings")
        result.append(dict(cast(Mapping[object, object], value)))
    return tuple(result)


def optional_sequence_value(
    loaded: Mapping[object, object], key: str
) -> tuple[object, ...]:
    value = loaded.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a sequence")
    return tuple(cast(Sequence[object], value))


def string_tuple(values: Sequence[object]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("expected string sequence")
        result.append(value)
    return tuple(result)


def string_value(loaded: Mapping[object, object], key: str) -> str:
    value = loaded.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def int_value(loaded: Mapping[object, object], key: str) -> int:
    value = loaded.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


def bool_value(loaded: Mapping[object, object], key: str) -> bool:
    value = loaded.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value
