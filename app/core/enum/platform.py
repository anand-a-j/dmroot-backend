from enum import StrEnum


class Platform(StrEnum):
    INSTAGRAM = "instagram"

class PlatformAccountStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DISCONNECTED = "disconnected"