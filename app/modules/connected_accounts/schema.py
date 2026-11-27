from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enum.platform import Platform, PlatformAccountStatus


class ConnectedAccountResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    platform: Platform
    platform_account_id: str
    account_name: str | None
    username: str | None
    status: PlatformAccountStatus
    token_expires_at: datetime | None
    connected_by_user_id: UUID | None
    disconnected_at: datetime | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
