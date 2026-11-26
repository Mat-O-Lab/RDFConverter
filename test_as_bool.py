"""Unit tests for as_bool (use_template_rowwise may arrive as a quoted string)."""

import pytest
import yaml
from yarrrml_utils import as_bool


@pytest.mark.parametrize("value", [True, "true", "True", "TRUE", " true ", "yes", "on", "1", 1])
def test_truthy(value):
    assert as_bool(value) is True


@pytest.mark.parametrize("value", [False, "false", "False", "no", "off", "0", 0, "", None])
def test_falsy(value):
    assert as_bool(value) is False


def test_default_only_applies_to_none():
    assert as_bool(None, default=True) is True
    assert as_bool("false", default=True) is False


@pytest.mark.parametrize("text,expected", [
    ("use_template_rowwise: 'false'", False),
    ("use_template_rowwise: 'true'", True),
    ("use_template_rowwise: false", False),
    ("use_template_rowwise: true", True),
])
def test_yaml_roundtrip(text, expected):
    assert as_bool(yaml.safe_load(text)["use_template_rowwise"]) is expected
