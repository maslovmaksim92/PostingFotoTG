from fastapi import FastAPI
from webhook import api_router

app = FastAPI()
app.include_router(api_router)