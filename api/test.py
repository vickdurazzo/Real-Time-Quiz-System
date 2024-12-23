from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
import redis
import time
import uuid

app = FastAPI()

# Redis connection
redis_client = redis.StrictRedis(host="localhost", port=6379, db=0, decode_responses=True)

redis_client.set('foo', 'hello world')
# True
print(redis_client.get('foo'))
