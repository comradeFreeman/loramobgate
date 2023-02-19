from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
import messengerapi
import networkapi
from s_settings import REDIS_CACHE_URL, REDIS_DATA_URL

import redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from pydantic import EmailStr
from redis_om import HashModel, NotFoundError, Migrator
from redis_om import get_redis_connection

app = FastAPI()
app.mount(f"/v{messengerapi.version}{messengerapi.api_path}", messengerapi.serverapp)
app.mount(f"/v{networkapi.version}{networkapi.api_path}", networkapi.serverapp)

class Item(BaseModel):
	name: str
	price: float
	is_offer: Optional[bool] = None

@app.get("/")
async def root():
	return {"message": "Hello World"}

@app.get("/hello/{name}")
async def say_hello(name: str):
	return {"message": f"Hello {name}"}

@app.get("/items/list")
async def read_item(a: int = 2, b: str = 3, c: int = 4, item_id: Optional[int] = 0, q: Optional[str] = None):
	return {"item_id": item_id, "q": q, "a": a, "b": b, "c": c}

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: Item):
	return {"item_name": item.name, "item_id": item_id}



@app.on_event("startup")
async def startup():
	r = redis.from_url(REDIS_CACHE_URL, encoding="utf8", decode_responses=True)
	FastAPICache.init(RedisBackend(r), prefix="fastapi-cache")

	# You can set the Redis OM URL using the REDIS_OM_URL environment
	# variable, or by manually creating the connection using your model's
	# Meta object.
	messengerapi.NetPacketIP.Meta.database = get_redis_connection(url=REDIS_DATA_URL,
													 decode_responses=True)
