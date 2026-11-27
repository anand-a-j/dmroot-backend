from enum import StrEnum


class UserRole(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    ADMIN = "admin"
    MEMBER = "member"