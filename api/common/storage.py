"""
Utility module for Firebase Storage operations.
This module provides functions for uploading, retrieving, and managing files in Firebase Storage.
"""
import os
import uuid
from datetime import datetime
from typing import BinaryIO, Optional

import firebase_admin
from firebase_admin import storage
from fastapi import HTTPException, UploadFile
from starlette import status


def get_storage_bucket():
    """Get the Firebase Storage bucket instance."""
    try:
        # Initialize default app if not already done
        if not firebase_admin._apps:
            raise ValueError("Firebase app not initialized")

        # Get default bucket
        return storage.bucket()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Storage bucket: {str(e)}"
        )


async def upload_image(
    file: UploadFile,
    folder: str = "products",
    file_id: Optional[str] = None,
    is_temporary: bool = True
) -> str:
    """
    Upload an image file to Firebase Storage.

    Args:
        file: The file to upload
        folder: The folder path within the bucket (e.g., 'products', 'brands')
        file_id: Optional custom ID for the file (will generate UUID if not provided)
        is_temporary: Whether this is a temporary upload (will be marked for potential cleanup)

    Returns:
        The public URL of the uploaded file

    Raises:
        HTTPException: If upload fails or file is not valid
    """
    # Validate file
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    # Check content type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File must be an image, got {content_type}"
        )

    try:
        # Read file content
        contents = await file.read()

        # Generate a unique filename if not provided
        if not file_id:
            file_id = f"{uuid.uuid4()}"

        # Get file extension from content type or original filename
        extension = os.path.splitext(file.filename)[1] if file.filename else ""
        if not extension and "/" in content_type:
            ext_from_type = content_type.split("/")[1].lower()
            if ext_from_type in ["jpeg", "jpg", "png", "gif", "webp", "svg+xml"]:
                extension = f".{ext_from_type.replace('+xml', '')}"

        # If still no extension, default to .jpg
        if not extension:
            extension = ".jpg"

        # Create the storage path and filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{file_id}_{timestamp}{extension}"
        storage_path = f"{folder}/{filename}"

        # Get bucket and upload
        bucket = get_storage_bucket()
        blob = bucket.blob(storage_path)

        # Set metadata to mark temporary uploads for later cleanup
        metadata = {}
        if is_temporary:
            metadata["temporary"] = "true"
            metadata["upload_time"] = timestamp

        # Upload the file with metadata
        blob.upload_from_string(
            contents,
            content_type=content_type,
            metadata=metadata
        )

        # Make the file public and get URL
        blob.make_public()
        return blob.public_url

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )
    finally:
        # Reset file cursor for potential future reads
        await file.seek(0)


async def delete_image_by_url(url: str) -> bool:
    """
    Delete an image from Firebase Storage using its public URL.

    Args:
        url: The public URL of the image to delete

    Returns:
        True if deletion was successful, False otherwise

    Raises:
        HTTPException: If deletion fails
    """
    try:
        bucket = get_storage_bucket()

        # Extract the blob path from URL
        if not url:
            return False

        # Parse URL to get blob name
        # URL format: https://storage.googleapis.com/BUCKET_NAME/PATH/TO/FILE
        url_parts = url.split("/")
        if len(url_parts) < 5:
            return False

        # Extract path (everything after the bucket name)
        bucket_name = url_parts[3]
        blob_path = "/".join(url_parts[4:])

        # Delete the blob
        blob = bucket.blob(blob_path)
        blob.delete()
        return True
    except Exception as e:
        # Log error but don't fail the operation
        print(f"Error deleting image: {str(e)}")
        return False


async def mark_image_permanent(url: str) -> bool:
    """
    Mark an uploaded image as permanent (not temporary).
    This removes the temporary marker from the image metadata.

    Args:
        url: The public URL of the image

    Returns:
        True if marking was successful, False otherwise
    """
    try:
        bucket = get_storage_bucket()

        # Extract the blob path from URL
        if not url:
            return False

        # Parse URL to get blob name
        # URL format: https://storage.googleapis.com/BUCKET_NAME/PATH/TO/FILE
        url_parts = url.split("/")
        if len(url_parts) < 5:
            return False

        # Extract path (everything after the bucket name)
        bucket_name = url_parts[3]
        blob_path = "/".join(url_parts[4:])

        # Get the blob and update metadata
        blob = bucket.blob(blob_path)
        if not blob.exists():
            return False

        # Get current metadata and remove temporary markers
        metadata = blob.metadata or {}
        if "temporary" in metadata:
            del metadata["temporary"]

        # Update blob metadata
        blob.metadata = metadata
        blob.patch()

        return True
    except Exception as e:
        # Log error but don't fail the operation
        print(f"Error marking image as permanent: {str(e)}")
        return False


async def cleanup_temporary_images(hours_threshold: int = 24):
    """
    Clean up temporary images that are older than the specified threshold.

    Args:
        hours_threshold: Number of hours after which temporary images should be deleted
    """
    try:
        bucket = get_storage_bucket()
        blobs = bucket.list_blobs()

        # Get current time for comparison
        current_time = datetime.now()
        delete_threshold = current_time.timestamp() - (hours_threshold * 3600)

        # Check each blob
        for blob in blobs:
            # Skip if no metadata or not marked temporary
            if not blob.metadata or "temporary" not in blob.metadata or blob.metadata["temporary"] != "true":
                continue

            # Check upload time if available
            upload_time_str = blob.metadata.get("upload_time")
            if not upload_time_str:
                continue

            try:
                # Parse the timestamp
                upload_time = datetime.strptime(upload_time_str, "%Y%m%d%H%M%S")

                # Delete if older than threshold
                if upload_time.timestamp() < delete_threshold:
                    blob.delete()
                    print(f"Deleted temporary image: {blob.name}")
            except ValueError:
                # If timestamp can't be parsed, skip
                continue
    except Exception as e:
        print(f"Error during temporary image cleanup: {str(e)}")
