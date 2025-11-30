from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import Base, engine, SessionLocal
import models
from services.etl import import_goodreads_csv

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