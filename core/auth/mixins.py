from __future__ import annotations

from .permissions import HasAPIKey


class APIKeyProtectedViewSetMixin:
    protected_actions = frozenset()
    required_api_key_env = None
    api_key_header_name = "X-API-Key"

    def get_permissions(self):
        if self.action in self.protected_actions:
            return [HasAPIKey()]
        return super().get_permissions()