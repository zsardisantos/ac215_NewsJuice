

'''
main.py

Main app file for chatter service as a FastAPI

Endpoints:

* /healthz
For checking whether the app works

* /api/chatter
Main chatter endpoint: calls the chatter() function.

'''


#load_dotenv()  # This loads .env file
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from typing import Dict, Any

from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from chatter_handler import chatter


# --------------------------
# Config
# --------------------------
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")
# --------------------------
# App / Clients
# --------------------------
logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
)

# --------------------------
# Health
# --------------------------
@app.get("/healthz")
async def healthz_root() -> Dict[str, bool]:
    return {"ok": True}

# --------------------------
# Main Endpoint
# --------------------------
@app.post("/api/chatter")
async def chatter_endpoint(payload: Dict[str, Any] = Body(...)):
    return await chatter(payload)

