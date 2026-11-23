"""open_file accepts inline data: URIs, so a mapping can be sent in the request itself
instead of being hosted at a static URL (e.g. /api/createrdfupload with a private mapping)."""
import base64

import pytest
from fastapi import HTTPException

from app import open_file


def test_base64_data_uri_returns_content():
    payload = "prefixes:\n  ex: http://example.org/\n"
    uri = "data:text/plain;base64," + base64.b64encode(payload.encode()).decode()
    data, filename = open_file(uri)
    assert data.decode() == payload
    assert filename


def test_plain_data_uri_returns_content():
    data, _ = open_file("data:text/plain,hello%20world")
    assert data == b"hello world"


def test_invalid_base64_data_uri_is_a_400():
    with pytest.raises(HTTPException) as exc:
        open_file("data:text/plain;base64,@@@not-base64@@@")
    assert exc.value.status_code == 400


def test_unknown_scheme_still_rejected():
    with pytest.raises(HTTPException) as exc:
        open_file("ftp://example.org/x")
    assert "unknown scheme" in exc.value.detail
