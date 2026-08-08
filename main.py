import logging
import sys
from dotenv import load_dotenv

load_dotenv()

from models import init_db
from telegram import run_telegram_bot
from agent import get_accounts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)

def main():
    logger.info("Chrysanthemius started")

    init_db()
    run_telegram_bot()

if __name__ == "__main__":
    main()
