from fastapi import Depends
from sqlalchemy.orm import Session

from application.categories.queries.get_categories import GetCategoriesHandler
from infrastructure.database.connection import get_db
from infrastructure.database.repositories.sqlalchemy_category_repository import (
    SQLAlchemyCategoryRepository,
)


def get_categories_handler(db: Session = Depends(get_db)) -> GetCategoriesHandler:
    category_repository = SQLAlchemyCategoryRepository(db)
    return GetCategoriesHandler(category_repository)
