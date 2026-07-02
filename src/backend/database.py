from motor.motor_asyncio import AsyncIOMotorClient
from backend.config import MONGO_URI, MONGO_DB

client: AsyncIOMotorClient | None = None


async def connect_db():
    global client
    client = AsyncIOMotorClient(MONGO_URI)
    return client[MONGO_DB]


async def close_db():
    global client
    if client:
        client.close()
        client = None


def get_db():
    if client is None:
        raise RuntimeError("Database not connected")
    return client[MONGO_DB]