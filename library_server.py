from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel

Base = declarative_base()

class Book(Base):
    __tablename__ = "books"

    uuid = Column(String, primary_key=True)
    title = Column(String, index=True)
    author_uuid = Column(Integer, ForeignKey("authors.uuid"))
    description = Column(Text)
    pages = Column(Integer)
    language = Column(String)
    genre = Column(String)

class Author(Base):
    __tablename__ = "authors"

    uuid = Column(String, primary_key=True)
    name = Column(String, index=True)

DATABASE_URL = "sqlite:///./library.db"
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BookCreate(BaseModel):
    uuid: str
    title: str
    author_uuid: str
    description: str
    pages: int
    language: str
    genre: str

class AuthorCreate(BaseModel):
    uuid: str
    name: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/books/", response_model=BookCreate)
async def create_or_update_book(book: BookCreate, db: Session = Depends(get_db)):
    existing_book = db.query(Book).filter(Book.uuid == book.uuid).first()
    if existing_book:
        for key, value in book.dict().items():
            setattr(existing_book, key, value)
        db.commit()
    else:
        db_book_data = book.dict()
        db_book = Book(**db_book_data)
        db.add(db_book)
        db.commit()
        db.refresh(db_book)
    return book

@app.post("/authors/", response_model=AuthorCreate)
async def create_or_update_author(author: AuthorCreate, db: Session = Depends(get_db)):
    existing_author = db.query(Author).filter(Author.uuid == author.uuid).first()
    if existing_author:
        existing_author.name = author.name
        db.commit()
    else:
        db_author_data = author.dict()
        db_author = Author(**db_author_data)
        db.add(db_author)
        db.commit()
        db.refresh(db_author)
    return author

@app.get("/books/")
async def get_books(
    title: str = None,
    author_uuid: str = None,
    language: str = None,
    min_pages: int = None,
    max_pages: int = None,
    genre: str = None,
    db: Session = Depends(get_db),
):  
    query = db.query(Book)
    if title:
        query = query.filter(Book.title.contains(title))
    if author_uuid:
        query = query.filter(Book.author_uuid == author_uuid)
    if language:
        query = query.filter(Book.language == language)
    if min_pages is not None:
        query = query.filter(Book.pages >= min_pages)
    if max_pages is not None:
        query = query.filter(Book.pages <= max_pages)
    if genre:
        query = query.filter(Book.genre == genre)
    books = query.all()
    return books

@app.get("/authors/")
async def get_authors(db: Session = Depends(get_db)):
    authors = db.query(Author).all()
    return authors

@app.post("/reset_data/")
async def reset_data(db: Session = Depends(get_db)):
    from data_dump import data_dump

    db.query(Book).delete()
    db.query(Author).delete()

    for author_data in data_dump["authors"]:
        db_author = Author(**author_data)
        db.add(db_author)

    for book_data in data_dump["books"]:
        db_book = Book(**book_data)
        db.add(db_book)

    db.commit()
    return {"message": "Data reset to provided values."}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)