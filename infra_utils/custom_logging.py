import os
import logging

DEBUG = True if os.environ.get("DEBUG", "False") == "True" else False


class DjangoDebugTrue(logging.Filter):
    def filter(self, record):
        return DEBUG


class DjangoDebugFalse(logging.Filter):
    def filter(self, record):
        return not DEBUG


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {"()": DjangoDebugFalse},
        "require_debug_true": {"()": DjangoDebugTrue},
    },
    "formatters": {
        "console": {
            "format": "{asctime} FILE:{pathname} LINE:{lineno} {levelname}:{message}",
            "style": "{",
            "datefmt": "%d-%m-%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            # 'filters': ['require_debug_false'],
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "loggers": {
        "app.logger": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
