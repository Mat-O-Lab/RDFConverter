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
