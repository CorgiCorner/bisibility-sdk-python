"""Strict public identifier types shared by the client and response models.

Public identifiers are the only identifiers accepted at the HTTP boundary. Their
prefix makes the resource type explicit, while the 24-character CUID2 suffix
keeps identifiers URL-safe and opaque.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal, TypeAlias

from pydantic import Field

PublicIdPrefix: TypeAlias = Literal[
    "al",
    "alr",
    "audit",
    "check",
    "cmp",
    "conn",
    "dwh",
    "ferry",
    "imp",
    "inv",
    "key",
    "kw",
    "mbr",
    "ntf",
    "pat",
    "prj",
    "sid",
    "sig",
    "svkw",
    "tag",
    "usr",
    "viw",
    "we",
]

PUBLIC_ID_PREFIXES: frozenset[PublicIdPrefix] = frozenset(
    {
        "al",
        "alr",
        "audit",
        "check",
        "cmp",
        "conn",
        "dwh",
        "ferry",
        "imp",
        "inv",
        "key",
        "kw",
        "mbr",
        "ntf",
        "pat",
        "prj",
        "sid",
        "sig",
        "svkw",
        "tag",
        "usr",
        "viw",
        "we",
    }
)
PUBLIC_ID_SUFFIX_PATTERN = r"[a-z][a-z0-9]{23}"


def public_id_pattern(prefix: PublicIdPrefix) -> str:
    """Return the anchored strict-v3 pattern for one resource prefix."""
    return rf"^{prefix}_{PUBLIC_ID_SUFFIX_PATTERN}$"


def require_public_id(value: str, prefix: PublicIdPrefix, *, field: str = "id") -> str:
    """Validate one boundary identifier and return it unchanged.

    This intentionally has no raw-ID or legacy fallback. Callers get a local,
    deterministic error before an invalid value can reach the HTTP transport.
    """
    if not isinstance(value, str) or not re.fullmatch(public_id_pattern(prefix), value):
        raise ValueError(f"{field} must be a strict public {prefix}_ identifier.")
    return value


TriggeredAlertId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("al"))]
AlertRuleId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("alr"))]
AuditId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("audit"))]
CheckId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("check"))]
CompetitorId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("cmp"))]
ConnectionId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("conn"))]
DeployWebhookId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("dwh"))]
TransferTokenId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("ferry"))]
CloudImportId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("imp"))]
InviteId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("inv"))]
KeyId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("key"))]
KeywordId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("kw"))]
MemberId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("mbr"))]
NotificationId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("ntf"))]
PersonalAccessTokenId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("pat"))]
ProjectId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("prj"))]
SessionId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("sid"))]
SignalId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("sig"))]
SavedKeywordId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("svkw"))]
TagId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("tag"))]
UserId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("usr"))]
ViewId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("viw"))]
WebhookEndpointId: TypeAlias = Annotated[str, Field(pattern=public_id_pattern("we"))]
