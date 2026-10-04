import base64
import os
import pytest
from Deployment.cloud.server import (
    save_uploaded_file,
    get_uploaded_file,
    sanitize_filename,
    _FILE_REGISTRY,
    BROWSER_ALLOWED_METHODS,
)

def test_sanitize_filename():
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("data;malicious.csv") == "data_malicious.csv"
    assert sanitize_filename("my test script.py") == "my test script.py"
    assert sanitize_filename("") == "uploaded_file.bin"

def test_save_and_get_text_file():
    content = "col1,col2\n10,20\n30,40"
    meta = save_uploaded_file("metrics.csv", content, "text/csv")
    assert meta["fileId"].startswith("file-")
    assert meta["filename"] == "metrics.csv"
    assert meta["mimeType"] == "text/csv"
    assert meta["size"] == len(content.encode("utf-8"))
    assert meta["hasText"] is True
    assert "metrics.csv" in meta["downloadUrl"] or meta["fileId"] in meta["downloadUrl"]

    fetched_meta, fetched_bytes = get_uploaded_file(meta["fileId"])
    assert fetched_meta is not None
    assert fetched_bytes == content.encode("utf-8")

def test_save_and_get_base64_file():
    raw = b"\x89PNG\r\n\x1a\nfake-image-bytes"
    b64 = base64.b64encode(raw).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"

    meta = save_uploaded_file("icon.png", data_uri, "image/png")
    assert meta["filename"] == "icon.png"
    assert meta["mimeType"] == "image/png"
    assert meta["size"] == len(raw)

    fetched_meta, fetched_bytes = get_uploaded_file(meta["fileId"])
    assert fetched_meta is not None
    assert fetched_bytes == raw

def test_allowed_methods_include_files():
    assert "UploadFile" in BROWSER_ALLOWED_METHODS
    assert "DownloadFile" in BROWSER_ALLOWED_METHODS
    assert "ListFiles" in BROWSER_ALLOWED_METHODS
