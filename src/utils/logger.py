import structlog
import logging
import sys
import os

def setup_logger():
    """
    Configures structlog for JSON logging in production and
    pretty-printed logging in development.
    """
    env = os.environ.get("PARTNER_OS_ENV", "development")
    
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if env == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
        
    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    """
    Returns a bound logger for the specified component.
    """
    return structlog.get_logger(name)

# Initial setup
setup_logger()
