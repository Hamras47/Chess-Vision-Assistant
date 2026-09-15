"""Tests must neither read nor overwrite the user's saved settings/credentials."""
import os
import pytest
from PySide6.QtCore import QSettings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolated_preferences(monkeypatch, tmp_path):
    from app.core.credentials import CredentialStore
    from app.ui import main_window
    values = {}
    backend = type("MemoryKeyring", (), {
        "get_password": staticmethod(lambda service, account: values.get((service, account))),
        "set_password": staticmethod(lambda service, account, value: values.__setitem__((service, account), value)),
        "delete_password": staticmethod(lambda service, account: values.pop((service, account), None)),
    })
    monkeypatch.setattr(CredentialStore, "_keyring", staticmethod(lambda: backend))
    monkeypatch.setattr(main_window, "QSettings", lambda *args: QSettings(str(tmp_path / "preferences.ini"), QSettings.IniFormat))
