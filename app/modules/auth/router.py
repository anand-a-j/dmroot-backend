from fastapi import APIRouter, Depends, Request

from app.core.responses import success_response
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_active_user
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.users.schemas import CurrentUser, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
async def register(payload: RegisterRequest, request: Request) -> dict:
    result = await service.register(
        payload, user_agent=request.headers.get("user-agent")
    )
    return success_response(
        data=result.model_dump(mode="json"), message="Registration successful"
    )


@router.post("/login")
async def login(payload: LoginRequest, request: Request) -> dict:
    result = await service.login(payload, user_agent=request.headers.get("user-agent"))
    return success_response(
        data=result.model_dump(mode="json"), message="Login successful"
    )


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_active_user)) -> dict:
    # Re-validate as UserResponse so internal fields (org_status) are not returned
    data = UserResponse.model_validate(user.model_dump()).model_dump(mode="json")
    return success_response(data=data)
