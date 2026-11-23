"""Unit tests for yarrrml_sparql.yarrrml_to_sparql."""

import pytest
from rdflib.plugins.sparql import prepareQuery

from yarrrml_sparql import yarrrml_to_sparql

WASTECODE_YAML = """\
base: 'urn:edcar:sample:'
mappings:
  WasteCode:
    po:
    - [a, cx:WasteCode]
    - [cx:wasteCode, $(wasteCode)]
    - [ext1:globalAssetId, $(globalAssetId)]
    s: WasteCodeWasteCode:$(globalAssetId)
    sources: root
prefixes:
  WasteCodeWasteCode: urn:edcar:sample:WasteCode:WasteCode-
  cx: urn:samm:io.catenax.material_accounting:1.0.0#
  ext1: urn:samm:io.catenax.shared.industry_core.common:1.0.0#
  rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
  xsd: http://www.w3.org/2001/XMLSchema#
sources:
  root:
    access: ../Sample JSON data/WasteCode.sample.json
    iterator: $
    referenceFormulation: jsonpath
"""

COMPOSITION_YAML = """\
base: 'urn:edcar:sample:'
mappings:
  Composition:
    po:
    - [a, cx:Composition]
    - o:
        mapping: Materials
      p: cx:materials
    - [ext1:globalAssetId, $(globalAssetId)]
    s: CompositionComposition:$(materials.globalAssetId)
    sources: root
  Materials:
    po:
    - [a, cx:MaterialEntity]
    - [cx:materialWeight, $(materials.materialWeight)]
    - [ext1:globalAssetId, $(materials.globalAssetId)]
    s: CompositionMaterials:$(materials.globalAssetId)
    sources: root
prefixes:
  CompositionComposition: urn:edcar:sample:Composition:Composition-
  CompositionMaterials: urn:edcar:sample:Composition:Materials-
  cx: urn:samm:io.catenax.material_accounting:1.0.0#
  ext1: urn:samm:io.catenax.shared.industry_core.common:1.0.0#
  rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
  xsd: http://www.w3.org/2001/XMLSchema#
sources:
  root:
    access: ../Sample JSON data/Composition.sample.json
    iterator: $
    referenceFormulation: jsonpath
"""

RECYCLINGBATCH_YAML = """\
base: 'urn:edcar:sample:'
mappings:
  ChildProcessSteps:
    po:
    - [a, cx:ProcessStep]
    - [cx:startTimestamp, $(startTimestamp)]
    s: RecyclingBatchChildProcessSteps:$(startTimestamp)
    sources: childProcessSteps_items
  RecyclingBatch:
    po:
    - [a, cx:RecyclingBatch]
    - [cx:recyclingBatchId, $(recyclingBatchId)]
    - o:
        mapping: ChildProcessSteps
      p: cx:childProcessSteps
    - [ext2:globalAssetId, $(globalAssetId)]
    s: RecyclingBatchRecyclingBatch:$(globalAssetId)
    sources: root
prefixes:
  RecyclingBatchChildProcessSteps: urn:edcar:sample:RecyclingBatch:ChildProcessSteps-
  RecyclingBatchRecyclingBatch: urn:edcar:sample:RecyclingBatch:RecyclingBatch-
  cx: urn:samm:io.catenax.material_accounting:1.0.0#
  ext2: urn:samm:io.catenax.shared.industry_core.common:1.0.0#
  rdf: http://www.w3.org/1999/02/22-rdf-syntax-ns#
  xsd: http://www.w3.org/2001/XMLSchema#
sources:
  childProcessSteps_items:
    access: ../Sample JSON data/RecyclingBatch.sample.json
    iterator: $.childProcessSteps[*]
    referenceFormulation: jsonpath
  root:
    access: ../Sample JSON data/RecyclingBatch.sample.json
    iterator: $
    referenceFormulation: jsonpath
"""


def test_pattern_a_wastecode_select_vars():
    result = yarrrml_to_sparql(WASTECODE_YAML)
    assert "?wasteCode" in result
    assert "?globalAssetId" in result


def test_pattern_a_no_type_column():
    result = yarrrml_to_sparql(WASTECODE_YAML)
    # should not have rdf:type as a SELECT variable
    assert "?a " not in result
    # no column for the rdf:type triple
    assert '"a":' not in result


def test_pattern_a_prefix_lines():
    result = yarrrml_to_sparql(WASTECODE_YAML)
    assert "PREFIX cx:" in result
    assert "PREFIX ext1:" in result


def test_pattern_a_parseable():
    result = yarrrml_to_sparql(WASTECODE_YAML)
    prepareQuery(result)  # raises if invalid SPARQL


