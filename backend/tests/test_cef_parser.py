from __future__ import annotations

import pytest

from app.cef.parser import CefParseError, parse_cef


def test_parses_minimal_header():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|Worm stopped|10|")
    assert event.cef_version == "0"
    assert event.device_vendor == "Acme"
    assert event.device_product == "Engine"
    assert event.device_version == "1.0"
    assert event.signature_id == "100"
    assert event.name == "Worm stopped"
    assert event.severity == "10"
    assert event.extensions == {}


def test_parses_extensions_with_spaces_in_values():
    raw = (
        "CEF:0|Acme|Engine|1.0|100|Bad thing|7|src=10.0.0.1 msg=hello world act=blocked"
    )
    event = parse_cef(raw)
    assert event.extensions["src"] == "10.0.0.1"
    assert event.extensions["msg"] == "hello world"
    assert event.extensions["act"] == "blocked"


def test_strips_syslog_prefix():
    raw = "<134>Sep 19 08:26:10 host CEF:0|Acme|Engine|1.0|100|Worm|10|eventid=5"
    event = parse_cef(raw)
    assert event.syslog_prefix is not None
    assert "host" in event.syslog_prefix
    assert event.name == "Worm"
    assert event.extensions["eventid"] == "5"


def test_header_pipe_escape():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|a\\|b|5|")
    assert event.name == "a|b"


def test_header_backslash_escape():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|path C\\\\x|5|")
    assert event.name == "path C\\x"


def test_extension_equals_escape():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|n|5|query=a\\=b key=v")
    assert event.extensions["query"] == "a=b"
    assert event.extensions["key"] == "v"


def test_extension_newline_escape():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|n|5|msg=line1\\nline2")
    assert event.extensions["msg"] == "line1\nline2"


def test_header_field_ending_in_escaped_backslash():
    event = parse_cef(r"CEF:0|A|E|1.0|100|C:\\Windows\\|7|dst=1.2.3.4")
    assert event.name == "C:\\Windows\\"
    assert event.severity == "7"
    assert event.extensions["dst"] == "1.2.3.4"


def test_extension_unknown_escape_preserves_backslash():
    event = parse_cef(r"CEF:0|A|E|1.0|100|n|5|user=domain\user path=C\temp")
    assert event.extensions["user"] == "domain\\user"
    assert event.extensions["path"] == "C\\temp"


def test_missing_marker_raises():
    with pytest.raises(CefParseError):
        parse_cef("just some random syslog line without the marker")


def test_too_few_header_fields_raises():
    with pytest.raises(CefParseError):
        parse_cef("CEF:0|Acme|Engine|only|three|")


def test_get_field_resolves_header_and_extension():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|Worm|9|filtertype=ids eventid=42")
    assert event.get_field("name") == "Worm"
    assert event.get_field("severity") == "9"
    assert event.get_field("filtertype") == "ids"
    assert event.get_field("eventid") == "42"
    assert event.get_field("nonexistent") is None


def test_get_field_is_case_insensitive():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|Worm|9|FilterType=ids")
    assert event.get_field("filtertype") == "ids"
    assert event.get_field("NAME") == "Worm"


def test_as_flat_dict_merges_header_and_extensions():
    event = parse_cef("CEF:0|Acme|Engine|1.0|100|Worm|9|eventid=42")
    flat = event.as_flat_dict()
    assert flat["name"] == "Worm"
    assert flat["eventid"] == "42"
