"""
Admin configuration for auth_app.

We register (if enabled) the SimpleJWT blacklist models so you can inspect:
- issued refresh tokens (OutstandingToken)
- blacklisted refresh tokens (BlacklistedToken)

This directly supports:
POST /api/logout/  -> refresh token becomes invalid (blacklist)
"""

from django.contrib import admin

try:
    # These models exist only if
    # 'rest_framework_simplejwt.token_blacklist' is in INSTALLED_APPS.
    from rest_framework_simplejwt.token_blacklist.models import (  # type: ignore
        BlacklistedToken,
        OutstandingToken,
    )

    @admin.register(OutstandingToken)
    class OutstandingTokenAdmin(admin.ModelAdmin):
        """Admin view for issued tokens."""
        list_display = ("user", "jti", "created_at", "expires_at")
        search_fields = ("user__username", "jti")
        list_filter = ("created_at", "expires_at")

    @admin.register(BlacklistedToken)
    class BlacklistedTokenAdmin(admin.ModelAdmin):
        """Admin view for blacklisted tokens."""
        list_display = ("token", "blacklisted_at")
        search_fields = ("token__jti", "token__user__username")
        list_filter = ("blacklisted_at",)

except Exception:
    pass
