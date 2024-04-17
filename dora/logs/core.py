import logging

from .models import ActionLog

__all__ = ["logger"]


class ActionLogHandler(logging.Handler):
    def emit(self, record):
        # voir : https://docs.python.org/3/library/logging.html#logrecord-attributes
        payload = payload = {"level": record.levelname, "msg": record.msg}
        if record.args and isinstance(record.args, dict):
            payload |= record.args
        ActionLog(payload=payload).save()


# ne pas s'amuser à instancier un logger pour les actions, plutôt utiliser :
# logging.getLogger("dora.logs.core")
# (ce logger est initialisé à la création de l'app Django)
logger = logging.getLogger(__name__)
logger.addHandler(ActionLogHandler())
