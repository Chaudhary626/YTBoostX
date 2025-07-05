import aiosqlite
import asyncio
from datetime import datetime, timedelta

DB_NAME = "ytboostx.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                trial_start_date TEXT,
                subscription_end_date TEXT,
                strikes INTEGER DEFAULT 0,
                ip_hash TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                is_banned BOOLEAN DEFAULT FALSE
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_title TEXT,
                video_thumbnail TEXT,
                instructions TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS proofs (
                proof_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER,
                prover_id INTEGER,
                proof_file_id TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                reason TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (task_id),
                FOREIGN KEY (prover_id) REFERENCES users (user_id)
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS payment_proofs (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                file_id TEXT,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        await db.commit()

async def get_setting(key):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else None

async def set_setting(key, value):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

# Add other database functions for user, task, proof management here...
# (Full code for all functions is extensive; key functions are shown in handlers)
