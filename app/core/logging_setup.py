"""Project-rooted, low-noise diagnostic logging for the desktop application."""
import logging
import os
import sys
import traceback
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIRECTORY = PROJECT_ROOT / 'logs'
APP_LOG_PATH = LOG_DIRECTORY / 'app.log'
CRASH_LOG_PATH = LOG_DIRECTORY / 'crash.log'
FORMAT = '%(asctime)s %(levelname)s %(name)s %(message)s'

def _level(debug=False):
    configured=os.getenv('CHESS_VISION_LOG_LEVEL','').upper()
    return logging.DEBUG if debug or configured=='DEBUG' else logging.INFO

def configure(debug=False):
    """Configure console and rotating project-file logging exactly once."""
    LOG_DIRECTORY.mkdir(parents=True,exist_ok=True)
    level=_level(debug); root=logging.getLogger(); root.setLevel(level); formatter=logging.Formatter(FORMAT)
    if not any(getattr(handler,'_chess_vision_console',False) for handler in root.handlers):
        console=logging.StreamHandler(); console._chess_vision_console=True; console.setLevel(level); console.setFormatter(formatter); root.addHandler(console)
    if not any(getattr(handler,'_chess_vision_app_log',False) for handler in root.handlers):
        handler=RotatingFileHandler(APP_LOG_PATH,maxBytes=5*1024*1024,backupCount=3,encoding='utf-8')
        handler._chess_vision_app_log=True; handler.setLevel(level); handler.setFormatter(formatter); root.addHandler(handler)
    for handler in root.handlers:
        if getattr(handler,'_chess_vision_console',False) or getattr(handler,'_chess_vision_app_log',False): handler.setLevel(level)
    for name in ('httpx','httpcore','openai','urllib3'): logging.getLogger(name).setLevel(logging.WARNING)
    warnings.filterwarnings('once',category=DeprecationWarning,module=r'(chess|mss)(\.|$)')
    logging.getLogger(__name__).info('APP_LOGGING_READY level=%s path=%s',logging.getLevelName(level),APP_LOG_PATH)
    return APP_LOG_PATH

def install_exception_hook(context):
    """Persist uncaught exceptions independently from normal application logs."""
    LOG_DIRECTORY.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('chess_vision.crash'); logger.setLevel(logging.ERROR); logger.propagate=False
    if not any(getattr(handler,'_chess_vision_crash_log',False) for handler in logger.handlers):
        crash=RotatingFileHandler(CRASH_LOG_PATH,maxBytes=5*1024*1024,backupCount=3,encoding='utf-8')
        crash._chess_vision_crash_log=True; crash.setFormatter(logging.Formatter(FORMAT)); logger.addHandler(crash)
    def hook(kind,value,tb):
        try: details=context()
        except Exception: details={}
        logger.error('UNCAUGHT_EXCEPTION type=%s message=%s context=%s\n%s',kind.__name__,value,details,''.join(traceback.format_exception(kind,value,tb)))
    sys.excepthook=hook
