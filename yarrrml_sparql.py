"""Utilities for converting YARRRML mapping files to SPARQL SELECT queries."""

import re
import yaml
from typing import Optional

from yarrrml_utils import normalize_yarrrml_nested_lists


def _skip_po_entry(entry) -> bool:
    """Return True if a po entry should be excluded from SELECT columns.

    Args:
        entry: A single po entry (list [pred, obj] or dict with p/o keys).

    Returns:
        True if entry is a type triple, sub-object link, has no template,
        or uses ~iri annotation.
    """
    if isinstance(entry, dict):
        p = entry.get("p", "")
        o = entry.get("o", {})
        if isinstance(o, dict) and "mapping" in o:
            return True  # sub-object link, handled separately
        obj_str = str(o) if not isinstance(o, dict) else ""
    elif isinstance(entry, list) and len(entry) >= 2:
        p = str(entry[0])
        obj_str = str(entry[1])
    else:
        return True

    if p in ("a", "rdf:type"):
        return True
    if not re.search(r'\$\([^)]+\)', obj_str):
        return True
    if obj_str.rstrip().endswith("~iri"):
        return True
    return False


def _is_sub_object_link(entry) -> bool:
    """Return True if entry is a sub-object link (o: mapping: X)."""
    if isinstance(entry, dict):
        o = entry.get("o", {})
        return isinstance(o, dict) and "mapping" in o
    return False


def _expand_uri(qname: str, prefix_map: dict) -> str:
    """Expand a prefixed name or bare URI using prefix_map.

    Args:
        qname: A prefixed name like 'cx:wasteCode' or bare URI.
        prefix_map: Dict mapping alias -> full URI prefix.

    Returns:
        Fully expanded URI string.
    """
    if qname.startswith("<") and qname.endswith(">"):
        return qname[1:-1]
    if ":" in qname:
        parts = qname.split(":", 1)
        alias = parts[0]
        local = parts[1]
        if alias in prefix_map:
            return prefix_map[alias] + local
    return qname


def _derive_variable(template: str, used_names: set, mapping_name: str = "") -> str:
    """Extract a SPARQL variable name from a $(path.to.field) template.

    Args:
        template: Object template string containing $(…).
        used_names: Mutable set of already-used variable base names (updated in place).
        mapping_name: The mapping block name (used as namespace for collision tracking).

    Returns:
        A variable name string like '?fieldName' or '?parent_fieldName'.
    """
    m = re.search(r'\$\(([^)]+)\)', template)
    if not m:
        return "?unknown"
    path = m.group(1).lstrip(".")
    parts = [p for p in path.split(".") if p]
    if not parts:
        return "?unknown"

    leaf = parts[-1]
    if leaf not in used_names:
        used_names.add(leaf)
        return f"?{leaf}"

    # Try parent_leaf
    if len(parts) >= 2:
        extended = f"{parts[-2]}_{parts[-1]}"
        if extended not in used_names:
            used_names.add(extended)
            return f"?{extended}"

    # Full path
    full = "_".join(parts)
    if full not in used_names:
        used_names.add(full)
        return f"?{full}"
    # Use mapping name as disambiguator
    if mapping_name:
        candidate = f"{mapping_name}_{full}"
        if candidate not in used_names:
            used_names.add(candidate)
            return f"?{candidate}"
    # Numeric suffix fallback
    i = 2
    candidate = f"{full}_{i}"
    while candidate in used_names:
        i += 1
        candidate = f"{full}_{i}"
    used_names.add(candidate)
    return f"?{candidate}"


def _normalize_sources(sources_val) -> str:
    """Return the first source name as a string regardless of list/string input."""
    if isinstance(sources_val, list):
        return str(sources_val[0])
    return str(sources_val)


