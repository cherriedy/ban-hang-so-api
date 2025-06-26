import json
import os

import firebase_admin
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from firebase_admin import credentials

load_dotenv()

# Load Firebase credentials
# Priority: FIREBASE_CREDENTIALS_JSON_CONTENT env var (for production/Render)
# Fallback: Local JSON file (for local development)
firebase_cred_json_content = os.environ.get('FIREBASE_CREDENTIALS_JSON_CONTENT')

# Get Firebase Storage bucket name from environment variable
firebase_storage_bucket = os.environ.get('FIREBASE_STORAGE_BUCKET')
if not firebase_storage_bucket:
    print("CRITICAL ERROR: FIREBASE_STORAGE_BUCKET environment variable is not set.")
    print("Set FIREBASE_STORAGE_BUCKET to your Firebase Storage bucket name (e.g., 'your-app.appspot.com').")
    raise RuntimeError("FIREBASE_STORAGE_BUCKET environment variable is required.")

if firebase_cred_json_content:
    try:
        cred_dict = json.loads(firebase_cred_json_content)
        cred = credentials.Certificate(cred_dict)
        print("Initialized Firebase from FIREBASE_CREDENTIALS_JSON_CONTENT env var.")
    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: FIREBASE_CREDENTIALS_JSON_CONTENT is set but contains invalid JSON: {e}")
        print(
            "The application will now exit. Ensure the environment variable is correctly set in your hosting environment (e.g., Render).")
        raise  # Re-raise the exception to stop the application
    except Exception as e:  # Catch any other potential errors during cert init from env var
        print(f"CRITICAL ERROR: Failed to initialize Firebase from FIREBASE_CREDENTIALS_JSON_CONTENT: {e}")
        print("The application will now exit.")
        raise
else:
    # FIREBASE_CREDENTIALS_JSON_CONTENT is not set, so assume local development
    # and use the local service account key file.
    local_cred_file = "cuahangso-firebase-adminsdk-fbsvc-22a0625424.json"
    try:
        cred = credentials.Certificate(local_cred_file)
        print(f"Initialized Firebase from local JSON file: {local_cred_file}")
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Local credentials file '{local_cred_file}' not found.")
        print("This file is required for local development if FIREBASE_CREDENTIALS_JSON_CONTENT is not set.")
        print("The application will now exit.")
        raise
    except Exception as e:  # Catch other errors like invalid format in local file
        print(f"CRITICAL ERROR: Failed to initialize Firebase from local file '{local_cred_file}': {e}")
        print("The application will now exit.")
        raise

# Pass storageBucket option to initialize_app
firebase_admin.initialize_app(cred, {
    'storageBucket': firebase_storage_bucket
})

app = FastAPI(title="Ban Hang So API")

from api.auth.routers import router as auth_router
from api.stores.routers import router as stores_router
from api.products.routers import router as products_router

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(stores_router, prefix="/stores", tags=["stores"])
app.include_router(products_router, prefix="/products", tags=["products"])


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
