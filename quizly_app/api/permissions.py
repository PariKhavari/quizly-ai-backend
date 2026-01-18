from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access only to the owner of the quiz object."""

    def has_object_permission(self, request, view, obj):
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)
