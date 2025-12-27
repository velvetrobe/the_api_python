import json
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

# --- Configuration and File I/O ---
DATA_DIR = "data"
BOOKS_FILE = os.path.join(DATA_DIR, "books.json")
READERS_FILE = os.path.join(DATA_DIR, "readers.json")

os.makedirs(DATA_DIR, exist_ok=True)  # Create data directory if it doesn't exist


def load_data(file_path):
    """Load data from a JSON file."""
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_data(file_path, data):
    """Save data to a JSON file."""
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- Pydantic Models ---
class Book(BaseModel):
    book_code: str
    author: str
    title: str
    publication_year: int
    price: float
    is_new: bool = False
    annotation: str = ""


class Reader(BaseModel):
    reader_ticket_number: str
    full_name: str
    address: str
    phone: str
    borrowed_books: list = Field(default_factory=list)  # List of {book_code, borrow_date, return_date}


class BorrowRequest(BaseModel):
    book_code: str
    borrow_date: str  # Format: YYYY-MM-DD
    return_date: str  # Format: YYYY-MM-DD


class ReturnRequest(BaseModel):
    book_code: str


# --- API Application Setup ---
app = FastAPI(title="Simple Library API")

# Configure CORS for WPF/Android clients (allows all origins for simplicity)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Helper Functions ---
def _find_book_by_code(code: str):
    books = load_data(BOOKS_FILE)
    for book in books:
        if book["book_code"] == code:
            return book, books
    return None, books


def _find_reader_by_ticket(ticket: str):
    readers = load_data(READERS_FILE)
    for reader in readers:
        if reader["reader_ticket_number"] == ticket:
            return reader, readers
    return None, readers


# --- Book Endpoints ---
@app.get("/books/")
def get_all_books():
    return load_data(BOOKS_FILE)


@app.get("/books/{book_code}")
def get_book(book_code: str):
    book, _ = _find_book_by_code(book_code)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.post("/books/")
def create_book(book: Book):
    existing_book, books = _find_book_by_code(book.book_code)
    if existing_book:
        raise HTTPException(status_code=409, detail="Book with this code already exists")
    books.append(book.dict())
    save_data(BOOKS_FILE, books)
    return book


@app.put("/books/{book_code}")
def update_book(book_code: str, updated_book: Book):
    book, books = _find_book_by_code(book_code)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    # Ensure the book_code in the path matches the one in the request body
    if updated_book.book_code != book_code:
        raise HTTPException(status_code=400, detail="Book code in request body must match path parameter")
    for i, b in enumerate(books):
        if b["book_code"] == book_code:
            books[i] = updated_book.dict()
            break
    save_data(BOOKS_FILE, books)
    return updated_book


@app.delete("/books/{book_code}")
def delete_book(book_code: str):
    book, books = _find_book_by_code(book_code)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if any reader has borrowed this book
    readers = load_data(READERS_FILE)
    for reader in readers:
        for borrowed_book in reader.get("borrowed_books", []):
            if borrowed_book.get("book_code") == book_code:
                raise HTTPException(status_code=409, detail="Cannot delete book, it is currently borrowed by a reader.")

    books.remove(book)
    save_data(BOOKS_FILE, books)
    return {"message": f"Book {book_code} deleted successfully"}


# --- Reader Endpoints ---
@app.get("/readers/")
def get_all_readers():
    return load_data(READERS_FILE)


@app.get("/readers/{ticket_number}")
def get_reader(ticket_number: str):
    reader, _ = _find_reader_by_ticket(ticket_number)
    if not reader:
        raise HTTPException(status_code=404, detail="Reader not found")
    return reader


@app.post("/readers/")
def create_reader(reader: Reader):
    existing_reader, readers = _find_reader_by_ticket(reader.reader_ticket_number)
    if existing_reader:
        raise HTTPException(status_code=409, detail="Reader with this ticket number already exists")
    readers.append(reader.dict())
    save_data(READERS_FILE, readers)
    return reader


@app.put("/readers/{ticket_number}")
def update_reader(ticket_number: str, updated_reader: Reader):
    reader, readers = _find_reader_by_ticket(ticket_number)
    if not reader:
        raise HTTPException(status_code=404, detail="Reader not found")
    # Ensure the ticket number in the path matches the one in the request body
    if updated_reader.reader_ticket_number != ticket_number:
        raise HTTPException(status_code=400, detail="Ticket number in request body must match path parameter")
    for i, r in enumerate(readers):
        if r["reader_ticket_number"] == ticket_number:
            readers[i] = updated_reader.dict()
            break
    save_data(READERS_FILE, readers)
    return updated_reader


@app.delete("/readers/{ticket_number}")
def delete_reader(ticket_number: str):
    reader, readers = _find_reader_by_ticket(ticket_number)
    if not reader:
        raise HTTPException(status_code=404, detail="Reader not found")
    # Check if reader has borrowed books
    if reader.get("borrowed_books"):
        raise HTTPException(status_code=409, detail="Cannot delete reader, they have borrowed books.")
    readers.remove(reader)
    save_data(READERS_FILE, readers)
    return {"message": f"Reader {ticket_number} deleted successfully"}


# --- Borrow/Return Endpoints ---
@app.post("/readers/{ticket_number}/borrow")
def borrow_book(ticket_number: str, request: BorrowRequest):
    reader, readers = _find_reader_by_ticket(ticket_number)
    if not reader:
        raise HTTPException(status_code=404, detail="Reader not found")

    book, _ = _find_book_by_code(request.book_code)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Check if already borrowed
    for borrowed_book in reader.get("borrowed_books", []):
        if borrowed_book["book_code"] == request.book_code:
            raise HTTPException(status_code=409, detail="Book is already borrowed by this reader")

    reader["borrowed_books"].append(request.dict())
    save_data(READERS_FILE, readers)
    return {"message": f"Book {request.book_code} borrowed by {ticket_number}"}


@app.post("/readers/{ticket_number}/return")
def return_book(ticket_number: str, request: ReturnRequest):
    reader, readers = _find_reader_by_ticket(ticket_number)
    if not reader:
        raise HTTPException(status_code=404, detail="Reader not found")

    borrowed_books = reader.get("borrowed_books", [])
    book_to_return_index = -1
    for i, borrowed_book in enumerate(borrowed_books):
        if borrowed_book["book_code"] == request.book_code:
            book_to_return_index = i
            break

    if book_to_return_index == -1:
        raise HTTPException(status_code=404, detail="This book is not currently borrowed by this reader.")

    borrowed_books.pop(book_to_return_index)
    reader["borrowed_books"] = borrowed_books
    save_data(READERS_FILE, readers)
    return {"message": f"Book {request.book_code} returned by {ticket_number}"}


@app.get("/readers/{ticket_number}/current_books")
def get_current_books(ticket_number: str):
    reader, _ = _find_reader_by_ticket(ticket_number)
    if not reader:
        raise HTTPException(status_code=404, detail="Reader not found")
    return reader.get("borrowed_books", [])


# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the Simple Library API!"}


# This block ensures the app runs only when the script is executed directly
if __name__ == "__main__":
    import uvicorn

    # Run the application using uvicorn on localhost port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)