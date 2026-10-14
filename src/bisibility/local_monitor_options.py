"""Strict input selections for retained Local reads; these never launch measurements."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LocalMonitorReadOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    as_of: str | None = None

    @field_validator("as_of", check_fields=False)
    @classmethod
    def valid_instant(cls, value: str | None) -> str | None:
        if value is not None:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", value):
                raise ValueError("Local time must be an ISO UTC millisecond instant")
            at = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if at.timestamp() < 0 or at > datetime.now(timezone.utc):
                raise ValueError("Local time precedes the supported epoch")
        return value


class LocalMonitorHistoryOptions(LocalMonitorReadOptions):
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    cursor: str | None = Field(default=None, min_length=1, max_length=8000, strict=True)

    @field_validator("from_", "to")
    @classmethod
    def valid_window_instant(cls, value: str | None) -> str | None:
        return cls.valid_instant(value)

    @field_validator("cursor")
    @classmethod
    def server_cursor_length(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-16-le")) // 2 > 8000:
            raise ValueError("Local cursor exceeds 8000 UTF-16 units")
        return value

    @model_validator(mode="after")
    def ordered_window(self) -> LocalMonitorHistoryOptions:
        until = self.to or self.as_of
        if self.from_ is not None and until is not None and self.from_ > until:
            raise ValueError("Local history from exceeds the selected end")
        if self.to is not None and self.as_of is not None and self.to > self.as_of:
            raise ValueError("Local history to exceeds as_of")
        return self


class LocalMonitorExportOptions(LocalMonitorReadOptions):
    version: Literal["1"] = "1"
    format: Literal["json", "csv"] = "json"
