from pydantic import BaseModel
from s_settings import DB_NAME
from typing import Union, Optional
from sqlalchemy import Boolean, Column, Integer, String

from db import Base
from redis_om import HashModel, Field



### FASTAPI MODELS
class Token(BaseModel):
	access_token: str
	token_type: str


class TokenData(BaseModel):
	dev_addr: Union[int, None] = None


class User(BaseModel):
	dev_addr: int
	username: Optional[str]
	disabled: Union[bool, None] = None

class UserDB(Base):
	__tablename__ = "users"
	dev_addr = Column(Integer, primary_key=True, index=True)
	hashed_key = Column(String)
	disabled = Column(Boolean, default=False)

class NetPacketIP(HashModel):
	sender: int = Field(index = True)
	recipient: int = Field(index = True)
	timestamp: str = Field(index = True)
	packet: str = Field(index = True)
###
