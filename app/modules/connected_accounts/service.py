import logging
from typing import Any
from uuid import UUID

from app.core.database import get_pool, transaction
from app.core.enum.platform import PlatformAccountStatus
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.modules.connected_accounts import repository
from app.modules.connected_accounts.policies import validate_transition
from app.modules.connected_accounts.schema import ConnectedAccountResponse

logger = logging.getLogger(__name__)

Account = dict[str, Any]


async def get_account(
    org_id: UUID | None,
    account_id: UUID,
) -> ConnectedAccountResponse:

    if org_id is None:
        raise ForbiddenException("You are not associated with an organization")

    db = get_pool()

    account = await repository.get_by_id(
        db,
        org_id=org_id,
        account_id=account_id,
    )

    if account is None:
        raise NotFoundException("Connected account not found")

    return account


async def disconnect_account(
    org_id: UUID | None,
    account_id: UUID,
) -> ConnectedAccountResponse:
    """Disconnect account and remove its stored token."""

    if org_id is None:
        raise ForbiddenException("You are not associated with an organization")

    async with transaction() as conn:
        account = await repository.lock_by_id(
            conn,
            org_id=org_id,
            account_id=account_id,
        )

        if account is None:
            raise NotFoundException("Connected account not found")

        current_status = PlatformAccountStatus(account.status)

        if current_status == PlatformAccountStatus.DISCONNECTED:
            return account

        validate_transition(
            current_status,
            PlatformAccountStatus.DISCONNECTED,
        )

        updated = await repository.mark_disconnected(
            conn,
            org_id=org_id,
            account_id=account_id,
        )

        if updated is None:
            raise ConflictException("Account could not be disconnected")

        return updated


async def mark_expired(
    org_id: UUID,
    account_id: UUID,
) -> bool:
    """INTERNAL (workers). active -> expired."""

    async with transaction() as conn:
        account = await repository.lock_by_id(
            conn,
            org_id=org_id,
            account_id=account_id,
        )

        if account is None or account.status != PlatformAccountStatus.ACTIVE.value:
            return False

        current_status = PlatformAccountStatus(account.status)

        validate_transition(
            current_status,
            PlatformAccountStatus.EXPIRED,
        )

        updated = await repository.mark_expired(
            conn,
            org_id=org_id,
            account_id=account_id,
        )

        return updated is not None
