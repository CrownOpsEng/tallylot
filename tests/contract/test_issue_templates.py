from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

import yaml

from repo_support.paths import repo_root


def _template_dir() -> Path:
    return repo_root() / ".github" / "ISSUE_TEMPLATE"


def _string_key_dict(value: Mapping[object, object]) -> dict[str, object]:
    return {str(key): item for key, item in value.items() if isinstance(key, str)}


def _load_yaml(path: Path) -> dict[str, object]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, Mapping), f"{path} must contain a YAML mapping"
    return _string_key_dict(cast(Mapping[object, object], loaded))


def _body_items(form: dict[str, object], *, path: Path) -> list[dict[str, object]]:
    body = form.get("body")
    assert isinstance(body, list) and body, f"{path} body is missing"
    typed_body = cast(list[object], body)

    items: list[dict[str, object]] = []
    for item in typed_body:
        assert isinstance(item, Mapping), f"{path} body item must be a mapping"
        items.append(_string_key_dict(cast(Mapping[object, object], item)))
    return items


def _attributes(item: dict[str, object]) -> dict[str, object]:
    attributes = item.get("attributes")
    assert isinstance(attributes, Mapping), "issue template item attributes are missing"
    return _string_key_dict(cast(Mapping[object, object], attributes))


def _template_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path for path in _template_dir().glob("*.yml") if path.name != "config.yml"
        )
    )


def test_issue_template_config_disables_blank_issues_and_points_to_docs() -> None:
    config = _load_yaml(_template_dir() / "config.yml")

    assert config["blank_issues_enabled"] is False
    contact_links = config.get("contact_links")
    assert isinstance(contact_links, list) and contact_links, (
        "contact_links are missing"
    )
    typed_contact_links = cast(list[object], contact_links)
    contact = typed_contact_links[0]
    assert isinstance(contact, Mapping)
    url = cast(Mapping[object, object], contact).get("url")
    assert isinstance(url, str)
    assert "docs/README.md" in url


def test_issue_template_filenames_define_stable_order() -> None:
    assert [path.name for path in _template_files()] == [
        "01-bug.yml",
        "02-workflow-gap.yml",
        "03-ops-follow-up.yml",
    ]


def test_issue_forms_share_required_sections_and_scope_checks() -> None:
    required_labels = {
        "Summary",
        "Repo Area",
        "Relevant Paths",
        "Problem",
        "Evidence",
        "Desired Outcome",
        "Acceptance Criteria",
        "Submission Checks",
    }

    for path in _template_files():
        form = _load_yaml(path)
        assert "assignees" not in form
        assert "projects" not in form
        assert "type" not in form

        body = _body_items(form, path=path)

        markdown_notice = body[0]
        assert markdown_notice.get("type") == "markdown"
        notice_text = str(_attributes(markdown_notice).get("value", ""))
        assert "repo-engineering work" in notice_text
        assert "personal information" in notice_text
        assert "repo-relative paths" in notice_text

        labels = {_attributes(item).get("label") for item in body}
        assert required_labels.issubset(labels), f"{path} is missing shared fields"

        submission_checks = next(
            item
            for item in body
            if _attributes(item).get("label") == "Submission Checks"
        )
        options = _attributes(submission_checks).get("options")
        assert isinstance(options, list)
        typed_options = cast(list[object], options)
        assert len(typed_options) == 3

        option_labels: list[str] = []
        for option in typed_options:
            assert isinstance(option, Mapping)
            label = cast(Mapping[object, object], option).get("label")
            assert isinstance(label, str)
            option_labels.append(label)

        assert any("searched for an existing issue" in label for label in option_labels)
        assert any("repo-scoped engineering work" in label for label in option_labels)
        assert any(
            "contains no personal information" in label for label in option_labels
        )


def test_issue_forms_do_not_collect_personal_contact_details() -> None:
    forbidden_needles = ("contact details", "email", "e-mail")

    for path in _template_files():
        _body_items(_load_yaml(path), path=path)
        lowered = path.read_text(encoding="utf-8").lower()
        for needle in forbidden_needles:
            assert needle not in lowered, f"{path} should not request {needle}"


def test_issue_forms_apply_expected_template_specific_defaults() -> None:
    bug = _load_yaml(_template_dir() / "01-bug.yml")
    workflow = _load_yaml(_template_dir() / "02-workflow-gap.yml")
    ops = _load_yaml(_template_dir() / "03-ops-follow-up.yml")

    assert bug["title"] == "[Bug]: "
    assert bug["labels"] == ["bug"]
    assert workflow["title"] == "[Workflow]: "
    assert workflow["labels"] == ["enhancement"]
    assert ops["title"] == "[Ops]: "
    assert "labels" not in ops
