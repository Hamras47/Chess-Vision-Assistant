import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QLineEdit

from app.ai.openai_client import OpenAIClient
from app.core.credentials import CredentialStore, resolve_openai_key
from app.core.resources import resource_path
from app.ui.settings import SettingsDialog, mask_api_key


class MemoryStore:
    def __init__(self, value=""):
        self.value = value

    def get_openai_key(self):
        return self.value

    def set_openai_key(self, value):
        self.value = value

    def delete_openai_key(self):
        self.value = ""


@pytest.fixture(scope="module")
def app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_credential_store_round_trip_without_plaintext_settings(monkeypatch):
    values = {}
    fake = type("Keyring", (), {
        "get_password": staticmethod(lambda service, account: values.get((service, account))),
        "set_password": staticmethod(lambda service, account, value: values.__setitem__((service, account), value)),
        "delete_password": staticmethod(lambda service, account: values.pop((service, account), None)),
    })
    monkeypatch.setattr(CredentialStore, "_keyring", staticmethod(lambda: fake))
    store = CredentialStore()
    store.set_openai_key("test-secret")
    assert store.get_openai_key() == "test-secret"
    store.delete_openai_key()
    assert store.get_openai_key() == ""


def test_key_precedence_and_no_key_behavior(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    assert resolve_openai_key(MemoryStore("stored-key"))[0:2] == ("stored-key", "credential_store")
    assert resolve_openai_key(MemoryStore(""))[0:2] == ("environment-key", "environment")
    monkeypatch.delenv("OPENAI_API_KEY")
    client = OpenAIClient(credential_store=MemoryStore())
    assert not client.ready()


def test_api_key_masking_never_displays_full_value():
    masked = mask_api_key("key-example-secret-1234")
    assert masked.startswith("key") and masked.endswith("1234")
    assert "example-secret" not in masked


def test_settings_save_retrieve_and_stockfish_path(app, tmp_path):
    store = MemoryStore()
    engine = tmp_path / "stockfish.exe"
    engine.touch()
    dialog = SettingsDialog("gpt-5.6-luna", str(engine), 600, credential_store=store)
    dialog.api_key.setText("user-owned-key")
    dialog._save()
    assert store.value == "user-owned-key"
    assert dialog.values()[1] == str(engine)
    assert dialog.api_key.echoMode() == QLineEdit.Password


def test_packaging_safe_resource_paths_exist():
    assert resource_path("assets", "pieces", "white_king.svg").is_file()
    assert resource_path("assets", "icons", "chess-vision.ico").is_file()
