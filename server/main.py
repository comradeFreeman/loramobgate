from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Optional
# import messengerapi
# import networkapi

import redis
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from pydantic import EmailStr
from redis_om import HashModel, NotFoundError, Migrator
from redis_om import get_redis_connection

import sys
sys.path.append("device")
from fastapi import FastAPI, Request, Depends, Response, HTTPException, status
from typing import Optional
from pydantic import BaseModel
from typing import Optional
import json
from uuid import uuid4
import os
from os import path
from threading import Thread
from datetime import datetime, timedelta
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from typing import Union
import traceback
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from s_settings import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, TTL_NETPACKET,\
	VERSION, REDIS_CACHE_URL, REDIS_DATA_URL, API_PATH
from sqlalchemy.orm import Session
from models import Base, User, Token, TokenData, UserDB, NetPacketIP
from db import SessionLocal, engine
from fastapi_cache.decorator import cache
from fastapi.routing import APIRouter

app = FastAPI()
serverapp = FastAPI(title="LoRaMobGate Server API")

app.mount(f"/v{VERSION}{API_PATH}", serverapp)

Base.metadata.create_all(bind=engine)

# Dependency
# def get_db():
db = SessionLocal()
try:
	db #yield
finally:
	db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



# "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Item(BaseModel):
	name: str
	price: float
	is_offer: Optional[bool] = None

@serverapp.on_event("startup")
async def startup():
	r = redis.from_url(REDIS_CACHE_URL, encoding="utf8", decode_responses=True)
	FastAPICache.init(RedisBackend(r), prefix="fastapi-cache")

	# You can set the Redis OM URL using the REDIS_OM_URL environment
	# variable, or by manually creating the connection using your model's
	# Meta object.
	NetPacketIP.Meta.database = get_redis_connection(url=REDIS_DATA_URL,
													 decode_responses=True)

@serverapp.get("/")
async def root():
	return {"message": "Hello World"}

def verify_key(plain_key, hashed_key):
	return pwd_context.verify(plain_key, hashed_key)

def get_user(dev_addr: int) -> UserDB:
	return db.query(UserDB).filter(UserDB.dev_addr == dev_addr).first()

def get_users(skip: int = 0, limit: int = 100):
	return db.query(UserDB).offset(skip).limit(limit).all()

def authenticate_user(dev_addr: int, key: str):
	user = get_user(dev_addr)
	if not user:
		return False
	if not verify_key(key, user.hashed_key):
		return False
	return user

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
	to_encode = data.copy()
	if expires_delta:
		expire = datetime.utcnow() + expires_delta
	else:
		expire = datetime.utcnow() + timedelta(minutes=15)
	to_encode.update({"exp": expire})
	encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
	return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
	credentials_exception = HTTPException(
		status_code=status.HTTP_401_UNAUTHORIZED,
		detail="Could not validate credentials",
		headers={"WWW-Authenticate": "Bearer"},
	)
	try:
		payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
		dev_addr: int = int(payload.get("sub"), 16)
		if dev_addr is None:
			raise credentials_exception
		token_data = TokenData(dev_addr = dev_addr)
	except JWTError:
		raise credentials_exception
	user_db = get_user(dev_addr=token_data.dev_addr)
	if not user_db:
		raise credentials_exception
	user = User(dev_addr = user_db.dev_addr, disabled = user_db.disabled)
	return user

async def get_current_active_user(current_user: UserDB = Depends(get_current_user)):
	if current_user.disabled:
		raise HTTPException(status_code=400, detail="Inactive user")
	return current_user

@serverapp.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
	user: Union[bool, User] = authenticate_user(int(form_data.username), form_data.password)
	if not user:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Incorrect username or password",
			headers={"WWW-Authenticate": "Bearer"},
		)
	access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
	access_token = create_access_token(
		data={"sub": hex(user.dev_addr)}, expires_delta=access_token_expires
	)
	return {"access_token": access_token, "token_type": "bearer"}

@serverapp.get("/users/me/", response_model=User)
async def read_users_me(current_user: UserDB = Depends(get_current_active_user)):
	return current_user

@serverapp.post("/messenger/messages/send/")
async def new_message(net_packet: NetPacketIP, current_user: UserDB = Depends(get_current_active_user)):
	net_packet.save()
	net_packet.expire(TTL_NETPACKET)

@serverapp.get("/messenger/messages/count/")
@cache(expire=10)
async def count_messages(current_user: UserDB = Depends(get_current_active_user)):
	# Для поиска нужен модуль RediSearch, который есть в Redis Stack Server
	return {"incoming": NetPacketIP.find(NetPacketIP.recipient == current_user.dev_addr).count()}

@serverapp.get("/messenger/messages/get/")
async def get_messages(current_user: UserDB = Depends(get_current_active_user), offset: int = 0, limit: int = 10):
	new = NetPacketIP.find(NetPacketIP.recipient == current_user.dev_addr).page(offset = offset, limit = limit)
	for np in new: NetPacketIP.delete(np.pk)
	return {"count": len(new), "offset": offset, "messages": new}

@serverapp.post("/network/neighbors/")
async def add_neighbors(item: Union[list, int]):
	print(item)