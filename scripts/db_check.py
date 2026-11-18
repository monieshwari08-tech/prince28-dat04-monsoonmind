"""Check that DATABASE_URL in .env works."""

import asyncio

from sqlalchemy import text

from monsoonmind.config import get_settings
from monsoonmind.db.session import make_engine


async def main() -> None:
    engine = make_engine(get_settings())
    async with engine.connect() as conn:
        version = await conn.scalar(text("SELECT version()"))
        database = await conn.scalar(text("SELECT current_database()"))
    await engine.dispose()
    print(f"Connected to database '{database}'")
    print(version)


if __name__ == "__main__":
    asyncio.run(main())
