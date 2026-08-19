import logging
import sys
from pythonjsonlogger import jsonlogger
import os

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logHandler = logging.StreamHandler(sys.stdout)
    
    # JSON Formatter
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    logHandler.setFormatter(formatter)
    
    # Remove existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.addHandler(logHandler)
    
    # Create a file handler as well
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    fileHandler = logging.FileHandler(os.path.join(log_dir, 'app.log'))
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    
    return logger
