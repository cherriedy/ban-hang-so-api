"""
Utility module for image storage operations.
This module provides functions for uploading, retrieving, and managing files.

MIGRATION NOTICE:
- Cloudinary is now the primary storage provider (NEW)
- Firebase Storage functions are marked as DEPRECATED
"""
import os
import uuid
import warnings
from datetime import datetime
from typing import Optional

import cloudinary
import cloudinary.uploader
import cloudinary.utils
import firebase_admin
from firebase_admin import storage
from fastapi import HTTPException, UploadFile
from starlette import status


# Cloudinary Configuration
def configure_cloudinary():
    """Configure Cloudinary with environment variables."""
    try:
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure Cloudinary: {str(e)}"
        )


# PRIMARY STORAGE FUNCTIONS (CLOUDINARY)

async def upload_image(
    file: UploadFile,
    folder: str = "products",
    file_id: Optional[str] = None,
    is_temporary: bool = True
) -> str:
    """
    Upload an image file to Cloudinary.

    Args:
        file: The file to upload
        folder: The folder path within Cloudinary (e.g., 'products', 'brands')
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
        # Configure Cloudinary
        configure_cloudinary()

        # Read file content
        contents = await file.read()

        # Generate a unique filename if not provided
        if not file_id:
            file_id = f"{uuid.uuid4()}"

        # Create the public ID for Cloudinary
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        public_id = f"{folder}/{file_id}_{timestamp}"

        # Prepare upload options
        upload_options = {
            "public_id": public_id,
            "folder": folder,
            "resource_type": "image",
            "quality": "auto:eco", # Automatically optimize quality
        }

        # Add tags for temporary uploads
        if is_temporary:
            upload_options["tags"] = ["temporary", f"uploaded_{timestamp}"]

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            **upload_options
        )

        return result.get("secure_url")

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
    Delete an image from Cloudinary using its public URL.

    Args:
        url: The public URL of the image to delete

    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        configure_cloudinary()

        if not url:
            return False

        # Extract public_id from Cloudinary URL
        # URL format: https://res.cloudinary.com/CLOUD_NAME/image/upload/v1234567890/folder/file_id.ext
        if "cloudinary.com" not in url:
            return False

        # Get the public_id from the URL
        url_parts = url.split("/")
        if len(url_parts) < 7:
            return False

        # Find the version part and get everything after it
        version_index = -1
        for i, part in enumerate(url_parts):
            if part.startswith("v") and part[1:].isdigit():
                version_index = i
                break

        if version_index == -1:
            return False

        # Get public_id (everything after version, without file extension)
        public_id_with_ext = "/".join(url_parts[version_index + 1:])
        public_id = os.path.splitext(public_id_with_ext)[0]

        # Delete from Cloudinary
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"

    except Exception as e:
        print(f"Error deleting image: {str(e)}")
        return False


async def mark_image_permanent(url: str) -> bool:
    """
    Mark an uploaded image as permanent (not temporary) by removing temporary tags.

    Args:
        url: The public URL of the image

    Returns:
        True if marking was successful, False otherwise
    """
    try:
        configure_cloudinary()

        if not url:
            return False

        # Extract public_id from URL (same logic as delete_image_by_url)
        if "cloudinary.com" not in url:
            return False

        url_parts = url.split("/")
        if len(url_parts) < 7:
            return False

        version_index = -1
        for i, part in enumerate(url_parts):
            if part.startswith("v") and part[1:].isdigit():
                version_index = i
                break

        if version_index == -1:
            return False

        public_id_with_ext = "/".join(url_parts[version_index + 1:])
        public_id = os.path.splitext(public_id_with_ext)[0]

        # Remove temporary tags
        result = cloudinary.uploader.remove_tag("temporary", [public_id])
        return result.get("public_ids", []) != []

    except Exception as e:
        print(f"Error marking image as permanent: {str(e)}")
        return False


async def cleanup_temporary_images(hours_threshold: int = 24):
    """
    Clean up temporary images that are older than the specified threshold.

    Args:
        hours_threshold: Number of hours after which temporary images should be deleted
    """
    try:
        configure_cloudinary()

        # Calculate the timestamp threshold
        current_time = datetime.now()
        threshold_timestamp = current_time.timestamp() - (hours_threshold * 3600)
        threshold_datetime = datetime.fromtimestamp(threshold_timestamp)
        threshold_str = threshold_datetime.strftime("%Y%m%d%H%M%S")

        # Search for images with temporary tag
        result = cloudinary.Search().expression(
            f"tags=temporary AND uploaded_at<{threshold_str}"
        ).sort_by([{"created_at": "desc"}]).max_results(500).execute()

        # Delete old temporary images
        for resource in result.get("resources", []):
            try:
                public_id = resource.get("public_id")
                if public_id:
                    delete_result = cloudinary.uploader.destroy(public_id)
                    if delete_result.get("result") == "ok":
                        print(f"Deleted temporary image: {public_id}")
            except Exception as e:
                print(f"Error deleting temporary image {public_id}: {str(e)}")

    except Exception as e:
        print(f"Error during temporary image cleanup: {str(e)}")


# DEPRECATED FIREBASE STORAGE FUNCTIONS
# These functions are kept for backward compatibility but should not be used for new code

def get_storage_bucket():
    """
    DEPRECATED: Get the Firebase Storage bucket instance.
    Use Cloudinary functions instead.
    """
    warnings.warn(
        "Firebase Storage functions are deprecated. Use Cloudinary functions instead.",
        DeprecationWarning,
        stacklevel=2
    )

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


async def upload_image_firebase_deprecated(
    file: UploadFile,
    folder: str = "products",
    file_id: Optional[str] = None,
    is_temporary: bool = True
) -> str:
    """
    DEPRECATED: Upload an image file to Firebase Storage.
    Use upload_image() which now uses Cloudinary instead.
    """
    warnings.warn(
        "upload_image_firebase_deprecated is deprecated. Use upload_image() which now uses Cloudinary.",
        DeprecationWarning,
        stacklevel=2
    )

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

        blob.upload_from_string(
            contents,
            content_type=content_type
        )

        # Set metadata after upload
        if metadata:
            blob.metadata = metadata
            blob.patch()

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


async def delete_image_by_url_firebase_deprecated(url: str) -> bool:
    """
    DEPRECATED: Delete an image from Firebase Storage using its public URL.
    Use delete_image_by_url() which now uses Cloudinary instead.
    """
    warnings.warn(
        "delete_image_by_url_firebase_deprecated is deprecated. Use delete_image_by_url() which now uses Cloudinary.",
        DeprecationWarning,
        stacklevel=2
    )
    try:
        bucket = get_storage_bucket()

        # Extract the blob path from URL
        if not url:
            return False

        # Parse URL to get blob name
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


async def mark_image_permanent_firebase_deprecated(url: str) -> bool:
    """
    DEPRECATED: Mark an uploaded image as permanent (not temporary) in Firebase Storage.
    Use mark_image_permanent() which now uses Cloudinary instead.
    """
    warnings.warn(
        "mark_image_permanent_firebase_deprecated is deprecated. Use mark_image_permanent() which now uses Cloudinary.",
        DeprecationWarning,
        stacklevel=2
    )
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


async def cleanup_temporary_images_firebase_deprecated(hours_threshold: int = 24):
    """
    DEPRECATED: Clean up temporary images in Firebase Storage.
    Use cleanup_temporary_images() which now uses Cloudinary instead.
    """
    warnings.warn(
        "cleanup_temporary_images_firebase_deprecated is deprecated. Use cleanup_temporary_images() which now uses Cloudinary.",
        DeprecationWarning,
        stacklevel=2
    )
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
