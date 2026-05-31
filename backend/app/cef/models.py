from __future__ import annotations

from pydantic import BaseModel, Field


HEADER_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "severity": "severity",
    "cef_version": "cef_version",
    "version": "cef_version",
    "device_vendor": "device_vendor",
    "devicevendor": "device_vendor",
    "device_product": "device_product",
    "deviceproduct": "device_product",
    "device_version": "device_version",
    "deviceversion": "device_version",
    "signature_id": "signature_id",
    "signatureid": "signature_id",
    "sig_id": "signature_id",
}


class CefEvent(BaseModel):
    raw: str = Field(description="Original decoded datagram text, verbatim")
    syslog_prefix: str | None = Field(
        default=None, description="Any syslog PRI/header text preceding 'CEF:'"
    )

    cef_version: str
    device_vendor: str
    device_product: str
    device_version: str
    signature_id: str
    name: str
    severity: str
    extensions: dict[str, str] = Field(default_factory=dict)

    def get_field(self, field: str) -> str | None:
        key = field.strip()
        attr = HEADER_FIELD_MAP.get(key.lower())
        if attr is not None:
            value = getattr(self, attr)
            return str(value) if value is not None else None
        if key in self.extensions:
            return self.extensions[key]
        lowered = key.lower()
        for ext_key, ext_val in self.extensions.items():
            if ext_key.lower() == lowered:
                return ext_val
        return None

    def as_flat_dict(self) -> dict[str, str]:
        flat: dict[str, str] = {
            "cef_version": self.cef_version,
            "device_vendor": self.device_vendor,
            "device_product": self.device_product,
            "device_version": self.device_version,
            "signature_id": self.signature_id,
            "name": self.name,
            "severity": self.severity,
        }
        flat.update(self.extensions)
        return flat
