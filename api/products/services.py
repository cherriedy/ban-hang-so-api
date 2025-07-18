import urllib.parse
from typing import List

from fastapi import HTTPException
from firebase_admin import firestore

from api.common.storage import mark_image_permanent
from api.products.schemas import ProductInDB, ProductsData


def get_firestore_client():
    return firestore.client()


def generate_default_thumbnail(product_name: str) -> str:
    """
    Generate a default thumbnail URL for a product when no images are provided.
    Similar to customer avatar logic but for products.
    """
    encoded_name = urllib.parse.quote(product_name)
    encoded_colors = urllib.parse.quote("f0f0f0,e0e0e0,d0d0d0")
    return f"https://api.dicebear.com/9.x/initials/png?seed={encoded_name}&backgroundColor={encoded_colors}"


def process_product_images(image_urls: List[str], product_name: str) -> tuple[List[str], str]:
    """
    Process product images and determine thumbnail URL.

    Args:
        image_urls: List of image URLs
        product_name: Name of the product for default thumbnail generation

    Returns:
        Tuple of (processed_image_urls, thumbnail_url)
    """
    if not image_urls:
        # Empty list - use default thumbnail
        return [], generate_default_thumbnail(product_name)

    # Filter out empty strings and None values
    processed_urls = [url for url in image_urls if url and url.strip()]

    if not processed_urls:
        # All URLs were empty - use default thumbnail
        return [], generate_default_thumbnail(product_name)

    # Use first image as thumbnail
    thumbnail_url = processed_urls[0]

    return processed_urls, thumbnail_url


