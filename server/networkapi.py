from fastapi import FastAPI, Request, Depends, Response, HTTPException
from typing import Optional, Union
from pydantic import BaseModel
from typing import Optional
import s_settings as settings
import json
from uuid import uuid4
import os
from os import path
from threading import Thread
from datetime import datetime, timedelta
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
serverapp: FastAPI = FastAPI(title="LoRaMobGate Server API. Network section")
version=1
api_path="/lmg/network"

@serverapp.get("/items/")
async def read_items(token: str = Depends(oauth2_scheme)):
	return {"token": token}

@serverapp.post("/neighbors/")
async def add_neighbors(item: Union[list, int]):
	print(item)