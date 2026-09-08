import logging
from threading import Event

import numpy as np

from app.core import logging_setup
from app.ai.board_recognizer import RecognitionWorker


def test_formatter_redacts_secrets_in_tracebacks(monkeypatch):
    key = 'sk-' + 'a' * 40
    monkeypatch.setenv('OPENAI_API_KEY', key)
    try:
        raise ValueError('authentication failed ' + key)
    except ValueError:
        import sys
        record = logging.LogRecord('test', logging.ERROR, '', 0, 'request failed', (), sys.exc_info())
    output = logging_setup.SecretSafeFormatter().format(record)
    assert key not in output
    assert 'ValueError' in output and '[REDACTED]' in output


def test_api_error_never_echoes_response_secret(caplog):
    from app.ai.openai_client import OpenAIClient, AIError
    import pytest
    marker = 'private-credential-marker'
    class Responses:
        def create(self, **kwargs):
            raise RuntimeError(marker)
    class Client:
        responses = Responses()
    client = OpenAIClient(client=Client(), api_key='test-key')
    with caplog.at_level(logging.ERROR), pytest.raises(AIError) as error:
        client.recognize(b'png', {}, 'test')
    assert marker not in caplog.text
    assert marker not in str(error.value)
    assert error.value.__suppress_context__


def test_unwritable_log_directory_falls_back(tmp_path, monkeypatch):
    blocked = tmp_path / 'blocked'
    blocked.write_text('not a directory')
    monkeypatch.setattr(logging_setup, 'LOG_DIRECTORY', blocked)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'user'))
    for name in ('app.log', 'crash.log'):
        handler = logging_setup._file_handler(name)
        try:
            handler.emit(logging.LogRecord('test', logging.ERROR, '', 0, 'diagnostic', (), None))
            assert (tmp_path / 'user' / 'ChessVision' / 'logs' / name).read_text().strip() == 'diagnostic'
        finally:
            handler.close()


def test_scan_cancellation_does_not_wait_for_network_or_retry():
    started, release, completed = Event(), Event(), Event()
    calls = []
    class Client:
        def recognize(self, *args):
            calls.append(1)
            started.set()
            release.wait(5)
            completed.set()
            raise RuntimeError('mock network timeout')
    worker = RecognitionWorker(np.zeros((8,8,3), dtype=np.uint8), 'mock', client=Client())
    worker.start()
    try:
        assert started.wait(2)
        worker.requestInterruption()
        assert worker.wait(1000), 'Qt worker must stop before network request returns'
        assert not completed.is_set()
    finally:
        release.set()
        worker.requestInterruption()
        worker.wait(2000)
    assert completed.wait(2)
    assert len(calls) == 1