async def get_products(store_id: str, limit: int = 100, offset: int = 0,
                       sort_by: str = "createdAt", sort_order: str = "desc") -> ProductsData:
    """
    Service function to retrieve products with pagination and sorting for a specific store.

    Args:
        store_id: The ID of the store to retrieve products from
        limit: Maximum number of products to return
        offset: Number of products to skip
        sort_by: Field to sort by
        sort_order: Sort direction ('asc' or 'desc')

    Returns:
        ProductsData object containing the paginated products

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
        products_ref = db.collection('products').where('storeId', '==', store_id)

        # Count total products for pagination info
        total_query = products_ref.count()
        total = total_query.get()[0][0].value

        # Get products with pagination
        direction = "DESCENDING"
        if sort_order and sort_order.lower().startswith("asc"):
            direction = "ASCENDING"

        query = products_ref.order_by(sort_by, direction=direction)

        if offset > 0:
            query = query.offset(offset)

        query = query.limit(limit)
        products_docs = query.get()

        product_items = []
        for doc in products_docs:
            product_data = doc.to_dict()
            product_data['id'] = doc.id
            product_items.append(ProductInDB(**product_data))

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return ProductsData(
            items=product_items,
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


async def get_product_by_id(product_id: str, store_id: str) -> ProductInDB:
    """
    Service function to retrieve a single product by ID within a specific store.

    Args:
        product_id: The unique identifier of the product
        store_id: The ID of the store the product belongs to

    Returns:
        ProductInDB object containing the product data

    Raises:
        HTTPException: If product is not found or other errors occur
    """
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Missing product ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products')
        doc_ref = products_ref.document(product_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        product_data = doc.to_dict()

        # Verify the product belongs to the specified store
        if product_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Product not found in the specified store"
            )

        product_data['id'] = doc.id
        return ProductInDB(**product_data)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def create_product(product_data: dict, store_id: str) -> ProductInDB:
    """
    Service function to create a new product in a specific store.

    Args:
        product_data: The product data to create (contains storeId from API)
        store_id: The ID of the store to create the product in

    Returns:
        ProductInDB object containing the created product data

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

        # Set storeId field for database (no mapping needed since database also uses storeId)
        if 'storeId' not in product_data:
            product_data['storeId'] = store_id

        # Fetch and replace brand data if provided
        if 'brand' in product_data and product_data.get('brand'):
            brand_id = product_data['brand']['id']
            brand_ref = db.collection('brands').document(brand_id)
            brand_doc = brand_ref.get()
            if not brand_doc.exists:
                raise HTTPException(status_code=404, detail=f"Brand with ID {brand_id} not found")

            brand_data = brand_doc.to_dict()
            # Verify brand belongs to the same store
            if brand_data.get('storeId') != store_id:
                raise HTTPException(status_code=400, detail=f"Brand does not belong to store {store_id}")
            # Preserve the brand ID
            brand_data['id'] = brand_id
            product_data['brand'] = brand_data

        # Fetch and replace category data if provided
        if 'category' in product_data and product_data.get('category'):
            category_id = product_data['category']['id']
            category_ref = db.collection('categories').document(category_id)
            category_doc = category_ref.get()
            if not category_doc.exists:
                raise HTTPException(status_code=404, detail=f"Category with ID {category_id} not found")

            category_data = category_doc.to_dict()
            # Verify category belongs to the same store
            if category_data.get('storeId') != store_id:
                raise HTTPException(status_code=400, detail=f"Category does not belong to store {store_id}")
            # Preserve the category ID
            category_data['id'] = category_id
            product_data['category'] = category_data

        products_ref = db.collection('products')

        product_data['createdAt'] = firestore.firestore.SERVER_TIMESTAMP
        product_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP

        # Create new document
        new_product_ref = products_ref.document()
        new_product_ref.set(product_data)

        # Retrieve the created product to return
        created_product = new_product_ref.get().to_dict()
        created_product['id'] = new_product_ref.id

        # Mark uploaded image as permanent if one was provided
        if product_data.get('avatarUrl'):
            await mark_image_permanent(product_data['avatarUrl'])

        return ProductInDB(**created_product)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def search_products(query: str, store_id: str, limit: int = 100, offset: int = 0) -> ProductsData:
    """
    Service function to search for products by name, brand, category, description or SKU with pagination within a specific store.

    Args:
        query: The search query
        store_id: The ID of the store to search products in
        limit: Maximum number of products to return
        offset: Number of products to skip

    Returns:
        ProductsData object containing the paginated search results

    Raises:
        HTTPException: If errors occur during search
    """
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products').where('storeId', '==', store_id)

        # If query is empty, return all products for the store instead of searching
        if not query or query.strip() == "":
            return await get_products(store_id=store_id, limit=limit, offset=offset)

        query = query.lower().strip()  # Normalize query for case-insensitive search

        # Dictionary to store all found products with their relevance score
        products = {}

        # Fetch all products for the store and perform client-side filtering
        # This approach allows searching for substrings anywhere in the fields
        all_products = products_ref.get()

        for doc in all_products:
            product_data = doc.to_dict()
            product_data['id'] = doc.id

            # Skip products that don't have required fields
            if not product_data:
                continue

            # Initialize relevance score
            relevance_score = 0

            # Check name field (highest priority)
            name = product_data.get('name', '').lower()
            if query in name:
                # Higher score for exact matches
                if name == query:
                    relevance_score += 15
                # Higher score if query is at the beginning of the name
                elif name.startswith(query):
                    relevance_score += 12
                # Standard score for substring matches
                else:
                    relevance_score += 10

            # Check SKU field (high priority)
            sku = product_data.get('sku', '').lower()
            if query in sku:
                relevance_score += 8

            # Check brand name (medium priority)
            brand = product_data.get('brand', {})
            if isinstance(brand, dict) and query in brand.get('name', '').lower():
                relevance_score += 5

            # Check category name (medium-low priority)
            category = product_data.get('category', {})
            if isinstance(category, dict) and query in category.get('name', '').lower():
                relevance_score += 3

            # Check description (lowest priority)
            description = product_data.get('description', '').lower()
            if query in description:
                relevance_score += 1

            # If this product matches the query in any field, add it to the results
            if relevance_score > 0:
                products[doc.id] = {
                    'product': ProductInDB(**product_data),
                    'relevance': relevance_score
                }

        # Sort results by relevance score (highest first)
        sorted_products = sorted(
            list(products.values()),
            key=lambda item: item['relevance'],
            reverse=True
        )

        # Extract just the product objects for the response
        all_results = [item['product'] for item in sorted_products]

        total = len(all_results)

        # Apply pagination
        paginated_results = all_results[offset:offset + limit]

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return ProductsData(
            items=paginated_results,
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


async def update_product(product_id: str, product_data: dict, store_id: str) -> ProductInDB:
    """
    Service function to update an existing product within a specific store.

    Args:
        product_id: The unique identifier of the product to update
        product_data: The product data to update (may contain storeId from API)
        store_id: The ID of the store the product belongs to

    Returns:
        ProductInDB object containing the updated product data

    Raises:
        HTTPException: If product is not found or other errors occur
    """
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Missing product ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products')
        product_ref = products_ref.document(product_id)
        product = product_ref.get()

        if not product.exists:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        existing_product_data = product.to_dict()

        # Verify the product belongs to the specified store
        if existing_product_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Product not found in the specified store"
            )

        update_data = product_data.copy()

        # Prevent changing storeId if present in update data
        if 'storeId' in update_data:
            if update_data['storeId'] != store_id:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot change storeId of existing product"
                )
            # Remove storeId from update_data as we don't want to update it
            update_data.pop('storeId')

        # Ensure store_id cannot be changed
        if 'store_id' in update_data and update_data['store_id'] != store_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot change store_id of existing product"
            )

        # Fetch and replace brand data if provided
        if 'brand' in update_data:
            if update_data.get('brand'):
                brand_id = update_data['brand']['id']
                brand_ref = db.collection('brands').document(brand_id)
                brand_doc = brand_ref.get()
                if not brand_doc.exists:
                    raise HTTPException(status_code=404, detail=f"Brand with ID {brand_id} not found")

                brand_data = brand_doc.to_dict()
                # Verify brand belongs to the same store
                if brand_data.get('storeId') != store_id:
                    raise HTTPException(status_code=400, detail=f"Brand does not belong to store {store_id}")
                # Preserve the brand ID
                brand_data['id'] = brand_id
                update_data['brand'] = brand_data
            else:  # handle case where brand is set to null
                update_data['brand'] = None

        # Fetch and replace category data if provided
        if 'category' in update_data:
            if update_data.get('category'):
                category_id = update_data['category']['id']
                category_ref = db.collection('categories').document(category_id)
                category_doc = category_ref.get()
                if not category_doc.exists:
                    raise HTTPException(status_code=404, detail=f"Category with ID {category_id} not found")

                category_data = category_doc.to_dict()
                # Verify category belongs to the same store
                if category_data.get('storeId') != store_id:
                    raise HTTPException(status_code=400, detail=f"Category does not belong to store {store_id}")
                # Preserve the category ID
                category_data['id'] = category_id
                update_data['category'] = category_data
            else:  # handle case where category is set to null
                update_data['category'] = None

        # --- Handle imageUrls and thumbnail update logic ---
        old_image_urls = existing_product_data.get('imageUrls', [])
        new_image_urls = update_data.get('imageUrls', old_image_urls)
        product_name = update_data.get('name', existing_product_data.get('name', ''))

        # Only update thumbnailUrl if imageUrls changed or if imageUrls is empty
        if new_image_urls != old_image_urls:
            processed_urls, new_thumbnail = process_product_images(new_image_urls, product_name)
            update_data['imageUrls'] = processed_urls
            update_data['thumbnailUrl'] = new_thumbnail
        elif not old_image_urls:
            update_data['thumbnailUrl'] = generate_default_thumbnail(product_name)
        # else: do not update thumbnailUrl if imageUrls unchanged and not empty
        # --- End image/thumbnail logic ---

        # Update only provided fields
        update_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP
        product_ref.update(update_data)

        # Mark uploaded image as permanent if a new one was provided
        if update_data.get('avatarUrl'):
            await mark_image_permanent(update_data['avatarUrl'])

        # Return updated product
        updated_product_dict = product_ref.get().to_dict()
        if updated_product_dict is None:
            # This can happen if the mock is not set up correctly for the second get
            raise HTTPException(status_code=500, detail="Failed to retrieve updated product")

        updated_product_dict['id'] = product_id
        return ProductInDB(**updated_product_dict)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def delete_product(product_id: str, store_id: str) -> bool:
    """
    Service function to delete a product by ID within a specific store.

    Args:
        product_id: The unique identifier of the product to delete
        store_id: The ID of the store the product belongs to

    Returns:
        bool: True if the product was deleted successfully

    Raises:
        HTTPException: If product is not found or other errors occur
    """
    if not product_id:
        raise HTTPException(
            status_code=400,
            detail="Missing product ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        products_ref = db.collection('products')
        product_ref = products_ref.document(product_id)
        product = product_ref.get()

        if not product.exists:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        product_data = product.to_dict()

        # Verify the product belongs to the specified store
        if product_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Product not found in the specified store"
            )

        # Delete the product
        product_ref.delete()
        return True

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )
