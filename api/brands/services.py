"""
Service functions for brand management operations.
Handles database interactions for brands including CRUD operations.
"""

from fastapi import HTTPException
from firebase_admin import firestore
from typing import List, Optional

from api.brands.schemas import BrandInDB, BrandsData
from api.common.utils import generate_default_thumbnail


def get_firestore_client():
    return firestore.client()


def determine_thumbnail_url(image_urls: List[str], brand_name: str) -> str:
    """
    Determine the thumbnail URL based on the list of image URLs.

    Args:
        image_urls: List of image URLs
        brand_name: Brand name for generating default thumbnail

    Returns:
        str: Thumbnail URL (first image or default)
    """
    if image_urls and len(image_urls) > 0:
        return image_urls[0]
    else:
        return generate_default_thumbnail(brand_name)


def should_update_thumbnail(existing_image_urls: List[str], new_image_urls: List[str]) -> bool:
    """
    Check if thumbnail should be updated based on changes to image URLs.

    Args:
        existing_image_urls: Current list of image URLs
        new_image_urls: New list of image URLs

    Returns:
        bool: True if thumbnail should be updated
    """
    # If either list is empty but the other isn't, update thumbnail
    if not existing_image_urls and new_image_urls:
        return True
    if existing_image_urls and not new_image_urls:
        return True

    # If both lists have items, check if first image changed
    if existing_image_urls and new_image_urls:
        return existing_image_urls[0] != new_image_urls[0]

    return False


async def count_products_by_brand(brand_id: str, store_id: str) -> int:
    """
    Count the number of products that belong to a specific brand.

    Args:
        brand_id: The ID of the brand
        store_id: The ID of the store

    Returns:
        int: Number of products in the brand
    """
    try:
        db = get_firestore_client()
        products_ref = db.collection('products').where('storeId', '==', store_id).where('brand.id', '==', brand_id)
        count_query = products_ref.count()
        count_result = count_query.get()
        return count_result[0][0].value
    except Exception:
        return 0