def test_pattern_b_composition_link_triple():
    result = yarrrml_to_sparql(COMPOSITION_YAML)
    # Required link triple (not OPTIONAL)
    assert "?Composition_subject" in result
    assert "?Materials_subject" in result
    # link triple must appear before OPTIONAL block
    lines = result.splitlines()
    link_idx = next(i for i, l in enumerate(lines) if "?Materials_subject" in l and "OPTIONAL" not in l)
    optional_idx = next(i for i, l in enumerate(lines) if "OPTIONAL" in l)
    assert link_idx < optional_idx


def test_pattern_b_material_weight_in_optional():
    result = yarrrml_to_sparql(COMPOSITION_YAML)
    lines = result.splitlines()
    optional_start = next(i for i, l in enumerate(lines) if l.strip() == "OPTIONAL {")
    optional_end = next(i for i, l in enumerate(lines[optional_start:]) if l.strip() == "}") + optional_start
    optional_block = "\n".join(lines[optional_start:optional_end + 1])
    assert "?materialWeight" in optional_block or "?materials_materialWeight" in optional_block


def test_pattern_b_parseable():
    result = yarrrml_to_sparql(COMPOSITION_YAML)
    prepareQuery(result)


def test_pattern_c_array_link_required():
    result = yarrrml_to_sparql(RECYCLINGBATCH_YAML)
    lines = result.splitlines()
    # Required link (not inside OPTIONAL block)
    required = [l for l in lines if "?ChildProcessSteps_subject" in l and "OPTIONAL" not in l]
    assert any("?RecyclingBatch_subject" in l for l in required)


def test_pattern_c_scalars_in_optional():
    result = yarrrml_to_sparql(RECYCLINGBATCH_YAML)
    assert "OPTIONAL" in result


def test_pattern_c_parseable():
    result = yarrrml_to_sparql(RECYCLINGBATCH_YAML)
    prepareQuery(result)


def test_missing_po_no_error():
    yaml_str = """\
mappings:
  Empty:
    s: MyPrefix:$(id)
    sources: root
prefixes:
  MyPrefix: 'urn:example:test:'
sources:
  root:
    access: data.json
    iterator: $
    referenceFormulation: jsonpath
"""
    result = yarrrml_to_sparql(yaml_str)
    assert "SELECT" in result


def test_a_predicate_skipped():
    result = yarrrml_to_sparql(WASTECODE_YAML)
    assert "rdf:type" not in result.split("WHERE")[0]


def test_iri_object_skipped():
    yaml_str = """\
mappings:
  Test:
    po:
    - [cx:foo, 'template:Bar~iri']
    - [cx:name, $(name)]
    s: TestPrefix:$(name)
    sources: root
prefixes:
  TestPrefix: 'urn:example:test:'
  cx: 'urn:example:cx#'
sources:
  root:
    access: data.json
    iterator: $
    referenceFormulation: jsonpath
"""
    result = yarrrml_to_sparql(yaml_str)
    assert "?foo" not in result
    assert "?name" in result


def test_bare_iri_object_skipped():
    yaml_str = """\
mappings:
  Test:
    po:
    - [cx:foo, 'urn:example:fixed-value']
    - [cx:name, $(name)]
    s: TestPrefix:$(name)
    sources: root
prefixes:
  TestPrefix: 'urn:example:test:'
  cx: 'urn:example:cx#'
sources:
  root:
    access: data.json
    iterator: $
    referenceFormulation: jsonpath
"""
    result = yarrrml_to_sparql(yaml_str)
    assert "?foo" not in result
    assert "?name" in result


def test_dotted_path_collision_resolution():
    yaml_str = """\
mappings:
  Root:
    po:
    - [a, cx:Root]
    - o:
        mapping: Child
      p: cx:child
    - [cx:globalAssetId, $(globalAssetId)]
    s: RootRoot:$(globalAssetId)
    sources: root
  Child:
    po:
    - [a, cx:Child]
    - [cx:globalAssetId, $(child.globalAssetId)]
    s: RootChild:$(child.globalAssetId)
    sources: root
prefixes:
  RootRoot: urn:example:root:Root-
  RootChild: urn:example:root:Child-
  cx: urn:example:cx#
sources:
  root:
    access: data.json
    iterator: $
    referenceFormulation: jsonpath
"""
    result = yarrrml_to_sparql(yaml_str)
    # Both globalAssetId fields must be distinguishable in SELECT
    assert result.count("?globalAssetId") + result.count("?child_globalAssetId") >= 2


