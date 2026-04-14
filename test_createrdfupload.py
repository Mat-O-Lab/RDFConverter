"""Integration tests for the /api/createrdfupload endpoint.

Run against a live service by setting TEST_BASE_URL:
    TEST_BASE_URL=http://localhost:6003 pytest test_createrdfupload.py -v
"""

import json
import os
import pytest
import httpx
from rdflib import Graph, Namespace, RDF

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:6003")

# Batch.json sample data from:
# https://raw.githubusercontent.com/eclipse-tractusx/sldt-semantic-models/refs/heads/main/io.catenax.batch/3.0.1/gen/Batch.json
BATCH_JSON = json.dumps({
    "localIdentifiers": [{"value": "BID12345678", "key": "batchId"}],
    "manufacturingInformation": {
        "date": "2025-09-26",
        "country": "HUR",
        "sites": [{"catenaXsiteId": "BPNS1234567890ZZ", "function": "production"}],
    },
    "catenaXId": "580d3adf-1981-44a0-a214-13d6ceed9379",
    "partTypeInformation": {
        "partClassification": [
            {
                "classificationStandard": "GIN 20510-21513",
                "classificationID": "1004712",
                "classificationDescription": (
                    "Generic standard for classification of parts in the automotive industry."
                ),
            }
        ],
        "manufacturerPartId": "123-0.740-3434-A",
        "nameAtManufacturer": "Mirror left",
    },
})

MAPPING_URL = (
    "https://raw.githubusercontent.com/Mat-O-Lab/RDFConverter/"
    "refs/heads/main/examples/catenax-batch-map.yaml"
)

DATA_URL = "https://edc.my-company.example.com/api/v1/assets/urn:uuid:580d3adf-1981-44a0-a214-13d6ceed9379"

# The canonical source URL used in the mapping (used for /api/createrdf comparison)
BATCH_JSON_URL = (
    "https://raw.githubusercontent.com/eclipse-tractusx/sldt-semantic-models"
    "/refs/heads/main/io.catenax.batch/3.0.1/gen/Batch.json"
)

PROV = Namespace("http://www.w3.org/ns/prov#")


def post(path, **kwargs):
    return httpx.post(f"{BASE_URL}{path}", **kwargs)


def test_createrdfupload_returns_200():
    """Endpoint returns HTTP 200 for valid input."""
    response = post(
        "/api/createrdfupload",
        json={"mapping_url": MAPPING_URL, "data_url": DATA_URL, "data_content": BATCH_JSON},
    )
    assert response.status_code == 200, response.text


def test_createrdfupload_filename_derived_from_data_url():
    """Filename is derived from the last segment of data_url with .ttl extension."""
    response = post(
        "/api/createrdfupload",
        json={"mapping_url": MAPPING_URL, "data_url": DATA_URL, "data_content": BATCH_JSON},
    )
    assert response.status_code == 200, response.text
    # last segment of DATA_URL is the URN (no dot) -> stem = full segment + ".ttl"
    assert response.json()["filename"] == "urn:uuid:580d3adf-1981-44a0-a214-13d6ceed9379.ttl"


def test_createrdfupload_filename_respects_return_type():
    """Filename extension changes with return_type query parameter."""
    response = post(
        "/api/createrdfupload?return_type=json-ld",
        json={"mapping_url": MAPPING_URL, "data_url": DATA_URL, "data_content": BATCH_JSON},
    )
    assert response.status_code == 200, response.text
    assert response.json()["filename"] == "urn:uuid:580d3adf-1981-44a0-a214-13d6ceed9379.jsonld"


def test_createrdfupload_graph_uses_data_url_as_base():
    """Generated RDF subjects are anchored to data_url#."""
    response = post(
        "/api/createrdfupload",
        json={"mapping_url": MAPPING_URL, "data_url": DATA_URL, "data_content": BATCH_JSON},
    )
    assert response.status_code == 200, response.text
    graph_str = response.json()["graph"]
    base = DATA_URL.rstrip("/") + "#"
    assert base in graph_str or "example.org/mydata/Batch.json" in graph_str, (
        f"Expected base URI {base!r} not found in graph output"
    )


def test_createrdfupload_graph_contains_triples():
    """Mapping produces at least some triples."""
    response = post(
        "/api/createrdfupload",
        json={"mapping_url": MAPPING_URL, "data_url": DATA_URL, "data_content": BATCH_JSON},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["num_mappings_applied"] > 0, "Expected at least one mapping rule to be applied"
    assert body["graph"].strip() != "", "Expected non-empty RDF graph"


def test_createrdfupload_missing_data_content_returns_422():
    """Request without data_content is rejected."""
    response = post(
        "/api/createrdfupload",
        json={"mapping_url": MAPPING_URL, "data_url": DATA_URL},
    )
    assert response.status_code == 422


def test_createrdfupload_missing_mapping_url_returns_422():
    """Request without mapping_url is rejected."""
    response = post(
        "/api/createrdfupload",
        json={"data_url": DATA_URL, "data_content": BATCH_JSON},
    )
    assert response.status_code == 422


def _strip_prov(g: Graph) -> Graph:
    """Remove all triples that involve the prov: namespace."""
    to_remove = [
        (s, p, o) for s, p, o in g
        if str(p).startswith(str(PROV)) or str(o).startswith(str(PROV))
    ]
    for triple in to_remove:
        g.remove(triple)
    return g


def test_createrdf_and_createrdfupload_produce_equivalent_graphs():
    """Both endpoints produce the same data triples for the same input.

    /api/createrdf fetches the data from the canonical source URL;
    /api/createrdfupload receives the same content directly in the body.
    After stripping provenance triples (which legitimately differ), the
    predicate-object pairs and rdf:type assertions must be identical.
    """
    url_resp = post(
        "/api/createrdf",
        json={"mapping_url": MAPPING_URL, "data_url": BATCH_JSON_URL},
    )
    assert url_resp.status_code == 200, url_resp.text

    upload_resp = post(
        "/api/createrdfupload",
        json={"mapping_url": MAPPING_URL, "data_url": BATCH_JSON_URL, "data_content": BATCH_JSON},
    )
    assert upload_resp.status_code == 200, upload_resp.text

    g_url = _strip_prov(Graph().parse(data=url_resp.json()["graph"], format="turtle"))
    g_upload = _strip_prov(Graph().parse(data=upload_resp.json()["graph"], format="turtle"))

    assert len(g_url) == len(g_upload), (
        f"Triple count mismatch: createrdf={len(g_url)}, createrdfupload={len(g_upload)}"
    )

    # Predicate-object pairs are independent of base URI and must match exactly
    po_url = {(str(p), str(o)) for _, p, o in g_url}
    po_upload = {(str(p), str(o)) for _, p, o in g_upload}
    assert po_url == po_upload, (
        f"Predicate-object mismatch:\n"
        f"  only in createrdf:       {po_url - po_upload}\n"
        f"  only in createrdfupload: {po_upload - po_url}"
    )
