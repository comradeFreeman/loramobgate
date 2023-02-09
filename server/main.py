from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
import messengerapi
import networkapi

app = FastAPI()#root_path="/api/v1") # docs_url=None, redoc_url=None)
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
