"""
Service functions for category management operations.
Handles database interactions for categories including CRUD operations.
"""

from fastapi import HTTPException
from firebase_admin import firestore

from api.categories.schemas import CategoryInDB, CategoriesData


def get_firestore_client():
    return firestore.client()


async def get_categories(store_id: str, limit: int = 100, offset: int = 0,
                        sort_by: str = "createdAt", sort_order: str = "desc") -> CategoriesData:
    """
    Service function to retrieve categories with pagination and sorting for a specific store.

    Args:
        store_id: The ID of the store to retrieve categories from
        limit: Maximum number of categories to return
        offset: Number of categories to skip
        sort_by: Field to sort by
        sort_order: Sort direction ('asc' or 'desc')

    Returns:
        CategoriesData object containing the paginated categories

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
        categories_ref = db.collection('categories').where('storeId', '==', store_id)

        # Count total categories for pagination info
        total_query = categories_ref.count()
        total = total_query.get()[0][0].value

        # Get categories with pagination
        query = categories_ref

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
        categories_docs = query.get()

        # Get all products for the store in one query
        products_ref = db.collection('products').where('storeId', '==', store_id)
        products_docs = products_ref.get()
        category_product_counts = {}
        for product_doc in products_docs:
            product = product_doc.to_dict()
            category_id = product.get('category', {}).get('id')
            if category_id:
                category_product_counts[category_id] = category_product_counts.get(category_id, 0) + 1

        category_items = []
        for doc in categories_docs:
            category_data = doc.to_dict()
            category_data['id'] = doc.id
            # Use precomputed product count
            category_data['productCount'] = category_product_counts.get(doc.id, 0)
            category_items.append(CategoryInDB(**category_data))

        # If we couldn't order in the query, sort in memory
        if sort_by == "createdAt":
            reverse_sort = sort_order and sort_order.lower().startswith("desc")
            category_items.sort(
                key=lambda x: getattr(x, sort_by, ""),
                reverse=reverse_sort
            )

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return CategoriesData(
            items=category_items,
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


async def get_category_by_id(category_id: str, store_id: str) -> CategoryInDB:
    """
    Service function to retrieve a single category by ID within a specific store.

    Args:
        category_id: The unique identifier of the category
        store_id: The ID of the store the category belongs to

    Returns:
        CategoryInDB object containing the category data

    Raises:
        HTTPException: If category is not found or other errors occur
    """
    if not category_id:
        raise HTTPException(
            status_code=400,
            detail="Missing category ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        categories_ref = db.collection('categories')
        doc_ref = categories_ref.document(category_id)
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        category_data = doc.to_dict()

        # Verify the category belongs to the specified store
        if category_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Category not found in the specified store"
            )

        category_data['id'] = doc.id

        # Add product count for this category
        product_count = await count_products_by_category(category_id, store_id)
        category_data['productCount'] = product_count

        return CategoryInDB(**category_data)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def create_category(category_data: dict, store_id: str) -> CategoryInDB:
    """
    Service function to create a new category in a specific store.

    Args:
        category_data: The category data to create (contains storeId from API)
        store_id: The ID of the store to create the category in

    Returns:
        CategoryInDB object containing the created category data

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
        if 'storeId' not in category_data:
            category_data['storeId'] = store_id

        # Verify the provided storeId matches the authenticated store
        if category_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=400,
                detail="Category storeId must match the authenticated store"
            )

        # Check if category name already exists in this store
        existing_categories = db.collection('categories').where('storeId', '==', store_id).where('name', '==', category_data['name']).get()
        if existing_categories:
            raise HTTPException(
                status_code=400,
                detail="Category name already exists in this store"
            )

        categories_ref = db.collection('categories')

        category_data['createdAt'] = firestore.firestore.SERVER_TIMESTAMP
        category_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP

        # Create new document
        new_category_ref = categories_ref.document()
        new_category_ref.set(category_data)

        # Retrieve the created category to return
        created_category = new_category_ref.get().to_dict()
        created_category['id'] = new_category_ref.id

        return CategoryInDB(**created_category)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def update_category(category_id: str, category_data: dict, store_id: str) -> CategoryInDB:
    """
    Service function to update an existing category within a specific store.

    Args:
        category_id: The unique identifier of the category to update
        category_data: The category data to update
        store_id: The ID of the store the category belongs to

    Returns:
        CategoryInDB object containing the updated category data

    Raises:
        HTTPException: If category is not found or other errors occur
    """
    if not category_id:
        raise HTTPException(
            status_code=400,
            detail="Missing category ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        categories_ref = db.collection('categories')
        category_ref = categories_ref.document(category_id)
        category = category_ref.get()

        if not category.exists:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        existing_category_data = category.to_dict()

        # Verify the category belongs to the specified store
        if existing_category_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Category not found in the specified store"
            )

        update_data = category_data.copy()

        # Prevent changing storeId
        if 'storeId' in update_data:
            update_data.pop('storeId')

        # Check if new name already exists in this store (if name is being updated)
        if 'name' in update_data and update_data['name'] != existing_category_data.get('name'):
            existing_categories = db.collection('categories').where('storeId', '==', store_id).where('name', '==', update_data['name']).get()
            if existing_categories:
                raise HTTPException(
                    status_code=400,
                    detail="Category name already exists in this store"
                )

        # Update only provided fields
        update_data['updatedAt'] = firestore.firestore.SERVER_TIMESTAMP
        category_ref.update(update_data)

        # Return updated category
        updated_category_dict = category_ref.get().to_dict()
        if updated_category_dict is None:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated category")

        updated_category_dict['id'] = category_id

        # After updating the category, update all products referencing this category if name or imageUrl changed
        updated_fields = {}
        if 'name' in update_data and update_data['name'] != existing_category_data.get('name'):
            updated_fields['category.name'] = update_data['name']
        if 'imageUrl' in update_data and update_data['imageUrl'] != existing_category_data.get('imageUrl'):
            updated_fields['category.imageUrl'] = update_data['imageUrl']
        if updated_fields:
            # Use batch to update all products with this category id
            products_ref = db.collection('products').where('storeId', '==', store_id).where('category.id', '==', category_id)
            products = products_ref.get()
            batch = db.batch()
            for product in products:
                product_ref = product.reference
                batch.update(product_ref, updated_fields)
            batch.commit()

        return CategoryInDB(**updated_category_dict)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def delete_category(category_id: str, store_id: str) -> bool:
    """
    Service function to delete a category by ID within a specific store.

    Args:
        category_id: The unique identifier of the category to delete
        store_id: The ID of the store the category belongs to

    Returns:
        bool: True if the category was deleted successfully

    Raises:
        HTTPException: If category is not found or other errors occur
    """
    if not category_id:
        raise HTTPException(
            status_code=400,
            detail="Missing category ID parameter"
        )

    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        db = get_firestore_client()
        categories_ref = db.collection('categories')
        category_ref = categories_ref.document(category_id)
        category = category_ref.get()

        if not category.exists:
            raise HTTPException(
                status_code=404,
                detail="Category not found"
            )

        category_data = category.to_dict()

        # Verify the category belongs to the specified store
        if category_data.get('storeId') != store_id:
            raise HTTPException(
                status_code=404,
                detail="Category not found in the specified store"
            )

        # Check if category is being used by any products
        products_using_category = db.collection('products').where('category.id', '==', category_id).limit(1).get()
        if products_using_category:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete category that is being used by products"
            )

        # Delete the category
        category_ref.delete()
        return True

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


