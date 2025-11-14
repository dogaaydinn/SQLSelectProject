"""
Base Repository Pattern
Provides abstract base class for data access layer
"""

from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload

from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.
    Implements repository pattern to abstract database access.
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize repository with model and database session.

        Args:
            model: SQLAlchemy model class
            db: Async database session
        """
        self.model = model
        self.db = db

    async def get_by_id(
        self,
        id_value: Any,
        id_field: str = "id",
        include_deleted: bool = False,
        relationships: Optional[List[str]] = None,
    ) -> Optional[ModelType]:
        """
        Get entity by ID with optional relationship loading.

        Args:
            id_value: ID value to search for
            id_field: Name of ID field (default: "id")
            include_deleted: Include soft-deleted records
            relationships: List of relationship names to eager load

        Returns:
            Model instance or None

        Example:
            employee = await repo.get_by_id(
                12345,
                id_field="emp_no",
                relationships=["salaries", "departments"]
            )
        """
        query = select(self.model).where(getattr(self.model, id_field) == id_value)

        # Exclude soft-deleted by default
        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)

        # Eager load relationships to prevent N+1 queries
        if relationships:
            for rel in relationships:
                if hasattr(self.model, rel):
                    query = query.options(selectinload(getattr(self.model, rel)))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        relationships: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """
        Get all entities with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Include soft-deleted records
            order_by: Field name to order by
            relationships: List of relationships to eager load
            filters: Dictionary of field: value filters

        Returns:
            List of model instances
        """
        query = select(self.model)

        # Apply filters
        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        # Eager load relationships
        if relationships:
            for rel in relationships:
                if hasattr(self.model, rel):
                    query = query.options(selectinload(getattr(self.model, rel)))

        # Order by
        if order_by and hasattr(self.model, order_by):
            query = query.order_by(getattr(self.model, order_by))

        # Pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        include_deleted: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Count total entities matching criteria.

        Args:
            include_deleted: Include soft-deleted records
            filters: Dictionary of field: value filters

        Returns:
            Total count
        """
        query = select(func.count()).select_from(self.model)

        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    query = query.where(getattr(self.model, field) == value)

        result = await self.db.execute(query)
        return result.scalar()

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        Create new entity.

        Args:
            obj_in: Dictionary of field values

        Returns:
            Created model instance
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        id_value: Any,
        obj_in: Dict[str, Any],
        id_field: str = "id",
    ) -> Optional[ModelType]:
        """
        Update existing entity.

        Args:
            id_value: ID value
            obj_in: Dictionary of fields to update
            id_field: Name of ID field

        Returns:
            Updated model instance or None
        """
        # Get existing entity
        db_obj = await self.get_by_id(id_value, id_field)
        if not db_obj:
            return None

        # Update fields
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        id_value: Any,
        id_field: str = "id",
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete entity (soft or hard delete).

        Args:
            id_value: ID value
            id_field: Name of ID field
            soft_delete: Use soft delete if model supports it

        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get_by_id(id_value, id_field, include_deleted=False)
        if not db_obj:
            return False

        if soft_delete and hasattr(db_obj, "is_deleted"):
            db_obj.is_deleted = True
            await self.db.commit()
        else:
            await self.db.delete(db_obj)
            await self.db.commit()

        return True

    async def exists(
        self,
        id_value: Any,
        id_field: str = "id",
        include_deleted: bool = False,
    ) -> bool:
        """
        Check if entity exists.

        Args:
            id_value: ID value
            id_field: Name of ID field
            include_deleted: Include soft-deleted records

        Returns:
            True if exists, False otherwise
        """
        query = select(func.count()).select_from(self.model).where(
            getattr(self.model, id_field) == id_value
        )

        if not include_deleted and hasattr(self.model, "is_deleted"):
            query = query.where(self.model.is_deleted == False)

        result = await self.db.execute(query)
        return result.scalar() > 0

    async def bulk_create(self, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple entities in bulk.

        Args:
            objects: List of dictionaries with field values

        Returns:
            List of created model instances
        """
        db_objs = [self.model(**obj) for obj in objects]
        self.db.add_all(db_objs)
        await self.db.commit()
        for obj in db_objs:
            await self.db.refresh(obj)
        return db_objs

    async def bulk_update(
        self,
        updates: List[Dict[str, Any]],
        id_field: str = "id",
    ) -> int:
        """
        Update multiple entities in bulk.

        Args:
            updates: List of dictionaries with 'id' and fields to update
            id_field: Name of ID field

        Returns:
            Number of updated records
        """
        count = 0
        for update_data in updates:
            id_value = update_data.pop(id_field, None)
            if id_value:
                stmt = (
                    update(self.model)
                    .where(getattr(self.model, id_field) == id_value)
                    .values(**update_data)
                )
                result = await self.db.execute(stmt)
                count += result.rowcount

        await self.db.commit()
        return count
