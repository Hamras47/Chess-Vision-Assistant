import logging
from app.core.logging_setup import APP_LOG_PATH,CRASH_LOG_PATH,configure,install_exception_hook

def test_configure_creates_project_app_log_and_console(monkeypatch):
    monkeypatch.delenv('CHESS_VISION_LOG_LEVEL',raising=False)
    path=configure()
    assert path==APP_LOG_PATH and APP_LOG_PATH.exists()
    assert any(getattr(handler,'_chess_vision_console',False) for handler in logging.getLogger().handlers)

def test_debug_environment_level_and_crash_handler(monkeypatch):
    monkeypatch.setenv('CHESS_VISION_LOG_LEVEL','DEBUG')
    configure(); install_exception_hook(lambda:{'safe':'context'})
    assert logging.getLogger().level==logging.DEBUG and CRASH_LOG_PATH.exists()
