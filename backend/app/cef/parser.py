from __future__ import annotations

import re

from app.cef.models import CefEvent


class CefParseError(ValueError):
    pass


_CEF_MARKER = "CEF:"

_EXT_KEY = re.compile(r"(?:^|\s)([A-Za-z0-9_.\-]+)=")

_HEADER_FIELDS = (
    "cef_version",
    "device_vendor",
    "device_product",
    "device_version",
    "signature_id",
    "name",
    "severity",
)


def _split_header_fields(body: str, maxsplit: int) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    i, n = 0, len(body)
    while i < n:
        ch = body[i]
        if ch == "\\" and i + 1 < n:
            current.append(ch)
            current.append(body[i + 1])
            i += 2
            continue
        if ch == "|" and len(parts) < maxsplit:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current))
    return parts


def _unescape_header(value: str) -> str:
    return value.replace("\\|", "|").replace("\\\\", "\\")


_EXT_ESCAPES = {"\\": "\\", "=": "=", "n": "\n", "r": "\r"}


def _unescape_extension_value(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append(_EXT_ESCAPES.get(nxt, "\\" + nxt))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _parse_extensions(extension: str) -> dict[str, str]:
    matches = list(_EXT_KEY.finditer(extension))
    result: dict[str, str] = {}
    for idx, match in enumerate(matches):
        key = match.group(1)
        value_start = match.end()
        value_end = (
            matches[idx + 1].start() if idx + 1 < len(matches) else len(extension)
        )
        raw_value = extension[value_start:value_end]
        result[key] = _unescape_extension_value(raw_value.strip())
    return result


def parse_cef(data: str) -> CefEvent:
    marker_at = data.find(_CEF_MARKER)
    if marker_at == -1:
        raise CefParseError("no 'CEF:' marker found")

    syslog_prefix = data[:marker_at].strip() or None
    body = data[marker_at + len(_CEF_MARKER) :]

    parts = _split_header_fields(body, maxsplit=7)
    if len(parts) < 7:
        raise CefParseError(
            f"malformed CEF header: expected 7 fields, got {len(parts)}"
        )

    header_values = [_unescape_header(p) for p in parts[:7]]
    extension_str = parts[7] if len(parts) == 8 else ""

    fields = dict(zip(_HEADER_FIELDS, header_values, strict=True))
    return CefEvent(
        raw=data,
        syslog_prefix=syslog_prefix,
        extensions=_parse_extensions(extension_str),
        **fields,
    )
