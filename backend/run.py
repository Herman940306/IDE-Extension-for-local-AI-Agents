"""
Backend Runner Script
Project Creator: Herman Swanepoel
"""

import os
import sys

import uvicorn

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="127.0.0.1", port=8001, reload=True, log_level="info")
