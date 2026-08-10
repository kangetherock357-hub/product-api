
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    email: str

class Category(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class ProductBase(SQLModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    category_id: Optional[int] = None
# 1. Initialize the FastAPI application instance
app = FastAPI(title="Product API")

# Placeholder dependencies (ensure your actual import paths match your project setup)
# from database import get_session
# from auth import get_current_user, User
# from models import Product, ProductCreate, ProductUpdate, Category


# --- PORTFOLIO HOMEPAGE ENDPOINT ---
@app.get("/", response_class=HTMLResponse)
async def portfolio():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Student Portfolio - Backend Assignments</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            .student-info { background: #e8f4fd; padding: 15px; border-radius: 8px; margin: 20px 0; }
            .admission { font-size: 1.2em; color: #2980b9; font-weight: bold; }
            .assignment { margin: 12px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #3498db; }
            .assignment a { color: #0366d6; text-decoration: none; font-weight: 500; }
            .badge { display: inline-block; background: #3498db; color: white; padding: 2px 10px; border-radius: 12px; font-size: 0.8em; margin-right: 10px; }
            .footer { margin-top: 30px; text-align: center; color: #95a5a6; font-size: 0.9em; border-top: 1px solid #ecf0f1; padding-top: 20px; }
        </style>
    </head>
    <body>
    <div class="container">
        <h1>Backend Development Portfolio</h1>
        <div class="student-info">
            <p><strong>Student Name:</strong> [YOUR FULL NAME]</p>
            <p><strong>Admission Number:</strong> <span class="admission">C027-01-XXXX/2024</span></p>
            <p><strong>Email:</strong> [YOUR STUDENT EMAIL] 📧</p>
        </div>
        <h2>Backend Assignments 📝</h2>
        <div class="assignment"><a href="[LESSON 1 GITHUB URL]" target="_blank"><span class="badge">Lesson 1</span> HTTP & Your First API</a></div>
        <div class="assignment"><a href="[LESSON 2 GITHUB URL]" target="_blank"><span class="badge">Lesson 2</span> Docker - Packaging Your API</a></div>
        <div class="assignment"><a href="[LESSON 3 GITHUB URL]" target="_blank"><span class="badge">Lesson 3</span> Routing, Parameters & Validation</a></div>
        <div class="assignment"><a href="[LESSON 4 GITHUB URL]" target="_blank"><span class="badge">Lesson 4</span> PostgreSQL & SQLModel</a></div>
        <div class="assignment"><a href="[LESSON 5 GITHUB URL]" target="_blank"><span class="badge">Lesson 5</span> CRUD Operations</a></div>
        <div class="assignment"><a href="[LESSON 6 GITHUB URL]" target="_blank"><span class="badge">Lesson 6</span> Error Handling & Validation</a></div>
        <div class="assignment"><a href="[LESSON 7 GITHUB URL]" target="_blank"><span class="badge">Lesson 7</span> JWT & Password Hashing</a></div>
        <div class="assignment"><a href="[LESSON 8 GITHUB URL]" target="_blank"><span class="badge">Lesson 8</span> Authorization & Rate Limiting</a></div>
        <div class="assignment"><a href="[LESSON 9 GITHUB URL]" target="_blank"><span class="badge">Lesson 9</span> File Uploads & External APIs</a></div>
        <div class="assignment"><a href="[LESSON 10 GITHUB URL]" target="_blank"><span class="badge">Lesson 10</span> Testing & Deployment</a></div>
        <div class="footer"><p>Deployed on Render | Last Updated: August 2026</p></div>
    </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# --- PRODUCT ENDPOINTS ---

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


# PLACED BEFORE /{product_id} TO PREVENT ROUTE MATCHING CONFLICTS
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

    product.updated_at = datetime.now(timezone.utc)
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