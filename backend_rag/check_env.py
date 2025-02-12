import os
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



def check_env():
    load_dotenv()
    # add more information about the process
    # List of required environment variables
    required_vars = ['WCD_URL', 'WCD_API_KEY', 'OPENAI_API_KEY']
    
    logger.info("Checking environment variables...")
    
    # Get the absolute path of the .env file
    env_path = os.path.abspath('.env')
    logger.info(f"Looking for .env file at: {env_path}")
    
    if not os.path.exists('.env'):
        logger.error(f".env file not found at {env_path}")
        return False
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value is None:
            missing_vars.append(var)
        else:
            # Show the value for URL, mask the keys
            if var == 'WCD_URL':
                logger.info(f"{var}: {value}")
            else:
                logger.info(f"{var}: {'*' * 8}")
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("All required environment variables are set")
    return True

if __name__ == "__main__":
    check_env() 
