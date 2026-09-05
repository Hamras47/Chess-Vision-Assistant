import sys,logging,traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
def configure(debug=False):
    Path('logs').mkdir(exist_ok=True); root=logging.getLogger(); root.setLevel(logging.DEBUG if debug else logging.INFO)
    if not any(isinstance(h,RotatingFileHandler) for h in root.handlers):
        try:
            handler=RotatingFileHandler('logs/chess_vision.log',maxBytes=2_000_000,backupCount=3,encoding='utf-8'); handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')); root.addHandler(handler)
        except OSError: root.addHandler(logging.NullHandler())
def install_exception_hook(context):
    logger=logging.getLogger('crash'); logger.setLevel(logging.ERROR); logger.propagate=False
    try:
        crash=RotatingFileHandler('logs/crash.log',maxBytes=1_000_000,backupCount=2,encoding='utf-8'); crash.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s')); logger.addHandler(crash)
    except OSError: logger.addHandler(logging.NullHandler())
    def hook(kind,value,tb):
        try:details=context()
        except Exception:details={}
        logger.error('Unhandled exception type=%s message=%s context=%s\n%s',kind.__name__,value,details,''.join(traceback.format_exception(kind,value,tb)))
    sys.excepthook=hook
