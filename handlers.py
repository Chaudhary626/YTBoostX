import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database as db
from utils import is_admin, check_user_status, generate_ip_hash

# --- User Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with db.aiosqlite.connect(db.DB_NAME) as conn:
        cursor = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
        existing_user = await cursor.fetchone()
        if not existing_user:
            ip_hash = generate_ip_hash(user.id, update.message.chat_id)
            cursor_ip = await conn.execute("SELECT * FROM users WHERE ip_hash = ?", (ip_hash,))
            if await cursor_ip.fetchone():
                await update.message.reply_text("This device has already been used for a free trial.")
                return

            await conn.execute(
                "INSERT INTO users (user_id, username, trial_start_date, ip_hash) VALUES (?, ?, ?, ?)",
                (user.id, user.username, datetime.now().isoformat(), ip_hash)
            )
            await conn.commit()
            welcome_message = await db.get_setting('welcome_message') or "Welcome to YTBoostX! Your free trial has started."
            await update.message.reply_text(welcome_message)
        else:
            await update.message.reply_text("Welcome back!")

async def trial_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status, remaining = await check_user_status(update.effective_user.id)
    if status == "trial_active":
        await update.message.reply_text(f"Your free trial is active. It expires in {remaining.days} days and {remaining.seconds//3600} hours.")
    elif status == "subscribed":
        await update.message.reply_text(f"You have an active subscription until {remaining.strftime('%Y-%m-%d')}.")
    else:
        await update.message.reply_text("Your trial has expired. Use /pay to subscribe.")

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upi_id = await db.get_setting('upi_id') or "Not Set"
    price = "₹30"
    user_id = update.effective_user.id
    message = (
        f"Please pay {price} to the following UPI ID:\n\n"
        f"`{upi_id}`\n\n"
        f"**IMPORTANT**: You MUST include the following in the payment note/memo:\n"
        f"`UserID:{user_id}`\n\n"
        f"After payment, upload the screenshot using the `/submitpaymentproof` command."
    )
    await update.message.reply_text(message, parse_mode='Markdown')

async def submit_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please upload a screenshot of your payment.")
        return

    user_id = update.effective_user.id
    file_id = update.message.photo[-1].file_id

    async with db.aiosqlite.connect(db.DB_NAME) as conn:
        await conn.execute("INSERT INTO payment_proofs (user_id, file_id) VALUES (?, ?)", (user_id, file_id))
        await conn.commit()

    admin_id = await db.get_setting('ADMIN_ID')
    keyboard = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{file_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}_{file_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_photo(
        chat_id=admin_id,
        photo=file_id,
        caption=f"Payment proof from User ID: {user_id}",
        reply_markup=reply_markup
    )
    await update.message.reply_text("Your payment proof has been submitted for review.")

# --- Admin Commands ---

async def set_trial_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized.")
        return
    try:
        days = int(context.args[0])
        await db.set_setting('trial_days', str(days))
        await update.message.reply_text(f"Trial duration set to {days} days.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /settrialdays <days>")

async def payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action, user_id, file_id = data[0], int(data[1]), data[2]

    async with db.aiosqlite.connect(db.DB_NAME) as conn:
        if action == "approve":
            subscription_end_date = (datetime.now() + timedelta(days=30)).isoformat()
            await conn.execute(
                "UPDATE users SET subscription_end_date = ? WHERE user_id = ?",
                (subscription_end_date, user_id)
            )
            await conn.execute(
                "UPDATE payment_proofs SET status = 'approved' WHERE user_id = ? AND file_id = ?",
                (user_id, file_id)
            )
            await conn.commit()
            await context.bot.send_message(user_id, "Your subscription has been approved and is active for 30 days!")
            await query.edit_message_caption(caption=f"✅ Approved payment for User ID: {user_id}")
        elif action == "reject":
            await conn.execute(
                "UPDATE payment_proofs SET status = 'rejected' WHERE user_id = ? AND file_id = ?",
                (user_id, file_id)
            )
            await conn.commit()
            await context.bot.send_message(user_id, "Your payment proof was rejected. Please contact support if you think this is a mistake.")
            await query.edit_message_caption(caption=f"❌ Rejected payment for User ID: {user_id}")

# (Other handlers for /upload, /gettask, /strike, /broadcast, etc. would follow a similar pattern)
