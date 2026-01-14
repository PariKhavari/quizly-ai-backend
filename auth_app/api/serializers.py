# auth_app/api/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    """
    Validates registration input and creates a new user.

    Expected request body:
    {
      "username": "your_username",
      "password": "your_password",
      "confirmed_password": "your_confirmed_password",
      "email": "your_email@example.com"
    }
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    confirmed_password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()

    def validate_username(self, value: str) -> str:
        # Enforce uniqueness case-insensitively
        username = value.strip()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Username is already taken.")
        return username

    def validate_email(self, value: str) -> str:
        # Enforce uniqueness case-insensitively
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Email is already in use.")
        return email

    def validate(self, attrs):
        # Ensure both password fields match
        password = attrs.get("password", "")
        confirmed_password = attrs.get("confirmed_password", "")
        if password != confirmed_password:
            raise serializers.ValidationError({"confirmed_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        # Create a Django user using the built-in user model
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
