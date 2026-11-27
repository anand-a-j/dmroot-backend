from app.core.enum.platform import PlatformAccountStatus
from app.core.exceptions import ConflictException

_TRANSITIONS: dict[PlatformAccountStatus, set[PlatformAccountStatus]] = {
    PlatformAccountStatus.ACTIVE: {
        PlatformAccountStatus.ACTIVE,
        PlatformAccountStatus.EXPIRED,
        PlatformAccountStatus.DISCONNECTED,
    },
    PlatformAccountStatus.EXPIRED: {
        PlatformAccountStatus.ACTIVE,
        PlatformAccountStatus.DISCONNECTED,
    },
    PlatformAccountStatus.DISCONNECTED: {
        PlatformAccountStatus.ACTIVE,
    },
}


def validate_transition(
    current: PlatformAccountStatus,
    new: PlatformAccountStatus,
    *,
    reconnect: bool = False,
) -> None:
    if new == PlatformAccountStatus.ACTIVE and not reconnect:
        raise ConflictException("Account can only be re-activated by reconnecting it")

    if new not in _TRANSITIONS.get(current, set()):
        raise ConflictException(
            f"Invalid account status change: {current.value} to {new.value}"
        )