def _extract_subject_prefix(s_template: str, prefix_map: dict) -> str:
    """Extract the literal URI prefix before $(field) in a subject template.

    Args:
        s_template: Subject template like 'PrefixAlias:$(field)' or 'urn:edcar:...:$(field)'.
        prefix_map: Dict mapping alias -> full URI prefix.

    Returns:
        The expanded URI prefix string (everything before the first '$(' ).

    Raises:
        ValueError: If the extracted prefix is too generic (scheme-only).
    """
    idx = s_template.find("$(")
    prefix_part = s_template[:idx] if idx >= 0 else s_template

    # Expand QNAME alias (e.g. "PrefixAlias:local" -> "urn:...local")
    if ":" in prefix_part:
        alias, local = prefix_part.split(":", 1)
        if alias in prefix_map:
            expanded = prefix_map[alias] + local
        else:
            expanded = prefix_part
    else:
        expanded = prefix_part

    # Guard: reject scheme-only prefixes (only when template has a variable)
    if idx >= 0:
        scheme_only = re.match(r'^[a-zA-Z][a-zA-Z0-9+\-.]*:$', expanded)
        if scheme_only:
            raise ValueError(
                f"Subject template prefix too generic for scoping: '{expanded}' "
                "— use a prefix alias in the YARRRML prefixes: block"
            )
    return expanded


def _collect_all_field_paths(mappings: dict) -> set:
    """Collect all $(path) strings across all mappings for collision pre-analysis."""
    paths = set()
    for defn in mappings.values():
        for entry in (defn.get("po") or []):
            if isinstance(entry, list) and len(entry) >= 2:
                m = re.search(r'\$\(([^)]+)\)', str(entry[1]))
                if m:
                    paths.add(m.group(1).lstrip("."))
            elif isinstance(entry, dict) and not _is_sub_object_link(entry):
                obj = entry.get("o", "")
                m = re.search(r'\$\(([^)]+)\)', str(obj))
                if m:
                    paths.add(m.group(1).lstrip("."))
    return paths


def _build_json_field_expr(json_key: str, var: str) -> str:
    """Build SPARQL CONCAT fragment for one scalar field.

    Emits unquoted values for booleans and numeric strings, quoted otherwise.
    """
    bool_check = f"REGEX(STR({var}), '^(true|false)$')"
    num_check = f"REGEX(STR({var}), '^-?[0-9]+(\\\\.[0-9]+)?$')"
    value_expr = (
        f"IF({bool_check}, STR({var}), "
        f"IF({num_check}, STR({var}), CONCAT('\"', STR({var}), '\"')))"
    )
    return f"'\"{ json_key }\":', {value_expr}"


def _get_po_templates(defn: dict) -> set:
    """Collect all $(path) template strings from a mapping's scalar po entries."""
    templates = set()
    for entry in (defn.get("po") or []):
        if isinstance(entry, list) and len(entry) >= 2:
            m = re.search(r'\$\(([^)]+)\)', str(entry[1]))
            if m:
                templates.add(m.group(1).lstrip("."))
        elif isinstance(entry, dict) and not _is_sub_object_link(entry):
            m = re.search(r'\$\(([^)]+)\)', str(entry.get("o", "")))
            if m:
                templates.add(m.group(1).lstrip("."))
    return templates


