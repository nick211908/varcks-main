import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_logger(name: str):
    """
    Returns a configured logger instance.
    """
    return logging.getLogger(name)

