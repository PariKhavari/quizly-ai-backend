from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegisterSerializer, LoginSerializer
from django.contrib.auth import authenticate
from auth_app.services import build_jwt_tokens_for_user, set_auth_cookies


class RegisterView(APIView):
    """
    POST /api/register/

    Registers a new user.
    Success response (201):
      {"detail": "User created successfully!"}
    """

    # This endpoint must be publicly accessible
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
    POST /api/login/

    Logs the user in and sets auth cookies:
    - access_token
    - refresh_token

    Success response (200):
    {
      "detail": "Login successfully!",
      "user": {
        "id": 1,
        "username": "...",
        "email": "..."
      }
    }

    Error response (401):
      {"detail": "Invalid credentials."}
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
            # Keep error messages generic for security reasons
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
