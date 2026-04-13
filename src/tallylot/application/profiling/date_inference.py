"""Date-only inference helpers for CSV profiling."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

_SLASH_DATE_PATTERN = re.compile(r"(?P<first>\d{2})/(?P<second>\d{2})/(?P<year>\d{4})$")
_FILENAME_DATE_PATTERN = re.compile(
    r"(?P<year>\d{4})[-_.](?P<month>\d{2})[-_.](?P<day>\d{2})"
)
_DATE_FORMATS = ("%d/%m/%Y", "%m/%d/%Y")


@dataclass(frozen=True)
class _SlashDateToken:
    first: int
    second: int
    year: int
    raw: str


@dataclass(frozen=True)
class _SlashDateCandidate:
    date_format: str
    token_count: int
    parsed_values: tuple[datetime, ...]


def infer_date_only_format(
    values: list[str],
    *,
    filename: str = "",
) -> str | None:
    normalized_values = [value.strip() for value in values if value.strip()]
    iso_values = [value for value in normalized_values if is_iso_date_only(value)]
    slash_tokens = _slash_date_tokens(normalized_values)
    if iso_values and not slash_tokens:
        return "%Y-%m-%d"
    if not slash_tokens or iso_values:
        return None

    candidates = _slash_candidates(slash_tokens)
    formats_to_try = (
        _slash_date_format_from_component_bounds(slash_tokens),
        _slash_date_format_from_chronology(slash_tokens, candidates),
        _slash_date_format_from_filename_anchor(candidates, filename=filename),
    )
    return next((fmt for fmt in formats_to_try if fmt is not None), None)


def filename_anchored_date_only_format(value: str, *, filename: str) -> str | None:
    tokens = _slash_date_tokens([value])
    if not tokens:
        return None
    return _slash_date_format_from_filename_anchor(
        _slash_candidates(tokens), filename=filename
    )


def is_iso_date_only(text: str) -> bool:
    return len(text) == 10 and text.count("-") == 2


def _slash_date_tokens(values: list[str]) -> tuple[_SlashDateToken, ...]:
    tokens: list[_SlashDateToken] = []
    for value in values:
        match = _SLASH_DATE_PATTERN.fullmatch(value)
        if match is None:
            continue
        tokens.append(
            _SlashDateToken(
                first=int(match.group("first")),
                second=int(match.group("second")),
                year=int(match.group("year")),
                raw=value,
            )
        )
    return tuple(tokens)


def _slash_candidates(
    tokens: tuple[_SlashDateToken, ...],
) -> tuple[_SlashDateCandidate, ...]:
    return tuple(
        _SlashDateCandidate(
            date_format=date_format,
            token_count=len(tokens),
            parsed_values=tuple(
                parsed
                for token in tokens
                if (parsed := _try_datetime(token.raw, date_format)) is not None
            ),
        )
        for date_format in _DATE_FORMATS
    )


def _slash_date_format_from_component_bounds(
    tokens: tuple[_SlashDateToken, ...],
) -> str | None:
    day_first_evidence = any(token.second <= 12 < token.first for token in tokens)
    month_first_evidence = any(token.first <= 12 < token.second for token in tokens)
    if day_first_evidence == month_first_evidence:
        return None
    return "%d/%m/%Y" if day_first_evidence else "%m/%d/%Y"


def _slash_date_format_from_chronology(
    tokens: tuple[_SlashDateToken, ...],
    candidates: tuple[_SlashDateCandidate, ...],
) -> str | None:
    candidate_map = {candidate.date_format: candidate for candidate in candidates}
    supported_formats = [
        candidate.date_format
        for candidate in candidates
        if _chronology_supports_inference(tokens, candidate.parsed_values)
    ]
    if len(supported_formats) != 1:
        return None

    winner = supported_formats[0]
    loser = next(date_format for date_format in _DATE_FORMATS if date_format != winner)
    winner_candidate = candidate_map[winner]
    loser_candidate = candidate_map[loser]
    if not _has_decisive_chronology_witness(
        winner_candidate.parsed_values, loser_candidate.parsed_values
    ):
        return None
    return winner


def _chronology_supports_inference(
    tokens: tuple[_SlashDateToken, ...],
    parsed_values: tuple[datetime, ...],
) -> bool:
    if len(parsed_values) != len(tokens) or len(parsed_values) < 3:
        return False
    if not _slash_components_vary(tokens):
        return False
    if not all(
        left <= right
        for left, right in zip(parsed_values, parsed_values[1:], strict=False)
    ):
        return False
    adjacent_gaps = [
        (right - left).days
        for left, right in zip(parsed_values, parsed_values[1:], strict=False)
    ]
    return bool(adjacent_gaps) and max(adjacent_gaps) <= 45


def _slash_components_vary(tokens: tuple[_SlashDateToken, ...]) -> bool:
    first_values = {token.first for token in tokens}
    second_values = {token.second for token in tokens}
    return len(first_values) > 1 and len(second_values) > 1


def _has_decisive_chronology_witness(
    winner_values: tuple[datetime, ...],
    loser_values: tuple[datetime, ...],
) -> bool:
    for winner_left, winner_right, loser_left, loser_right in zip(
        winner_values,
        winner_values[1:],
        loser_values,
        loser_values[1:],
        strict=False,
    ):
        winner_gap = (winner_right - winner_left).days
        loser_gap = (loser_right - loser_left).days
        if 0 <= winner_gap <= 7 and (loser_gap < 0 or loser_gap > 21):
            return True
    return False


def _slash_date_format_from_filename_anchor(
    candidates: tuple[_SlashDateCandidate, ...],
    *,
    filename: str,
) -> str | None:
    if not filename:
        return None
    matching_formats = [
        candidate.date_format
        for candidate in candidates
        if _filename_matches_any_slash_date(candidate, filename=filename)
    ]
    if len(matching_formats) == 1:
        return matching_formats[0]
    return None


def _filename_matches_any_slash_date(
    candidate: _SlashDateCandidate,
    *,
    filename: str,
) -> bool:
    if len(candidate.parsed_values) != candidate.token_count:
        return False
    if not candidate.parsed_values:
        return False

    anchored_dates: list[datetime] = []
    for filename_match in _FILENAME_DATE_PATTERN.finditer(filename):
        try:
            anchored_dates.append(
                datetime(
                    int(filename_match.group("year")),
                    int(filename_match.group("month")),
                    int(filename_match.group("day")),
                    tzinfo=UTC,
                )
            )
        except ValueError:
            continue
    return bool(anchored_dates) and any(
        anchored.date() == parsed.date()
        for anchored in anchored_dates
        for parsed in candidate.parsed_values
    )


def _try_datetime(text: str, fmt: str) -> datetime | None:
    try:
        return datetime.strptime(text, fmt).replace(tzinfo=UTC)
    except ValueError:
        return None
