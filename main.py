import json
import os

import firebase_admin
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from firebase_admin import credentials

load_dotenv()

cred_json = os.environ.get('FIREBASE_CREDENTIALS')
if cred_json:
    cred = credentials.Certificate(json.loads(cred_json))
else:
    # Path to the service account key json
    cred = credentials.Certificate("")

firebase_admin.initialize_app(cred)

app = FastAPI(title="Ban Hang So API")

from api.auth.routers import router as auth_router
from api.stores.routers import router as stores_router

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(stores_router, prefix="/stores", tags=["stores"])


@app.get("/")
def read_root():
    """Root endpoint for the API.
    Returns:
        A simple message indicating the API is running.
    """
    return {"message": "Ban Hang So API"}


if __name__ == "__main__":
    # Set port from environment variable or default to 8000
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
