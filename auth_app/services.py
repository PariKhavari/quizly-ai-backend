from __future__ import annotations
from typing import Dict
from django.conf import settings
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


def build_jwt_tokens_for_user(user) -> Dict[str, str]:
    """
    Create a new refresh/access token pair for the given user.
    Returns:
        dict: {"access": "<token>", "refresh": "<token>"}
    """
    refresh = RefreshToken.for_user(user)
    access = refresh.access_token

    return {
        "access": str(access),
        "refresh": str(refresh),
    }


def set_auth_cookies(response: Response, access: str, refresh: str) -> Response:
    """
    Set HTTP-only cookies for access and refresh tokens on the given response.
    Cookie names and behavior are aligned with the endpoint documentation:
    - access_token
    - refresh_token
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


def clear_auth_cookies(response: Response) -> Response:
    """
    Remove auth cookies from the client by deleting them.
    """
    response.delete_cookie(key=settings.JWT_ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.JWT_REFRESH_COOKIE_NAME, path="/")
    return response


def blacklist_refresh_token(refresh_token: str) -> None:
    """
    Blacklist the given refresh token so it cannot be used again.
    Raises:
        TokenError: If the token is invalid/expired.
    """
    token = RefreshToken(refresh_token)
    token.blacklist()
