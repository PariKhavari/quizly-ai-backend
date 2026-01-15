from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, LoginSerializer
from ..services import build_jwt_tokens_for_user, set_auth_cookies,clear_auth_cookies, blacklist_refresh_token,refresh_access_token
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings



class RegisterView(APIView):
    """
    Registers a new user.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"detail": "User created successfully!"},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    Logs in the user and sets auth cookies:
    - access_token
    - refresh_token
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        user = authenticate(request=request, username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        tokens = build_jwt_tokens_for_user(user)

        response = Response(
            {
                "detail": "Login successfully!",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
            },
            status=status.HTTP_200_OK,
        )

        return set_auth_cookies(response, tokens["access"], tokens["refresh"])


class LogoutView(APIView):
    """
    Logs the user out by:
    - blacklisting the refresh token (making it invalid)
    - deleting access_token and refresh_token cookies

    """

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            blacklist_refresh_token(refresh_token)
        except TokenError:
            pass

        response = Response(
            {
                "detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."
            },
            status=status.HTTP_200_OK,
        )
        return clear_auth_cookies(response)


class TokenRefreshView(APIView):
    """POST /api/token/refresh/ - Refresh access token using refresh_token cookie."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"detail": "Refresh token missing."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            new_access = refresh_access_token(refresh_token)
        except TokenError:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response({"detail": "Token refreshed", "access": new_access}, status=status.HTTP_200_OK)
        
        response.set_cookie(
            key=settings.JWT_ACCESS_COOKIE_NAME,
            value=new_access,
            max_age=settings.JWT_ACCESS_COOKIE_MAX_AGE,
            httponly=settings.JWT_COOKIE_HTTPONLY,
            secure=settings.JWT_COOKIE_SECURE,
            samesite=settings.JWT_COOKIE_SAMESITE,
            path="/",
        )
        return response