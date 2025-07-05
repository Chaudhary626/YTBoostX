from datetime import datetime, timedelta
import hashlib
import database as db

async def is_admin(user_id):
    admin_id = await db.get_setting('ADMIN_ID')
    return str(user_id) == str(admin_id)

async def check_user_status(user_id):
    async with db.aiosqlite.connect(db.DB_NAME) as conn:
        cursor = await conn.execute("SELECT trial_start_date, subscription_end_date, is_banned FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            return "not_registered", None

        is_banned = user[2]
        if is_banned:
            return "banned", None

        trial_start_date_str = user[0]
        subscription_end_date_str = user[1]
        trial_days_str = await db.get_setting('trial_days')
        trial_duration = int(trial_days_str) if trial_days_str else 7

        if subscription_end_date_str:
            sub_end_date = datetime.fromisoformat(subscription_end_date_str)
            if datetime.now() < sub_end_date:
                return "subscribed", sub_end_date
            else:
                return "subscription_expired", None

        if trial_start_date_str:
            trial_start_date = datetime.fromisoformat(trial_start_date_str)
            if datetime.now() < trial_start_date + timedelta(days=trial_duration):
                remaining = (trial_start_date + timedelta(days=trial_duration)) - datetime.now()
                return "trial_active", remaining
            else:
                return "trial_expired", None

        return "error", None # Should not happen

def generate_ip_hash(user_id, chat_id):
    return hashlib.sha256(f"{user_id}-{chat_id}".encode()).hexdigest()
