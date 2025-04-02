import logging
logging.basicConfig(level=logging.DEBUG)
logging.debug("Starting script...")

# ... твои импорты ...

logging.debug("Imports completed, initializing bot...")

# ... остальной код ...

if __name__ == "__main__":
    try:
        logging.debug("Starting main...")
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
        raise