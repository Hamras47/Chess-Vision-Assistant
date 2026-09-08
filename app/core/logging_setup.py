"""Project-rooted, low-noise diagnostic logging for the desktop application."""
import logging
import os
import sys
import traceback
import warnings
import tempfile
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if getattr(sys, "frozen", False):
    LOG_DIRECTORY = Path(os.getenv("LOCALAPPDATA", Path.home())) / "ChessVision" / "logs"
else:
    LOG_DIRECTORY = PROJECT_ROOT / 'logs'
APP_LOG_PATH = LOG_DIRECTORY / 'app.log'
CRASH_LOG_PATH = LOG_DIRECTORY / 'crash.log'
FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'

class SecretSafeFormatter(logging.Formatter):
    def format(self, record):
        rendered = super().format(record)
        rendered = re.sub(r'\bsk-[A-Za-z0-9_-]{12,}', '[REDACTED]', rendered)
        key = os.getenv('OPENAI_API_KEY', '')
        return rendered.replace(key, '[REDACTED]') if key else rendered

def _file_handler(filename):
    """Prefer project logs, then per-user logs when a checkout is read-only."""
    candidates = (LOG_DIRECTORY,
                  Path(os.getenv('LOCALAPPDATA', Path.home())) / 'ChessVision' / 'logs',
                  Path(tempfile.gettempdir()) / 'ChessVision' / 'logs')
    for directory in dict.fromkeys(candidates):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            return RotatingFileHandler(directory / filename, maxBytes=5*1024*1024,
                                       backupCount=3, encoding='utf-8')
        except OSError:
            continue
    logging.getLogger(__name__).warning('FILE_LOG_UNAVAILABLE file=%s; using console', filename)
    return logging.StreamHandler()

def _level(debug=False):
    configured=os.getenv('CHESS_VISION_LOG_LEVEL','').upper()
    return logging.DEBUG if debug or configured=='DEBUG' else logging.INFO

def configure(debug=False):
    """Configure console and rotating project-file logging exactly once."""
    level=_level(debug); root=logging.getLogger(); root.setLevel(level); formatter=SecretSafeFormatter(FORMAT)
    if not any(getattr(handler,'_chess_vision_console',False) for handler in root.handlers):
        console=logging.StreamHandler(); console._chess_vision_console=True; console.setLevel(level); console.setFormatter(formatter); root.addHandler(console)
    if not any(getattr(handler,'_chess_vision_app_log',False) for handler in root.handlers):
        handler=_file_handler('app.log')
        handler._chess_vision_app_log=True; handler.setLevel(level); handler.setFormatter(formatter); root.addHandler(handler)
    for handler in root.handlers:
        if getattr(handler,'_chess_vision_console',False) or getattr(handler,'_chess_vision_app_log',False): handler.setLevel(level)
    for name in ('httpx','httpcore','openai','urllib3'): logging.getLogger(name).setLevel(logging.WARNING)
    warnings.filterwarnings('once',category=DeprecationWarning,module=r'(chess|mss)(\.|$)')
    active = next(handler for handler in root.handlers if getattr(handler,'_chess_vision_app_log',False))
    path = Path(active.baseFilename) if hasattr(active, 'baseFilename') else None
    logging.getLogger(__name__).info('APP_LOGGING_READY level=%s path=%s',logging.getLevelName(level),path)
    return path

def install_exception_hook(context):
    """Persist uncaught exceptions independently from normal application logs."""
    logger=logging.getLogger('chess_vision.crash'); logger.setLevel(logging.ERROR); logger.propagate=False
    if not any(getattr(handler,'_chess_vision_crash_log',False) for handler in logger.handlers):
        crash=_file_handler('crash.log')
        crash._chess_vision_crash_log=True; crash.setFormatter(SecretSafeFormatter(FORMAT)); logger.addHandler(crash)
    def hook(kind,value,tb):
        try: details=context()
        except Exception: details={}
        logger.error('UNCAUGHT_EXCEPTION type=%s message=%s context=%s\n%s',kind.__name__,value,details,''.join(traceback.format_exception(kind,value,tb)))
    sys.excepthook=hook
