from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import os
from datetime import datetime

JSON_FILE_PATH = "products.json"
CART_FILE_PATH = "cart.json"
USERS_FILE_PATH = "users.json"
ORDERS_FILE_PATH = "orders.json"

class Product(BaseModel):
    id: int
    name: str
    description: str
    category: str
    price: float
    imageUrl: str

class CartItem(BaseModel):
    productId: int
    quantity: int

class Cart(BaseModel):
    userId: int
    items: List[CartItem]

class User(BaseModel):
    id: int
    name: str
    email: str
    birthDate: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    user: Optional[Dict] = None

class OrderItem(CartItem):
    name: str
    price: float
    imageUrl: str

class Order(BaseModel):
    id: int
    userId: int
    items: List[OrderItem]
    totalPrice: float
    totalQuantity: int
    orderDate: str
    status: str = "Ожидание"

class CheckoutResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    orderId: Optional[int] = None

def load_json_file(filepath: str, default_data: List):
    if not os.path.exists(filepath):
        print(f"File {filepath} not found. Creating with default data.")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding {filepath}. Using default data.")
        return default_data

def save_json_file(filepath: str, data : List):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_default_products():
    return [
        {
            "id": 1,
            "name": "MF DOOM - Mm..Food",
            "description": "A classic hip-hop album featuring the iconic MF DOOM.",
            "category": "Music",
            "price": 12.99,
            "imageUrl": "https://upload.wikimedia.org/wikipedia/en/3/3a/Mmfood.jpg"
        },
        {
            "id": 2,
            "name": "MF DOOM - Madvillainy",
            "description": "Collaboration album with Madlib, considered one of the greatest hip-hop albums.",
            "category": "Music",
            "price": 14.99,
            "imageUrl": "https://upload.wikimedia.org/wikipedia/en/6/65/Madvillain-madvillainy-album.jpg"
        }
    ]

def get_default_users():
    return [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "birthDate": "1990-01-01",
            "password": "password123"
        }
    ]

def get_default_orders():
    return []

app = FastAPI(title="API Personal Stuff (Python)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/Products/GetAllProducts", response_model=List[Product])
async def get_all_products():
    products = load_json_file(JSON_FILE_PATH, get_default_products())
    return products

