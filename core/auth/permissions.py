from __future__ import annotations

from hmac import compare_digest

from rest_framework.permissions import BasePermission

from helpers.env import get_env


class HasAPIKey(BasePermission):
    message = "Invalid or missing API key."
    header_name = "X-API-Key"

    def has_permission(self, request, view):
        env_name = getattr(view, "required_api_key_env", None)
        if not env_name:
            return False

        expected_key = get_env(env_name)
        if not expected_key:
            return False

        header_name = getattr(view, "api_key_header_name", self.header_name)
        provided_key = request.headers.get(header_name, "").strip()

        return bool(provided_key) and compare_digest(provided_key, expected_key.strip())