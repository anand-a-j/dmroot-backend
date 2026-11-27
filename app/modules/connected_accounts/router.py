from uuid import UUID

from fastapi import APIRouter

from app.core.responses import success_response
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.connected_accounts import service
from app.modules.connected_accounts.schema import ConnectedAccountResponse

router = APIRouter(
    prefix="/connected-accounts",
    tags=["connected-accounts"],
)


@router.get("/{account_id}", response_model=ConnectedAccountResponse)
async def get_connected_account(
    account_id: UUID,
    current_user: CurrentUserDep,
):
    result = await service.get_account(
        account_id=account_id,
        org_id=current_user.org_id,
    )

    return success_response(
        data=result.model_dump(mode="json"),
    )


@router.post("/{account_id}/disconnect")
async def disconnect_connected_account(
    account_id: UUID,
    current_user: CurrentUserDep,
):
    result = await service.disconnect_account(
        org_id=current_user.org_id,
        account_id=account_id,
    )

    return success_response(
        data=result.model_dump(mode="json"),
        message="Account disconnected successfully",
    )
