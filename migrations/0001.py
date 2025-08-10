import asyncio

import aiosqlite

DB_FILE = "../db.sqlite"

async def make_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        ALTER TABLE subscriptions
        ADD COLUMN alert_threshold INTEGER
        DEFAULT 1
        """)
        await db.execute("""
        ALTER TABLE subscriptions
        ADD COLUMN interval INTEGER
        DEFAULT 3600
        """)
        await db.commit()

if __name__ == '__main__':
    asyncio.run(make_migration())