from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
import models
from services.etl import import_goodreads_csv
from sqlalchemy import func
from datetime import date as _date
from services.recommend import recommend_to_read

app = FastAPI()

# create tables once at startup
Base.metadata.create_all(bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/import/goodreads")
async def import_goodreads(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=415, detail="upload a .csv file")
    content = await file.read()
    result = import_goodreads_csv(content, db)
    return result


@app.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    total_books = db.query(models.Book).count()
    total_readings = db.query(models.Reading).count()

    read_count = (
        db.query(models.Reading)
          .filter(models.Reading.exclusive_shelf == "read")
          .count()
    )

    avg_rating = (
        db.query(func.avg(models.Reading.rating))
          .filter(models.Reading.rating.isnot(None))
          .scalar()
    )

    total_pages_read = (
        db.query(func.sum(models.Book.pages))
          .join(models.Reading, models.Reading.book_id == models.Book.id)
          .filter(models.Reading.exclusive_shelf == "read",
                  models.Book.pages.isnot(None))
          .scalar()
    ) or 0

    first_read = db.query(func.min(models.Reading.date_read)).scalar()
    days = max(1, (_date.today() - first_read).days) if first_read else 1
    pages_per_day = round(total_pages_read / days, 2) if total_pages_read else 0

    return {
        "total_books": total_books,
        "total_readings": total_readings,
        "read_count": read_count,
        "avg_rating": round(float(avg_rating), 2) if avg_rating is not None else None,
        "total_pages_read": int(total_pages_read),
        "pages_per_day": pages_per_day,
        "since": str(first_read) if first_read else None,
    }

@app.get("/recommend/next")
def recommend_next(
    limit: int = 10,
    w_author: float = 0.35,
    w_year: float = 0.25,
    w_pages: float = 0.20,
    k_author: float = 2.0,
    k_year: float = 2.0,
    db: Session = Depends(get_db)
):
    return recommend_to_read(
        db,
        user_id="me",
        limit=limit,
        w_author=w_author,
        w_pages=w_pages,
        w_year=w_year,
        k_author=k_author,
        k_year=k_year,
    )



app = FastAPI()

Base.metadata.create_all(bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/import/goodreads")
async def import_goodreads(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=415, detail="upload a .csv file")
    content = await file.read()
    result = import_goodreads_csv(content, db)
    return result


@app.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    total_books = db.query(models.Book).count()
    total_readings = db.query(models.Reading).count()

    read_count = (
        db.query(models.Reading)
          .filter(models.Reading.exclusive_shelf == "read")
          .count()
    )

    avg_rating = (
        db.query(func.avg(models.Reading.rating))
          .filter(models.Reading.rating.isnot(None))
          .scalar()
    )

    total_pages_read = (
        db.query(func.sum(models.Book.pages))
          .join(models.Reading, models.Reading.book_id == models.Book.id)
          .filter(models.Reading.exclusive_shelf == "read",
                  models.Book.pages.isnot(None))
          .scalar()
    ) or 0

    first_read = db.query(func.min(models.Reading.date_read)).scalar()
    days = max(1, (_date.today() - first_read).days) if first_read else 1
    pages_per_day = round(total_pages_read / days, 2) if total_pages_read else 0

    return {
        "total_books": total_books,
        "total_readings": total_readings,
        "read_count": read_count,
        "avg_rating": round(float(avg_rating), 2) if avg_rating is not None else None,
        "total_pages_read": int(total_pages_read),
        "pages_per_day": pages_per_day,
        "since": str(first_read) if first_read else None,
    }

@app.get("/recommend/next")
def recommend_next(
    limit: int = 10,
    w_author: float = 0.35,
    w_year: float = 0.25,
    w_pages: float = 0.20,
    k_author: float = 2.0,
    k_year: float = 2.0,
    db: Session = Depends(get_db)
):
    return recommend_to_read(
        db,
        user_id="me",
        limit=limit,
        w_author=w_author,
        w_pages=w_pages,
        w_year=w_year,
        k_author=k_author,
        k_year=k_year,
    )