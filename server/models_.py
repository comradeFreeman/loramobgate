# from peewee import SqliteDatabase, IntegerField, DateTimeField, \
# 	ForeignKeyField, CompositeKey, BooleanField, BlobField, CharField, SmallIntegerField, VirtualField
from pydantic import BaseModel
from s_settings import DB_NAME
from typing import Union
# from playhouse.signals import pre_save, Model
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db import Base
#db = SqliteDatabase(DB_NAME, pragmas={ 'journal_mode': 'wal', 'cache_size': -1024 * 64 })
#from proto import NetPacket
import json


### FASTAPI MODELS
class Token(BaseModel):
	access_token: str
	token_type: str


class TokenData(BaseModel):
	dev_addr: Union[int, None] = None


class User(BaseModel):
	dev_addr: int
	disabled: Union[bool, None] = None

# class UserFull(User):
# 	hashed_key: str
#
# 	class Config:
# 		orm_mode = True


class UserDB(Base):
	__tablename__ = "users"

	dev_addr = Column(Integer, primary_key=True, index=True)
	hashed_key = Column(String)
	disabled = Column(Boolean, default=False)

class NetPacketIP(BaseModel):
	sender: int
	recipient: int
	timestamp: str
	packet: bytes

###
