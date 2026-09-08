"""OS-backed credential storage for user-owned secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass

SERVICE_NAME = "ChessVision"
OPENAI_ACCOUNT = "openai-api-key"


class CredentialStoreError(RuntimeError):
    """Raised when the operating-system credential store is unavailable."""


@dataclass
class CredentialStore:
    """Store credentials through keyring (Windows Credential Manager on Windows)."""

    service_name: str = SERVICE_NAME

    @staticmethod
    def _keyring():
        try:
            import keyring
        except ImportError as exc:
            raise CredentialStoreError("Secure credential storage is unavailable.") from exc
        return keyring

    def get_openai_key(self) -> str:
        try:
            return (self._keyring().get_password(self.service_name, OPENAI_ACCOUNT) or "").strip()
        except Exception as exc:
            raise CredentialStoreError("Could not read the secure credential store.") from exc

    def set_openai_key(self, api_key: str) -> None:
        value = api_key.strip()
        if not value:
            self.delete_openai_key()
            return
        try:
            self._keyring().set_password(self.service_name, OPENAI_ACCOUNT, value)
        except Exception as exc:
            raise CredentialStoreError("Could not save to the secure credential store.") from exc

    def delete_openai_key(self) -> None:
        try:
            self._keyring().delete_password(self.service_name, OPENAI_ACCOUNT)
        except Exception as exc:
            # keyring raises when an entry does not exist; absence is already success.
            if exc.__class__.__name__ != "PasswordDeleteError":
                raise CredentialStoreError("Could not update the secure credential store.") from exc


def resolve_openai_key(store: CredentialStore | None = None, environment=None) -> tuple[str, str]:
    """Resolve keyring first, then OPENAI_API_KEY, without persisting environment keys."""
    credential_store = store or CredentialStore()
    env = os.environ if environment is None else environment
    try:
        stored = credential_store.get_openai_key()
    except CredentialStoreError:
        stored = ""
    if stored:
        return stored, "credential_store"
    environment_key = str(env.get("OPENAI_API_KEY", "")).strip()
    return (environment_key, "environment") if environment_key else ("", "none")
