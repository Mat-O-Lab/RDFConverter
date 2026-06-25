"""Roundtrip test: yarrrml_to_sparql -> rdflib -> json.loads -> compare with sample JSON.

Run with pytest:
    pytest test_yarrrml_sparql_roundtrip.py -v

Run standalone:
    python3 test_yarrrml_sparql_roundtrip.py
"""

import json
import os
import pathlib
import sys

import pytest
import rdflib

from yarrrml_sparql import yarrrml_to_sparql

EDCAR_REPO = pathlib.Path(
    os.environ.get("EDCAR_REPO_PATH", "/home/hanke/edcar-sldt-semantic-models")
)
MAPPINGS_ROOT = EDCAR_REPO / "SAMM_to_Ontology_Mappings"

SKIP_MAPPINGS = {
    "MaterialDataLegacy",
    "SimulationParameter",  # empty sub-objects {} can't round-trip through RDF
}


def _sort_recursive(obj):
    """Recursively sort lists in obj; coerce numeric strings to int/float first."""
    if isinstance(obj, list):
        coerced = []
        for item in obj:
            item = _sort_recursive(item)
            coerced.append(item)
        def sort_key(x):
            if isinstance(x, (int, float)):
                return (0, x, "")
            if isinstance(x, str):
                try:
                    return (0, float(x), "")
                except ValueError:
                    pass
            return (1, 0, str(x))
        return sorted(coerced, key=sort_key)
    if isinstance(obj, dict):
        return {k: _sort_recursive(v) for k, v in obj.items()}
    # Coerce numeric and boolean strings
    if isinstance(obj, str):
        if obj == "true":
            return True
        if obj == "false":
            return False
        try:
            if "." in obj:
                return float(obj)
            return int(obj)
        except ValueError:
            pass
    return obj


def _find_mapping_folders():
    if not MAPPINGS_ROOT.exists():
        return []
    folders = []
    for folder in sorted(MAPPINGS_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        name = folder.name
        if name in SKIP_MAPPINGS:
            continue
        yaml_dir = folder / "JSON to SAMM RDF mapping"
        ttl_dir = folder / "SAMM RDF result"
        json_dir = folder / "Sample JSON data"
        if not yaml_dir.exists() or not ttl_dir.exists() or not json_dir.exists():
            continue
        yaml_files = list(yaml_dir.glob("*.json-to-samm.yaml"))
        ttl_files = list(ttl_dir.glob("*.samm.ttl"))
        json_files = list(json_dir.glob("*.sample.json"))
        if yaml_files and ttl_files and json_files:
            folders.append((name, yaml_files[0], ttl_files[0], json_files[0]))
    return folders


MAPPING_PARAMS = _find_mapping_folders()


def _run_roundtrip(mapping_name, yaml_path, ttl_path, json_path):
    yaml_str = yaml_path.read_text(encoding="utf-8")

    sparql_str = yarrrml_to_sparql(yaml_str)

    g = rdflib.Graph()
    g.parse(str(ttl_path), format="turtle")

    results = list(g.query(sparql_str))
    assert len(results) >= 1, f"{mapping_name}: query returned no rows"

    # Collect all ?json values and merge into one dict (handles multi-row root)
    all_json = []
    for row in results:
        json_val = str(row.json) if hasattr(row, "json") else str(row[0])
        parsed = json.loads(json_val)
        all_json.append(parsed)

    # If single row, compare directly; if multiple (shouldn't happen with GROUP BY), collect
    if len(all_json) == 1:
        actual = all_json[0]
    else:
        actual = all_json

    expected = json.loads(json_path.read_text(encoding="utf-8"))

    assert _sort_recursive(actual) == _sort_recursive(expected), (
        f"{mapping_name}: mismatch\nactual:   {actual}\nexpected: {expected}"
    )


@pytest.mark.skipif(
    not MAPPINGS_ROOT.exists(),
    reason="edcar-sldt-semantic-models repo not available"
)
@pytest.mark.parametrize(
    "mapping_name,yaml_path,ttl_path,json_path",
    MAPPING_PARAMS,
    ids=[p[0] for p in MAPPING_PARAMS],
)
def test_roundtrip(mapping_name, yaml_path, ttl_path, json_path):
    _run_roundtrip(mapping_name, yaml_path, ttl_path, json_path)


@pytest.mark.skipif(
    not MAPPINGS_ROOT.exists(),
    reason="edcar-sldt-semantic-models repo not available"
)
def test_scoping_isolation():
    """Two-mapping merged graph: WasteCode query returns only WasteCode subjects."""
    wc_dir = MAPPINGS_ROOT / "WasteCode"
    vi_dir = MAPPINGS_ROOT / "VehicleIdentification"
    wc_yaml = (wc_dir / "JSON to SAMM RDF mapping" / "WasteCode.json-to-samm.yaml")
    wc_ttl = (wc_dir / "SAMM RDF result" / "WasteCode.samm.ttl")
    vi_ttl = (vi_dir / "SAMM RDF result" / "VehicleIdentification.samm.ttl")
    if not (wc_yaml.exists() and wc_ttl.exists() and vi_ttl.exists()):
        pytest.skip("fixture files not available")

    sparql_str = yarrrml_to_sparql(wc_yaml.read_text())

    g = rdflib.Graph()
    g.parse(str(wc_ttl), format="turtle")
    g.parse(str(vi_ttl), format="turtle")

    results = list(g.query(sparql_str))
    # Should return exactly WasteCode subjects, not VehicleIdentification ones
    assert len(results) >= 1
    for row in results:
        json_val = str(row.json) if hasattr(row, "json") else str(row[0])
        parsed = json.loads(json_val)
        assert "wasteCode" in parsed or "globalAssetId" in parsed, (
            f"scoping: unexpected row from merged graph: {parsed}"
        )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if not MAPPINGS_ROOT.exists():
        print(f"SKIP: edcar repo not found at {MAPPINGS_ROOT}")
        sys.exit(0)

    params = _find_mapping_folders()
    ok = 0
    fail = 0
    errors = []
    for mapping_name, yaml_path, ttl_path, json_path in params:
        try:
            _run_roundtrip(mapping_name, yaml_path, ttl_path, json_path)
            print(f"ok  {mapping_name}")
            ok += 1
        except Exception as exc:
            print(f"FAIL {mapping_name}: {exc}")
            fail += 1
            errors.append((mapping_name, str(exc)))

    print(f"\nok={ok}/{ok + fail}")
    if errors:
        sys.exit(1)
