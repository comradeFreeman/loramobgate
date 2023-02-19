DB_NAME = "db.sqlite"
SECRET_KEY = "9daf1233962e206bb44f70ccd5c7791d9372c0f7e2246e8383bb53e627f37c49"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# This Redis instance is tuned for durability.
REDIS_DATA_URL = "redis://localhost:6380"

# This Redis instance is tuned for cache performance.
REDIS_CACHE_URL = "redis://localhost:6379"

TTL_NETPACKET = 86400