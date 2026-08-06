# main.py
from datetime import datetime, timezone
import logging
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database.session import get_session
from models.product import (
    Category,
    CategoryCreate,
    Product,
    ProductCreate,
    ProductUpdate,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Product Catalog API", version="1.0.0")


# ============================================================
# EXCEPTION HANDLERS
# ============================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "status_code": 422,
            "message": "Validation error",
            "errors": errors,
            "path": request.url.path,
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error(f"Integrity error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": True,
            "status_code": 409,
            "message": "Duplicate entry or constraint violation",
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "status_code": 500,
            "message": "An internal error occurred",
            "path": request.url.path,
        },
    )


# ============================================================
# CATEGORY CRUD
# ============================================================


@app.post(
    "/categories",
    response_model=Category,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category: CategoryCreate, session: Session = Depends(get_session)
):
    """Create a new category"""
    existing = session.exec(
        select(Category).where(Category.name == category.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category already exists",
        )

    db_category = Category.model_validate(category)
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category


@app.get("/categories", response_model=List[Category])
def list_categories(session: Session = Depends(get_session)):
    """List all categories"""
    return session.exec(select(Category)).all()


# ============================================================
# PRODUCT CRUD
# ============================================================


@app.post(
    "/products", response_model=Product, status_code=status.HTTP_201_CREATED
)
def create_product(
    product: ProductCreate, session: Session = Depends(get_session)
):
    """Create a new product"""
    if product.category_id:
        category = session.get(Category, product.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

    db_product = Product.model_validate(product)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product


@app.get("/products", response_model=List[Product])
def list_products(
    skip: int = 0,
    limit: int = 10,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    session: Session = Depends(get_session),
):
    """List products with filters"""
    query = select(Product)
    if category_id:
        query = query.where(Product.category_id == category_id)
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if in_stock is not None:
        if in_stock:
            query = query.where(Product.stock > 0)
        else:
            query = query.where(Product.stock == 0)
    return session.exec(query.offset(skip).limit(limit)).all()


@app.get("/products/search", response_model=List[Product])
def search_products(q: str, session: Session = Depends(get_session)):
    """Search products by name or description"""
    query = select(Product).where(
        (Product.name.contains(q)) | (Product.description.contains(q))
    )
    return session.exec(query).all()


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, session: Session = Depends(get_session)):
    """Get a specific product by ID"""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@app.patch("/products/{product_id}", response_model=Product)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    session: Session = Depends(get_session),
):
    """Partially update a product"""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    product.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, session: Session = Depends(get_session)):
    """Delete a product"""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    session.delete(product)
    session.commit()
    return None