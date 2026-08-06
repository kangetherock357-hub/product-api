import logging
import os
import platform
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from typing import Annotated

import psutil
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from auth import (
    create_access_token,
    get_current_admin,
    get_current_user,
    hash_password,
    verify_password,
)
from database.session import get_session, init_db
from models.product import (
    Category,
    CategoryCreate,
    Product,
    ProductCreate,
    ProductUpdate,
)
from models.user import User, UserCreate, UserResponse

# ============================================================
# LOGGING & CONFIGURATION
# ============================================================

LOG_FILE = os.getenv("LOG_FILE", "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=5),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

start_time = time.time()


# ============================================================
# LIFESPAN & APPLICATION SETUP
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code execution
    init_db()
    yield
    # Shutdown code execution (if needed)


app = FastAPI(
    title="CloudDeploy Product API",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# MIDDLEWARE
# ============================================================


@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_start = time.time()
    response = await call_next(request)
    duration = time.time() - req_start
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {duration:.3f}s"
    )
    return response


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
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
# AUTHENTICATION ENDPOINTS
# ============================================================


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, session: Annotated[Session, Depends(get_session)]):
    """Register a new user account"""
    if session.exec(select(User).where(User.username == user_in.username)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/login")
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)],
):
    """Authenticate user and return JWT access token"""
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


# ============================================================
# CATEGORY CRUD
# ============================================================


@app.post(
    "/categories",
    response_model=Category,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    category: CategoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
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


@app.get("/categories", response_model=list[Category])
def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """List all categories"""
    return session.exec(select(Category)).all()


# ============================================================
# PRODUCT CRUD
# ============================================================


@app.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Create a new product"""
    if product.price < 0 or product.stock < 0 or not product.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product payload values",
        )

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


@app.get("/products", response_model=list[Product])
def list_products(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    skip: int = 0,
    limit: int = 10,
    category_id: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    in_stock: bool | None = None,
):
    """List products with optional search filters"""
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


@app.get("/products/search", response_model=list[Product])
def search_products(
    q: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Search products by name or description"""
    query = select(Product).where(
        (Product.name.contains(q)) | (Product.description.contains(q))
    )
    return session.exec(query).all()


@app.get("/products/{product_id}", response_model=Product)
def get_product(
    product_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
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
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
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

    product.updated_at = datetime.now(UTC)
    session.commit()
    session.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
):
    """Delete a product"""
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    session.delete(product)
    session.commit()


# ============================================================
# SYSTEM HEALTH & MONITORING ENDPOINTS
# ============================================================


@app.get("/health")
def health_check():
    """Application uptime and system status health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "version": "1.0.0",
        "uptime": time.time() - start_time,
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
    }


@app.get("/metrics")
def get_metrics(
    current_user: Annotated[User, Depends(get_current_admin)],
):
    """System utilization metrics (Admin access required)"""
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage("/").percent,
    }