def _build_where_block(
    mapping_name: str,
    subject_var: str,
    defn: dict,
    mappings: dict,
    prefix_map: dict,
    source_iterators: dict,
    child_names: set,
    is_root: bool,
    used_vars: set,
    indent: int = 2,
) -> tuple:
    """Build WHERE-clause triple patterns and SELECT column expressions for one mapping.

    Args:
        mapping_name: Name of this mapping block.
        subject_var: SPARQL variable for this block's subject, e.g. '?WasteCode_subject'.
        defn: The mapping definition dict.
        mappings: All mapping definitions (for recursive child resolution).
        prefix_map: Alias -> full URI dict.
        source_iterators: Source name -> iterator string.
        child_names: Set of mapping names that are children of some other mapping.
        is_root: True if this is the root mapping.
        used_vars: Mutable set of already-used variable names.
        indent: Current indentation level (spaces).

    Returns:
        Tuple (triple_lines: list[str], select_exprs: list[str])
        triple_lines are WHERE-clause lines; select_exprs are JSON field fragments.
    """
    pad = " " * indent
    triple_lines = []
    select_exprs = []
    has_condition = "condition" in defn

    po_entries = defn.get("po") or []

    for entry in po_entries:
        if _is_sub_object_link(entry):
            child_mapping_name = entry["o"]["mapping"]
            pred_uri = _expand_uri(entry.get("p", ""), prefix_map)
            child_var = f"?{child_mapping_name}_subject"
            child_defn = mappings.get(child_mapping_name)
            if child_defn is None:
                continue

            parent_source = _normalize_sources(defn.get("sources", "root"))
            child_source = _normalize_sources(child_defn.get("sources", "root"))
            child_iterator = source_iterators.get(child_source, "$")
            is_array = "[*]" in child_iterator and child_source != parent_source

            # Required link triple (never OPTIONAL)
            triple_lines.append(f"{pad}{subject_var} <{pred_uri}> {child_var} .")

            if not has_condition:
                # Recurse into child block, wrapped in OPTIONAL
                child_triples, child_exprs = _build_where_block(
                    child_mapping_name,
                    child_var,
                    child_defn,
                    mappings,
                    prefix_map,
                    source_iterators,
                    child_names,
                    is_root=False,
                    used_vars=used_vars,
                    indent=indent + 2,
                )

                if is_array:
                    # Array child: build GROUP_CONCAT expression
                    # json_key from predicate local name
                    pred_local = pred_uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
                    if child_exprs:
                        inner_concat = ", ', ', ".join(child_exprs)
                        child_json_frag = f"CONCAT('{{', {inner_concat}, '}}')"
                        gc_expr = f"GROUP_CONCAT(DISTINCT {child_json_frag}; SEPARATOR=', ')"
                        array_expr = f"'\"{ pred_local }\":[', {gc_expr}, ']'"
                        select_exprs.append(array_expr)

                    triple_lines.append(f"{pad}OPTIONAL {{")
                    triple_lines.extend(child_triples)
                    triple_lines.append(f"{pad}}}")
                else:
                    # Non-array sub-object: nest child fields under predicate local name
                    if child_exprs and not has_condition:
                        parent_templates = _get_po_templates(defn)
                        child_templates = _get_po_templates(child_defn)
                        is_ghost = bool(child_templates) and child_templates.issubset(parent_templates)
                        if not is_ghost:
                            inner_concat = ", ', ', ".join(child_exprs)
                            nested_concat = f"CONCAT('{{', {inner_concat}, '}}')"
                            pred_local_name = pred_uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
                            select_exprs.append(f"'\"{ pred_local_name }\":', {nested_concat}")
                    triple_lines.append(f"{pad}OPTIONAL {{")
                    triple_lines.extend(child_triples)
                    triple_lines.append(f"{pad}}}")

        elif not _skip_po_entry(entry) and not has_condition:
            # Scalar predicate/object
            if isinstance(entry, list):
                pred_str = str(entry[0])
                obj_str = str(entry[1])
            else:
                pred_str = str(entry.get("p", ""))
                obj_str = str(entry.get("o", ""))

            pred_uri = _expand_uri(pred_str, prefix_map)
            var = _derive_variable(obj_str, used_vars, mapping_name)

            triple_lines.append(f"{pad}{subject_var} <{pred_uri}> {var} .")

            # JSON key: use local name of predicate
            pred_local = pred_uri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            json_key = pred_local
            # Also grab the field name from template for a more faithful key
            m = re.search(r'\$\(([^)]+)\)', obj_str)
            if m:
                field_path = m.group(1).lstrip(".")
                json_key = field_path.split(".")[-1]

            select_exprs.append(_build_json_field_expr(json_key, var))

    return triple_lines, select_exprs


