"""Central logging configuration.

All modules obtain their logger with ``logging.getLogger(__name__)``; this module
only decides *how* records are formatted and where they go.
"""

import logging.config

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger and align Uvicorn's loggers with the same format."""
    logging.config.dictConfig(
        {
            "version": 1,
            # Keep loggers created before this call (e.g. Uvicorn's) working.
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": LOG_FORMAT, "datefmt": "%Y-%m-%d %H:%M:%S"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"level": level, "handlers": ["console"]},
            "loggers": {
                # Route Uvicorn through the root handler so the output is uniform.
                "uvicorn": {"level": level, "handlers": [], "propagate": True},
                "uvicorn.error": {"level": level, "handlers": [], "propagate": True},
                # Request logging is done by our own middleware (see app.main).
                "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": True},
            },
        }
    )
