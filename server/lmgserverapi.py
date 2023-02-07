from fastapi import FastAPI, Request, Depends, Response, HTTPException
from typing import Optional
from pydantic import BaseModel
from typing import Optional
import settings
import json
from uuid import uuid4
import os
from os import path
from threading import Thread
from datetime import datetime, timedelta
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse


serverapp: FastAPI = FastAPI(title="LoRaMobGate Server API")
version=1
api_path="/lmg/messenger"
