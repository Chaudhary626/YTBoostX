import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from aiohttp import web  # <-- CHANGE 1: Corrected import

import database as db
import handlers

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
ADMIN_ID = os.environ.get("ADMIN_ID")
PORT = int(os.environ.get('PORT', 8443))

async def main():
    """Start the bot."""
    # Initialize the database and settings
    await db.init_db()
    await db.set_setting('ADMIN_ID', ADMIN_ID)
    if not await db.get_setting('trial_days'):
        await db.set_setting('trial_days', '7')
    if not await db.get_setting('upi_id'):
        upi_id_from_env = os.environ.get("UPI_ID", "your-upi@bank")
        await db.set_setting('upi_id', upi_id_from_env)

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Register Handlers ---
    # User Commands
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("trialstatus", handlers.trial_status))
    application.add_handler(CommandHandler("pay", handlers.pay))
    application.add_handler(CommandHandler("submitpaymentproof", handlers.submit_payment_proof))
    # ... other user commands

    # Admin Commands
    application.add_handler(CommandHandler("settrialdays", handlers.set_trial_days))
    # ... other admin commands

    # Callback Query Handler
    application.add_handler(CallbackQueryHandler(handlers.payment_callback, pattern='^(approve_|reject_)'))

    # Set up webhook
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/telegram")

    # Run the bot with aiohttp web server
    # Run the bot with aiohttp web server
    async def telegram_webhook(request):
        update = Update.de_json(await request.json(), application.bot)
        logger.info(f"🔔 Received update: {update}")
        await application.process_update(update)
        return web.Response()

    async def webhook_ping(request):  # <-- This handles GET /telegram
        return web.Response(text="Webhook is alive!")

    app = web.Application()
    app.router.add_get("/telegram", webhook_ping)  # <-- Add this GET route
    app.router.add_post("/telegram", telegram_webhook)  # <-- Existing POST route

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    logger.info(f"🚀 Starting web server on port {PORT}")
    await site.start()

    # Keep the bot running
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    # Ensure database is initialized before running the main async loop
    asyncio.run(db.init_db())
    asyncio.run(main())
