from datetime import timedelta
from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken


def build_jwt_tokens_for_user(user) -> dict:
    """
    Create a new refresh/access token pair for a given user.

    Returns:
        dict: {"access": "<...>", "refresh": "<...>"}
    """
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    return {
        "access": str(access),
        "refresh": str(refresh),
    }


def set_auth_cookies(response: Response, access: str, refresh: str) -> Response:
    """
    Set HTTP-only cookies for access and refresh tokens on the response.
    Cookie names are aligned with the provided API documentation.
    """
    response.set_cookie(
        key=settings.JWT_ACCESS_COOKIE_NAME,
        value=access,
        max_age=settings.JWT_ACCESS_COOKIE_MAX_AGE,
        httponly=settings.JWT_COOKIE_HTTPONLY,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        key=settings.JWT_REFRESH_COOKIE_NAME,
        value=refresh,
        max_age=settings.JWT_REFRESH_COOKIE_MAX_AGE,
        httponly=settings.JWT_COOKIE_HTTPONLY,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )
    return response
