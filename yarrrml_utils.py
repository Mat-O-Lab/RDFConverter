"""Utilities for pre-processing YARRRML mapping files."""

import re


def normalize_yarrrml_nested_lists(yaml_str: str) -> str:
    """Convert YARRRML nested-list po: blocks to inline-list form.

    yarrrml-parser silently drops the two-line nested-list form:
        - - predicate
          - object
    This function converts it to the inline-list form that is accepted:
        - [predicate, object]

    Three-element (or longer) nested lists are left unchanged — the
    negative lookahead ensures only exactly two-element pairs are touched.
    Windows line endings are normalised before the regex runs.
    """
    yaml_str = yaml_str.replace('\r\n', '\n')
    return re.sub(
        r'^( +)- - (.+)\n\1  - (.+)$(?!\n\1  -)',
        lambda m: f"{m.group(1)}- [{m.group(2)}, {m.group(3)}]",
        yaml_str,
        flags=re.MULTILINE,
    )


_TRUE_STRINGS = frozenset({"true", "yes", "on", "1"})


def as_bool(value, default: bool = False) -> bool:
    """Interpret a YAML flag as a boolean.

    Mappings written by older MapToMethod versions carry flags as quoted strings
    (``use_template_rowwise: 'false'``). Python treats any non-empty string as true,
    so ``'false'`` would silently switch the feature on.
    """
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in _TRUE_STRINGS
    return bool(value)