def test_leading_dot_in_template():
    yaml_str = """\
mappings:
  Test:
    po:
    - [cx:date, $(.manufacturingInformation.date)]
    s: TestPrefix:$(.manufacturingInformation.date)
    sources: root
prefixes:
  TestPrefix: 'urn:example:test:'
  cx: 'urn:example:cx#'
sources:
  root:
    access: data.json
    iterator: $
    referenceFormulation: jsonpath
"""
    result = yarrrml_to_sparql(yaml_str)
    assert "?date" in result


def test_sources_as_string_vs_list():
    yaml_list = WASTECODE_YAML.replace("sources: root", "sources: [root]")
    r1 = yarrrml_to_sparql(WASTECODE_YAML)
    r2 = yarrrml_to_sparql(yaml_list)
    assert r1 == r2


def test_no_sources_block():
    yaml_str = """\
mappings:
  Test:
    po:
    - [cx:name, $(name)]
    s: TestPrefix:$(name)
    sources: root
prefixes:
  TestPrefix: 'urn:example:test:'
  cx: 'urn:example:cx#'
"""
    result = yarrrml_to_sparql(yaml_str)
    assert "WARNING" in result
    assert "?name" in result


def test_condition_mapping_subject_in_where_po_excluded():
    yaml_str = """\
mappings:
  Root:
    po:
    - [a, cx:Root]
    - [cx:name, $(name)]
    - o:
        mapping: Conditional
      p: cx:cond
    s: RootRoot:$(name)
    sources: root
  Conditional:
    condition:
      function: grel:string_startsWith
      parameters:
      - [grel:valueParameter, $(flag)]
      - [grel:valueParameter2, 'true']
    po:
    - [a, cx:Cond]
    - [cx:flag, $(flag)]
    s: RootCond:$(flag)
    sources: root
prefixes:
  RootRoot: urn:example:root:Root-
  RootCond: urn:example:root:Cond-
  cx: urn:example:cx#
sources:
  root:
    access: data.json
    iterator: $
    referenceFormulation: jsonpath
"""
    result = yarrrml_to_sparql(yaml_str)
    assert "?Conditional_subject" in result
    assert "?flag" not in result


def test_multiple_roots_first_only_with_comment():
    yaml_str = """\
mappings:
  Alpha:
    po:
    - [cx:name, $(name)]
    s: AlphaPrefix:$(name)
    sources: root
  Beta:
    po:
    - [cx:code, $(code)]
    s: BetaPrefix:$(code)
    sources: root
prefixes:
  AlphaPrefix: urn:example:alpha:Alpha-
  BetaPrefix: urn:example:beta:Beta-
  cx: urn:example:cx#
sources:
  root:
    access: data.json
    iterator: $
    referenceFormulation: jsonpath
"""
    result = yarrrml_to_sparql(yaml_str)
    assert "NOTE: additional root mappings skipped" in result
    # Only first root's subject var present in WHERE
    assert "?Alpha_subject" in result or "?Beta_subject" in result


def test_malformed_yaml_raises():
    with pytest.raises(ValueError, match="Invalid YAML"):
        yarrrml_to_sparql("key: [unclosed")


def test_empty_mappings_raises():
    with pytest.raises(ValueError, match="No mappings found"):
        yarrrml_to_sparql("mappings: {}")


def test_integration_wastecode_parseable():
    import pathlib
    yaml_path = pathlib.Path(
        "/home/hanke/edcar-sldt-semantic-models/SAMM_to_Ontology_Mappings/"
        "WasteCode/JSON to SAMM RDF mapping/WasteCode.json-to-samm.yaml"
    )
    if not yaml_path.exists():
        pytest.skip("edcar repo not available")
    result = yarrrml_to_sparql(yaml_path.read_text())
    prepareQuery(result)
    assert "PREFIX" in result
    assert "SELECT" in result


def test_integration_composition_parseable():
    import pathlib
    yaml_path = pathlib.Path(
        "/home/hanke/edcar-sldt-semantic-models/SAMM_to_Ontology_Mappings/"
        "Composition/JSON to SAMM RDF mapping/Composition.json-to-samm.yaml"
    )
    if not yaml_path.exists():
        pytest.skip("edcar repo not available")
    result = yarrrml_to_sparql(yaml_path.read_text())
    prepareQuery(result)


def test_integration_recyclingbatch_parseable():
    import pathlib
    yaml_path = pathlib.Path(
        "/home/hanke/edcar-sldt-semantic-models/SAMM_to_Ontology_Mappings/"
        "RecyclingBatch/JSON to SAMM RDF mapping/RecyclingBatch.json-to-samm.yaml"
    )
    if not yaml_path.exists():
        pytest.skip("edcar repo not available")
    result = yarrrml_to_sparql(yaml_path.read_text())
    prepareQuery(result)
