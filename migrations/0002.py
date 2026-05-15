import asyncio

import aiosqlite

DB_FILE = "./db.sqlite"

async def make_migration():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
        ALTER TABLE users
        ADD COLUMN is_cbrf_subscribed BOOLEAN
        DEFAULT False
        """)
        await db.commit()

if __name__ == '__main__':
    asyncio.run(make_migration())