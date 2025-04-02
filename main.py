async def main():
    logging.info("Bot starting...")
    asyncio.create_task(check_reminders())
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logging.error(f"Polling failed: {e}")
        raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Для отладки
    asyncio.run(main())