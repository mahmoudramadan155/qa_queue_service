import logging
from app.config import settings

def setup_logger():
    """Setup application logger"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger("qa_service")

logger = setup_logger()
