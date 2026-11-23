"""Data bodies are typed by their content; the URL extension is only a hint.

Needed for /api/createrdfupload, where data arrives inline as data_content and
data_url is just a base identifier (often without a file extension).
"""
import json

import pytest
from fastapi import HTTPException

from app import looks_like_csv, process_data_to_jsonld, sniff_rdf_format, source_file_kind

TURTLE = '@prefix ex: <http://example.org/> .\nex:a ex:p "x" .\n'
RDFXML = (
    '<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" '
    'xmlns:ex="http://example.org/"><rdf:Description rdf:about="http://example.org/a">'
    "<ex:p>x</ex:p></rdf:Description></rdf:RDF>"
)
NO_EXT = "https://edc.example.com/api/v1/assets/urn:uuid:1234"


def test_turtle_detected_without_file_extension():
    assert sniff_rdf_format(TURTLE, NO_EXT) == "turtle"


def test_rdfxml_detected_without_file_extension():
    assert sniff_rdf_format(RDFXML, NO_EXT) == "xml"


def test_url_extension_hint_is_still_used():
    assert sniff_rdf_format(TURTLE, "http://example.org/data.ttl") == "turtle"


@pytest.mark.parametrize("text", ["id,label\n1,hello\n", "id;label\n1;hello\n", "id\tlabel\n1\thello\n"])
def test_csv_variants_detected(text):
    assert looks_like_csv(text)
    assert sniff_rdf_format(text, NO_EXT) is None  # CSV must not be mistaken for RDF
    assert source_file_kind(text, NO_EXT) == "csv"


@pytest.mark.parametrize("text", ["just some text", "single\ncolumn\nonly\n", "", "a,b\n1,2,3\n"])
def test_non_tables_are_not_csv(text):
    assert not looks_like_csv(text)


def test_json_is_json():
    assert source_file_kind(json.dumps({"a": 1}), NO_EXT) == "json"


def test_rdf_is_json_kind_because_it_is_converted_to_jsonld():
    assert source_file_kind(TURTLE, NO_EXT) == "json"


def test_process_json_unchanged():
    body = json.dumps({"a": 1})
    content, is_rdf, _ = process_data_to_jsonld(body.encode(), NO_EXT)
    assert (content, is_rdf) == (body, False)


def test_process_csv_passes_through_unchanged():
    content, is_rdf, _ = process_data_to_jsonld(b"id,label\n1,hello\n", NO_EXT)
    assert (content, is_rdf) == ("id,label\n1,hello\n", False)


def test_process_turtle_without_extension_is_converted():
    content, is_rdf, _ = process_data_to_jsonld(TURTLE.encode(), NO_EXT)
    assert is_rdf is True
    assert "example.org" in content


def test_process_garbage_is_still_rejected():
    with pytest.raises(HTTPException) as exc:
        process_data_to_jsonld(b"just some text, nothing structured", NO_EXT)
    assert exc.value.status_code == 422