async def count_products_by_category(category_id: str, store_id: str) -> int:
    """
    Count the number of products that belong to a specific category.

    Args:
        category_id: The ID of the category
        store_id: The ID of the store

    Returns:
        int: Number of products in the category
    """
    try:
        db = get_firestore_client()
        products_ref = db.collection('products').where('storeId', '==', store_id).where('category.id', '==', category_id)
        count_query = products_ref.count()
        count_result = count_query.get()
        return count_result[0][0].value
    except Exception:
        return 0


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


async def search_categories(query: str, store_id: str, limit: int = 100, offset: int = 0) -> CategoriesData:
    """
    Service function to search for categories by name with pagination within a specific store.

    Args:
        query: The search query
        store_id: The ID of the store to search categories in
        limit: Maximum number of categories to return
        offset: Number of categories to skip

    Returns:
        CategoriesData object containing the paginated search results

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
        categories_ref = db.collection('categories').where('storeId', '==', store_id)

        # If query is empty, return all categories for the store instead of searching
        if not query or query.strip() == "":
            return await get_categories(store_id=store_id, limit=limit, offset=offset)

        query = query.lower().strip()  # Normalize query for case-insensitive search

        # List to store all found categories with their relevance score
        categories = []

        # Fetch all categories for the store and perform client-side filtering
        # This approach allows searching for substrings anywhere in the fields
        all_categories = categories_ref.get()

        for doc in all_categories:
            category_data = doc.to_dict()
            category_data['id'] = doc.id

            # Skip categories that don't have required fields
            if not category_data:
                continue

            # Initialize relevance score
            relevance_score = 0

            # Check name field (main search field for categories)
            name = category_data.get('name', '').lower()
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

            # Only include categories that match the search query
            if relevance_score > 0:
                # Add product count for this category
                product_count = await count_products_by_category(doc.id, store_id)
                category_data['productCount'] = product_count

                categories.append({
                    'data': CategoryInDB(**category_data),
                    'score': relevance_score
                })

        # Sort by relevance score (highest first), then by name for ties
        categories.sort(key=lambda x: (-x['score'], x['data'].name.lower()))

        # Extract just the category data after sorting
        sorted_categories = [item['data'] for item in categories]

        # Apply pagination
        total = len(sorted_categories)
        paginated_categories = sorted_categories[offset:offset + limit]

        page = offset // limit + 1
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return CategoriesData(
            items=paginated_categories,
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
