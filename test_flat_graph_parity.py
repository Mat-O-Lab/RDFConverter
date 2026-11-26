"""JSON-LD and Turtle input describe the same RDF graph; one mapping, written against the flat
'@graph', must see the same nodes in both. Existing nested JSON-LD structure stays untouched."""
import json

from jsonpath_ng.ext import parse as jsonpath_parse

from app import process_data_to_jsonld

TURTLE = """\
@prefix ex: <http://example.org/data/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
ex:col-a a ex:Thing ; rdfs:label "Width" .
ex:col-b a ex:Thing ; rdfs:label "Height" .
"""

JSONLD = {
    "@context": {"ex": "http://example.org/data/", "label": "http://www.w3.org/2000/01/rdf-schema#label"},
    "things": [
        {"@id": "ex:col-a", "@type": "ex:Thing", "label": "Width"},
        {"@id": "ex:col-b", "@type": "ex:Thing", "label": "Height"},
    ],
}
# not JSON-LD to rdflib unless 'things' maps to a property; give it one
JSONLD["@context"]["things"] = "http://example.org/data/things"


def labels(processed):
    doc = json.loads(processed)
    nodes = [m.value for m in jsonpath_parse("$['@graph'][*]").find(doc)]
    return sorted(v for n in nodes for v in ([n["label"]] if isinstance(n.get("label"), str) else []))


def test_same_rule_sees_same_nodes_in_turtle_and_jsonld():
    ttl, _, _ = process_data_to_jsonld(TURTLE.encode(), "http://example.org/x.ttl")
    jld, _, _ = process_data_to_jsonld(json.dumps(JSONLD).encode(), "http://example.org/x.jsonld")
    assert labels(ttl) == labels(jld) == ["Height", "Width"]


def test_jsonld_keeps_original_structure():
    jld, is_rdf, _ = process_data_to_jsonld(json.dumps(JSONLD).encode(), "http://example.org/x.jsonld")
    doc = json.loads(jld)
    assert [t["label"] for t in doc["things"]] == ["Width", "Height"]
    assert is_rdf is False  # data is not copied into the output graph


def test_jsonld_without_context_is_untouched():
    plain = json.dumps({"a": [1, 2]})
    out, _, _ = process_data_to_jsonld(plain.encode(), "http://example.org/x.json")
    assert json.loads(out) == {"a": [1, 2]}
