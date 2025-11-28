from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"
    id   = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class Book(Base):
    __tablename__ = "books"
    id     = Column(Integer, primary_key=True, autoincrement=True)
    title  = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    pages  = Column(Integer)
    year   = Column(Integer)
    shelves = Column(String)                     # comma-joined tags
    __table_args__ = (UniqueConstraint("title", "author", name="uq_title_author"),)

    readings = relationship("Reading", back_populates="book", cascade="all, delete")

class Reading(Base):
    __tablename__ = "readings"
    id      = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    rating  = Column(Float)
    exclusive_shelf = Column(String)
    date_read = Column(Date)

    user = relationship("User")
    book = relationship("Book", back_populates="readings")