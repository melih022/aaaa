#
# Mongo: tolerant init. Use MONGO_DB_URI from config; no remote fallback secrets.
#

from motor.motor_asyncio import AsyncIOMotorClient as _mongo_client_
from pymongo import MongoClient

import config

from ..logging import LOGGER

_uri = config.MONGO_DB_URI or "mongodb://localhost:27017"

LOGGER(__name__).info(f"Connecting MongoDB: {_uri.split('@')[-1]}")

_mongo_async_ = _mongo_client_(_uri)
_mongo_sync_ = MongoClient(_uri)

# Database name is fixed as "Kaal" for backward compatibility with existing collections.
mongodb = _mongo_async_.Kaal
pymongodb = _mongo_sync_.Kaal