def yarrrml_to_sparql(mapping_yaml: str) -> str:
    """Convert a YARRRML mapping YAML string to a SPARQL SELECT query.

    The generated query returns a single ?json column. When executed against
    the RDF graph produced by the same mapping, each result row contains a
    JSON object reconstructing the original source record.

    Arrays (Pattern C: separate iterator source) are emitted as GROUP_CONCAT
    inside JSON arrays. Sub-objects (Pattern B: shared root source) are
    inlined into the flat JSON object. Scalar fields (Pattern A) map directly.

    Only the first root mapping is used when multiple roots exist; a SPARQL
    comment identifies any skipped root mappings (known limitation).

    Args:
        mapping_yaml: A YARRRML mapping file as a YAML string.

    Returns:
        A SPARQL 1.1 SELECT query string.

    Raises:
        ValueError: If the input is not valid YAML, contains no mappings,
            or has a subject template prefix too generic for scoping.
    """
    # R6: normalize nested-list po: blocks first
    mapping_yaml = normalize_yarrrml_nested_lists(mapping_yaml)

    try:
        doc = yaml.safe_load(mapping_yaml)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc

    if not isinstance(doc, dict):
        raise ValueError("No mappings found in YARRRML document")

    prefixes = doc.get("prefixes") or {}
    sources_block = doc.get("sources") or {}
    mappings = doc.get("mappings") or {}

    if not mappings:
        raise ValueError("No mappings found in YARRRML document")

    # Build prefix_map: alias -> full URI
    prefix_map: dict = {}
    for alias, uri in prefixes.items():
        prefix_map[str(alias)] = str(uri)

    # Build source_iterators: source_name -> iterator string
    source_iterators: dict = {}
    comments = []
    if not sources_block:
        comments.append("# WARNING: no top-level sources block; all sources treated as root-level")
    else:
        for src_name, src_defn in sources_block.items():
            if isinstance(src_defn, dict):
                source_iterators[str(src_name)] = src_defn.get("iterator", "$")
            else:
                source_iterators[str(src_name)] = "$"

    # Pass 1: classify mappings into root vs child
    child_names: set = set()
    for defn in mappings.values():
        for entry in (defn.get("po") or []):
            if _is_sub_object_link(entry):
                child_names.add(entry["o"]["mapping"])

    root_names = [name for name in mappings if name not in child_names]
    if not root_names:
        # Fallback: use first mapping
        root_names = [next(iter(mappings))]

    root_name = root_names[0]
    skipped_roots = root_names[1:]

    root_defn = mappings[root_name]
    root_s_template = root_defn.get("s", "")
    root_subject_var = f"?{root_name}_subject"

    # Derive subject URI prefix for FILTER (R9)
    root_subject_prefix = _extract_subject_prefix(root_s_template, prefix_map)

    # Pass 2: generate WHERE clause and SELECT expressions
    used_vars: set = set()
    where_lines, select_exprs = _build_where_block(
        root_name,
        root_subject_var,
        root_defn,
        mappings,
        prefix_map,
        source_iterators,
        child_names,
        is_root=True,
        used_vars=used_vars,
        indent=2,
    )

    # Build SELECT ?json via CONCAT of all field expressions
    lines = []

    # BASE
    base = doc.get("base")
    if base and base != "#":
        lines.append(f"BASE <{base}>")

    # PREFIX declarations (R3)
    for alias, uri in sorted(prefix_map.items()):
        lines.append(f"PREFIX {alias}: <{uri}>")
    lines.append("")

    # Comments
    for c in comments:
        lines.append(c)
    if skipped_roots:
        lines.append(f"# NOTE: additional root mappings skipped: {skipped_roots}")
    lines.append("")

    # SELECT
    if select_exprs:
        # Build JSON CONCAT: { "key": value, "key2": value2 }
        # Interleave commas
        concat_parts = []
        for i, expr in enumerate(select_exprs):
            if i == 0:
                concat_parts.append(f"'{{', {expr}")
            else:
                concat_parts.append(f"', ', {expr}")
        concat_parts.append("'}'")
        concat_str = ",\n      ".join(concat_parts)
        select_col = f"(CONCAT(\n      {concat_str}\n    ) AS ?json)"
    else:
        select_col = "?json"

    lines.append(f"SELECT {select_col}")
    lines.append("WHERE {")
    lines.append(f"  FILTER(STRSTARTS(STR({root_subject_var}), \"{root_subject_prefix}\"))")

    # Subject triple pattern (for root)
    root_type_uri = None
    for entry in (root_defn.get("po") or []):
        if isinstance(entry, list) and len(entry) >= 2 and str(entry[0]) in ("a", "rdf:type"):
            root_type_uri = _expand_uri(str(entry[1]), prefix_map)
            break

    if root_type_uri:
        lines.append(f"  {root_subject_var} a <{root_type_uri}> .")

    lines.extend(where_lines)
    lines.append("}")
    lines.append(f"GROUP BY {root_subject_var}")

    return "\n".join(lines)