@app.get("/api/Products/GetProduct/{product_id}", response_model=Product)
async def get_product(product_id: int):
    products = load_json_file(JSON_FILE_PATH, get_default_products())
    product = next((p for p in products if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@app.get("/api/Cart/GetCart/{user_id}", response_model=Cart)
async def get_cart(user_id: int):
    carts = load_json_file(CART_FILE_PATH, [])
    user_cart = next((c for c in carts if c["userId"] == user_id), None)
    if not user_cart:
        return Cart(userId=user_id, items=[])
    return Cart(**user_cart)

@app.post("/api/Cart/AddToCart/{user_id}/{product_id}/{quantity}")
async def add_to_cart(user_id: int, product_id: int, quantity: int):
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    carts = load_json_file(CART_FILE_PATH, [])
    user_cart = next((c for c in carts if c["userId"] == user_id), None)

    if not user_cart:
        user_cart = {"userId": user_id, "items": []}
        carts.append(user_cart)

    existing_item = next((i for i in user_cart["items"] if i["productId"] == product_id), None)
    if existing_item:
        existing_item["quantity"] += quantity
    else:
        user_cart["items"].append({"productId": product_id, "quantity": quantity})

    save_json_file(CART_FILE_PATH, carts)
    return {"message": "Item added to cart successfully", "cart": user_cart}

@app.put("/api/Cart/UpdateQuantity/{user_id}/{product_id}/{new_quantity}")
async def update_quantity(user_id: int, product_id: int, new_quantity: int):
    if new_quantity < 0:
         raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    carts = load_json_file(CART_FILE_PATH, [])
    user_cart = next((c for c in carts if c["userId"] == user_id), None)

    if not user_cart:
        raise HTTPException(status_code=404, detail="Cart not found for user")

    existing_item = next((i for i in user_cart["items"] if i["productId"] == product_id), None)
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item not found in cart")

    if new_quantity == 0:
        user_cart["items"] = [i for i in user_cart["items"] if i["productId"] != product_id]
    else:
        existing_item["quantity"] = new_quantity

    save_json_file(CART_FILE_PATH, carts)
    return {"message": "Cart updated successfully", "cart": user_cart}

@app.delete("/api/Cart/RemoveFromCart/{user_id}/{product_id}")
async def remove_from_cart(user_id: int, product_id: int):
    carts = load_json_file(CART_FILE_PATH, [])
    user_cart = next((c for c in carts if c["userId"] == user_id), None)

    if not user_cart:
        raise HTTPException(status_code=404, detail="Cart not found for user")

    original_length = len(user_cart["items"])
    user_cart["items"] = [i for i in user_cart["items"] if i["productId"] != product_id]

    if len(user_cart["items"]) == original_length:
        raise HTTPException(status_code=404, detail="Item not found in cart")

    save_json_file(CART_FILE_PATH, carts)
    return {"message": "Item removed from cart successfully", "cart": user_cart}

@app.get("/api/Auth/Users", response_model=List[User])
async def get_all_users():
    users = load_json_file(USERS_FILE_PATH, get_default_users())
    return [User(**u) for u in users]

@app.post("/api/Auth/Register", response_model=LoginResponse)
async def register(user_data: User):
    users = load_json_file(USERS_FILE_PATH, get_default_users())

    if any(u["email"] == user_data.email for u in users):
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_id = max([u["id"] for u in users], default=0) + 1
    user_data.id = new_id

    users.append(user_data.dict())
    save_json_file(USERS_FILE_PATH, users)

    return LoginResponse(
        success=True,
        message="Registration successful",
        user={"id": user_data.id, "name": user_data.name, "email": user_data.email, "birthDate": user_data.birthDate}
    )

@app.post("/api/Auth/Login", response_model=LoginResponse)
async def login(login_request: LoginRequest):
    users = load_json_file(USERS_FILE_PATH, get_default_users())

    user = next((u for u in users if u["email"] == login_request.email and u["password"] == login_request.password), None)

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return LoginResponse(
        success=True,
        message="Login successful",
        user={"id": user["id"], "name": user["name"], "email": user["email"], "birthDate": user["birthDate"]}
    )

@app.post("/api/Orders/Checkout/{user_id}", response_model=CheckoutResponse)
async def checkout(user_id: int):
    carts = load_json_file(CART_FILE_PATH, [])
    user_cart = next((c for c in carts if c["userId"] == user_id), None)

    if not user_cart or not user_cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty or does not exist for user")

    products = load_json_file(JSON_FILE_PATH, get_default_products())
    product_map = {p["id"]: p for p in products}

    total_price = 0.0
    total_quantity = 0
    order_items = []
    for cart_item in user_cart["items"]:
        product_id = cart_item["productId"]
        quantity = cart_item["quantity"]
        product = product_map.get(product_id)

        if not product:
            raise HTTPException(status_code=400, detail=f"Product with ID {product_id} not found.")

        item_total_price = product["price"] * quantity
        total_price += item_total_price
        total_quantity += quantity

        order_items.append(OrderItem(
            productId=product_id,
            quantity=quantity,
            name=product["name"],
            price=product["price"],
            imageUrl=product["imageUrl"]
        ))

    orders = load_json_file(ORDERS_FILE_PATH, get_default_orders())
    new_order_id = max([o["id"] for o in orders], default=0) + 1

    order = Order(
        id=new_order_id,
        userId=user_id,
        items=order_items,
        totalPrice=total_price,
        totalQuantity=total_quantity,
        orderDate=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    orders.append(order.dict())
    save_json_file(ORDERS_FILE_PATH, orders)

    carts.remove(user_cart)
    save_json_file(CART_FILE_PATH, carts)

    return CheckoutResponse(
        success=True,
        message="Order created successfully",
        orderId=new_order_id
    )

@app.get("/api/Orders/GetUserOrders/{user_id}", response_model=List[Order])
async def get_user_orders(user_id: int):
    """Retrieve all orders for a specific user."""
    orders = load_json_file(ORDERS_FILE_PATH, get_default_orders())
    user_orders = [Order(**o) for o in orders if o["userId"] == user_id]
    return user_orders

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5079)
