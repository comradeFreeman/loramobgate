import sys
sys.path.append("device")
from fastapi import FastAPI, Request, Depends, Response, HTTPException, status
from typing import Optional
from pydantic import BaseModel
from typing import Optional
#import s_settings as settings
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

from s_settings import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM
from sqlalchemy.orm import Session

from models import Base, User, Token, TokenData, UserDB, NetPacketIP, NetPacketCache
from db import SessionLocal, engine

# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
Base.metadata.create_all(bind=engine)

# Dependency
# def get_db():
db = SessionLocal()
try:
	db #yield
finally:
	db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
serverapp: FastAPI = FastAPI(title="LoRaMobGate Server API. Messenger section ")
version=1
api_path="/lmg/messenger"


# class Item(BaseModel):
# 	key: str
# 	value: Union[str, None] = None
#
#
# @serverapp.get("/items/")
# async def read_items(token: str = Depends(oauth2_scheme)):
# 	return {"token": token}
#
# @serverapp.post("/db/insert/")
# async def func(item: Item):
# 	print(item)
# 	db[item.key] = item.value
# 	db.commit()
# 	return Response(status_code=200)
#
# @serverapp.get("/db/read/")
# async def func():
# 	return {k:v for k, v in db.items()}


# "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_key(plain_key, hashed_key):
	return pwd_context.verify(plain_key, hashed_key)

def get_user(dev_addr: int) -> UserDB:
	return db.query(UserDB).filter(UserDB.dev_addr == dev_addr).first()
	#User(dev_addr = user_db.dev_addr, disabled = user_db.disabled)#, hashed_key = user_db.hashed_key)

# def create_user(user: User):
# 	db_user = UserDB(dev_addr = user.dev_addr, hashed_key = pwd_context.hash("123456"))
# 	db.add(db_user)
# 	db.commit()
# 	db.refresh(db_user)
# 	return db_user

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

# @serverapp.get("/users/me/items/")
# async def read_own_items(current_user: UserDB = Depends(get_current_active_user), users = Depends(get_users)):
# 	return {"current": current_user, "all": users}


#
# @serverapp.post("/users/create/", response_model=User)
# async def create(user: User):
# 	create_user(user)
# 	user = User(dev_addr = user.dev_addr, disabled = user.disabled)#, hashed_key = pwd_context.hash("12345678"))
# 	return user

@serverapp.post("/messages/send/")
async def new_message(net_packet: NetPacketIP, current_user: UserDB = Depends(get_current_active_user)):
	print(net_packet)
	new = NetPacketCache.create(
						sender = net_packet.sender,
						recipient = net_packet.recipient,
						timestamp = net_packet.timestamp,
						packet = net_packet.packet)
	#print(, current_user)

@serverapp.get("/messages/count/")
async def count_messages(current_user: UserDB = Depends(get_current_active_user)):
	print(NetPacketCache.get_or_none())
	a = NetPacketCache.get_or_none(recipient = current_user.dev_addr)
	if a:
		print(a)
		print(len(a))


@serverapp.get("/messages/get/")
async def get_messages(current_user: UserDB = Depends(get_current_active_user), offset: int = 0, limit: int = 10):
	print()