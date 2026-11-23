"""Unit tests for normalize_yarrrml_nested_lists."""

import glob
import os
import pytest
from yarrrml_utils import normalize_yarrrml_nested_lists


# ---------------------------------------------------------------------------
# Happy-path: two-element nested list converted to inline list
# ---------------------------------------------------------------------------

NESTED_TWO = """\
mappings:
  Person:
    s: ex:$(id)
    po:
      - - rdf:type
        - ex:Person
      - - foaf:name
        - $(name)
"""

INLINE_TWO = """\
mappings:
  Person:
    s: ex:$(id)
    po:
      - [rdf:type, ex:Person]
      - [foaf:name, $(name)]
"""


def test_two_element_nested_converted():
    assert normalize_yarrrml_nested_lists(NESTED_TWO) == INLINE_TWO


# ---------------------------------------------------------------------------
# Guard: three-element nested list must NOT be touched
# ---------------------------------------------------------------------------

NESTED_THREE = """\
mappings:
  Person:
    po:
      - - rdf:type
        - ex:Person
        - ex:Thing
"""


def test_three_element_nested_not_converted():
    result = normalize_yarrrml_nested_lists(NESTED_THREE)
    assert result == NESTED_THREE, (
        "Three-element nested list must be left unchanged; got:\n" + result
    )


# ---------------------------------------------------------------------------
# Already inline — must be idempotent
# ---------------------------------------------------------------------------

ALREADY_INLINE = """\
mappings:
  Person:
    po:
      - [rdf:type, ex:Person]
"""


def test_already_inline_unchanged():
    assert normalize_yarrrml_nested_lists(ALREADY_INLINE) == ALREADY_INLINE


# ---------------------------------------------------------------------------
# Windows line endings normalized before regex
# ---------------------------------------------------------------------------

def test_crlf_normalized():
    crlf = NESTED_TWO.replace('\n', '\r\n')
    result = normalize_yarrrml_nested_lists(crlf)
    assert result == INLINE_TWO


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_empty_string():
    assert normalize_yarrrml_nested_lists("") == ""


# ---------------------------------------------------------------------------
# Mixed: some nested, some already inline
# ---------------------------------------------------------------------------

MIXED = """\
mappings:
  A:
    po:
      - [rdf:type, ex:A]
      - - foaf:name
        - $(name)
"""

MIXED_NORMALIZED = """\
mappings:
  A:
    po:
      - [rdf:type, ex:A]
      - [foaf:name, $(name)]
"""


def test_mixed_input():
    assert normalize_yarrrml_nested_lists(MIXED) == MIXED_NORMALIZED


# ---------------------------------------------------------------------------
# Regression: examples/ YAML files contain no - - patterns to corrupt
# ---------------------------------------------------------------------------

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "examples")


@pytest.mark.parametrize("path", glob.glob(os.path.join(EXAMPLES_DIR, "*.yaml")))
def test_examples_idempotent(path):
    """Normalizing existing examples must not change them."""
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert normalize_yarrrml_nested_lists(content) == content, (
        f"{path} changed after normalization — check for unintended - - patterns"
    )