async def get_brands(store_id: str, limit: int = 100, offset: int = 0,
                    sort_by: str = "createdAt", sort_order: str = "desc") -> BrandsData:
    """
    Service function to retrieve brands with pagination and sorting for a specific store.

    Args:
        store_id: The ID of the store to retrieve brands from
        limit: Maximum number of brands to return
        offset: Number of brands to skip
        sort_by: Field to sort by
        sort_order: Sort direction ('asc' or 'desc')

    Returns:
        BrandsData object containing the paginated brands

    Raises:
        HTTPException: If errors occur during retrieval
    """
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        brands_ref = db.collection('brands').where('storeId', '==', store_id)

        # Count total brands for pagination info
        total_query = brands_ref.count()
        total = total_query.get()[0][0].value

        # Get brands with pagination
        query = brands_ref

        # Handle sorting with fallback for missing indexes
        try:
            if sort_by and sort_by != "createdAt":
                direction = "DESCENDING" if sort_order and sort_order.lower().startswith("desc") else "ASCENDING"
                query = query.order_by(sort_by, direction=direction)
        except Exception:
            # If ordering fails due to missing index, proceed without ordering
            pass

        if offset > 0:
            query = query.offset(offset)

        query = query.limit(limit)
        brands_docs = query.get()

        # Get all products for the store in one query
        products_ref = db.collection('products').where('storeId', '==', store_id)
        products_docs = products_ref.get()
        brand_product_counts = {}
        for product_doc in products_docs:
            product = product_doc.to_dict()
            brand_id = product.get('brand', {}).get('id')
            if brand_id:
                brand_product_counts[brand_id] = brand_product_counts.get(brand_id, 0) + 1

        brand_items = []
        for doc in brands_docs:
            brand_data = doc.to_dict()
            brand_data['id'] = doc.id

            # Handle backwards compatibility for existing brands
            if 'imageUrls' not in brand_data:
                # If old imageUrl field exists, convert to imageUrls list
                if 'imageUrl' in brand_data and brand_data['imageUrl']:
                    brand_data['imageUrls'] = [brand_data['imageUrl']]
                else:
                    brand_data['imageUrls'] = []

            # Generate thumbnailUrl if missing
            if 'thumbnailUrl' not in brand_data:
                brand_data['thumbnailUrl'] = determine_thumbnail_url(
                    brand_data['imageUrls'],
                    brand_data.get('name', '')
                )

            # Use precomputed product count
            brand_data['productCount'] = brand_product_counts.get(doc.id, 0)
            brand_items.append(BrandInDB(**brand_data))

        # If we couldn't order in the query, sort in memory
        if sort_by == "createdAt":
            reverse_sort = sort_order and sort_order.lower().startswith("desc")
            brand_items.sort(
                key=lambda x: getattr(x, sort_by, ""),
                reverse=reverse_sort
            )

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return BrandsData(
            items=brand_items,
            total=total,
            page=page,
            size=limit,
            pages=pages
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def get_brand_by_id(brand_id: str, store_id: str) -> BrandInDB:
    """
    Service function to retrieve a single brand by ID within a specific store.

    Args:
        brand_id: The unique identifier of the brand
        store_id: The ID of the store the brand belongs to

    Returns:
        BrandInDB object containing the brand data

    Raises:
        HTTPException: If brand is not found or other errors occur
    """
    if not brand_id:
        raise HTTPException(
            status_code=400,
            detail="Missing brand ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        brands_ref = db.collection('brands')
        doc_ref = brands_ref.document(brand_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Brand not found"
            )

        brand_data = doc.to_dict()

        # Verify the brand belongs to the specified store
        if brand_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Brand not found in the specified store"
            )

        brand_data['id'] = doc.id

        # Handle backwards compatibility for existing brands
        if 'imageUrls' not in brand_data:
            # If old imageUrl field exists, convert to imageUrls list
            if 'imageUrl' in brand_data and brand_data['imageUrl']:
                brand_data['imageUrls'] = [brand_data['imageUrl']]
            else:
                brand_data['imageUrls'] = []

        # Generate thumbnailUrl if missing
        if 'thumbnailUrl' not in brand_data:
            brand_data['thumbnailUrl'] = determine_thumbnail_url(
                brand_data['imageUrls'],
                brand_data.get('name', '')
            )

        # Add product count for this brand
        product_count = await count_products_by_brand(brand_id, store_id)
        brand_data['productCount'] = product_count

        return BrandInDB(**brand_data)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def create_brand(brand_data: dict, store_id: str) -> BrandInDB:
    """
    Service function to create a new brand in a specific store.

    Args:
        brand_data: The brand data to create (contains storeId from API)
        store_id: The ID of the store to create the brand in

    Returns:
        BrandInDB object containing the created brand data

    Raises:
        HTTPException: If errors occur during creation
    """
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()

        # Verify store exists
        store_ref = db.collection('stores').document(store_id)
        store_doc = store_ref.get()
        if not store_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Store with ID {store_id} not found"
            )

        # Set storeId field for database
        if 'storeId' not in brand_data:
            brand_data['storeId'] = store_id

        # Verify the provided storeId matches the authenticated store
        if brand_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=400,
                detail="Brand storeId must match the authenticated store"
            )

        # Check if brand name already exists in this store
        existing_brands = db.collection('brands').where('storeId', '==', store_id).where('name', '==', brand_data['name']).get()
        if existing_brands:
            raise HTTPException(
                status_code=400,
                detail="Brand name already exists in this store"
            )

        # Handle imageUrls and thumbnailUrl
        image_urls = brand_data.get('imageUrls', [])
        if not image_urls:
            image_urls = []

        brand_data['imageUrls'] = image_urls
        brand_data['thumbnailUrl'] = determine_thumbnail_url(image_urls, brand_data['name'])

        brands_ref = db.collection('brands')

        brand_data['createdAt'] = firestore.firestore.SERVER_TIMESTAMP
        brand_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP

        # Create new document
        new_brand_ref = brands_ref.document()
        new_brand_ref.set(brand_data)

        # Retrieve the created brand to return
        created_brand = new_brand_ref.get().to_dict()
        created_brand['id'] = new_brand_ref.id
        created_brand['productCount'] = 0  # New brands start with 0 products

        return BrandInDB(**created_brand)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def update_brand(brand_id: str, brand_data: dict, store_id: str) -> BrandInDB:
    """
    Service function to update an existing brand within a specific store.

    Args:
        brand_id: The unique identifier of the brand to update
        brand_data: The brand data to update
        store_id: The ID of the store the brand belongs to

    Returns:
        BrandInDB object containing the updated brand data

    Raises:
        HTTPException: If brand is not found or other errors occur
    """
    if not brand_id:
        raise HTTPException(
            status_code=400,
            detail="Missing brand ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        brands_ref = db.collection('brands')
        brand_ref = brands_ref.document(brand_id)
        brand = brand_ref.get()

        if not brand.exists:
            raise HTTPException(
                status_code=404,
                detail="Brand not found"
            )

        existing_brand_data = brand.to_dict()

        # Verify the brand belongs to the specified store
        if existing_brand_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Brand not found in the specified store"
            )

        update_data = brand_data.copy()

        # Prevent changing storeId
        if 'storeId' in update_data:
            update_data.pop('storeId')

        # Check if new name already exists in this store (if name is being updated)
        if 'name' in update_data and update_data['name'] != existing_brand_data.get('name'):
            existing_brands = db.collection('brands').where('storeId', '==', store_id).where('name', '==', update_data['name']).get()
            if existing_brands:
                raise HTTPException(
                    status_code=400,
                    detail="Brand name already exists in this store"
                )

        # Handle imageUrls and thumbnailUrl updates
        existing_image_urls = existing_brand_data.get('imageUrls', [])
        new_image_urls = update_data.get('imageUrls')

        # Use current brand name for thumbnail generation, or updated name if provided
        brand_name = update_data.get('name', existing_brand_data.get('name'))

        if new_image_urls is not None:
            # Client provided imageUrls (could be empty list or list with items)
            if not new_image_urls:
                # Empty list - remove all images and set default thumbnail
                update_data['imageUrls'] = []
                update_data['thumbnailUrl'] = generate_default_thumbnail(brand_name)
            else:
                # Non-empty list - check if first image changed
                if should_update_thumbnail(existing_image_urls, new_image_urls):
                    update_data['thumbnailUrl'] = determine_thumbnail_url(new_image_urls, brand_name)
        elif 'name' in update_data and update_data['name'] != existing_brand_data.get('name'):
            # If only name changed and no imageUrls provided, update thumbnail if using default
            if not existing_image_urls:
                update_data['thumbnailUrl'] = generate_default_thumbnail(brand_name)

        # Update only provided fields
        update_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP
        brand_ref.update(update_data)

        # Return updated brand
        updated_brand_dict = brand_ref.get().to_dict()
        if updated_brand_dict is None:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated brand")

        updated_brand_dict['id'] = brand_id

        # Add product count for this brand
        product_count = await count_products_by_brand(brand_id, store_id)
        updated_brand_dict['productCount'] = product_count

        # After updating the brand, update all products referencing this brand if name or thumbnail changed
        updated_fields = {}
        if 'name' in update_data and update_data['name'] != existing_brand_data.get('name'):
            updated_fields['brand.name'] = update_data['name']
        if 'thumbnailUrl' in update_data and update_data['thumbnailUrl'] != existing_brand_data.get('thumbnailUrl'):
            updated_fields['brand.thumbnailUrl'] = update_data['thumbnailUrl']
        if updated_fields:
            # Use batch to update all products with this brand id
            products_ref = db.collection('products').where('storeId', '==', store_id).where('brand.id', '==', brand_id)
            products = products_ref.get()
            batch = db.batch()
            for product in products:
                product_ref = product.reference
                batch.update(product_ref, updated_fields)
            batch.commit()

        return BrandInDB(**updated_brand_dict)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def delete_brand(brand_id: str, store_id: str) -> bool:
    """
    Service function to delete a brand by ID within a specific store.

    Args:
        brand_id: The unique identifier of the brand to delete
        store_id: The ID of the store the brand belongs to

    Returns:
        bool: True if the brand was deleted successfully

    Raises:
        HTTPException: If brand is not found or other errors occur
    """
    if not brand_id:
        raise HTTPException(
            status_code=400,
            detail="Missing brand ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        brands_ref = db.collection('brands')
        brand_ref = brands_ref.document(brand_id)
        brand = brand_ref.get()

        if not brand.exists:
            raise HTTPException(
                status_code=404,
                detail="Brand not found"
            )

        brand_data = brand.to_dict()

        # Verify the brand belongs to the specified store
        if brand_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Brand not found in the specified store"
            )

        # Check if brand is being used by any products
        products_using_brand = db.collection('products').where('brand.id', '==', brand_id).limit(1).get()
        if products_using_brand:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete brand that is being used by products"
            )

        # Delete the brand
        brand_ref.delete()
        return True

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )
