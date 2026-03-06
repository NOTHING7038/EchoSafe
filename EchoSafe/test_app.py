#!/usr/bin/env python3
"""Minimal test app to debug the issue"""

from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/api/test")
async def test():
    return {"test": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
