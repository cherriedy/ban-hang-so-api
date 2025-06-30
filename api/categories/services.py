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

        category_items = []
        for doc in categories_docs:
            category_data = doc.to_dict()
            category_data['id'] = doc.id
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
