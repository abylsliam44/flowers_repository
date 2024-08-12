from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
from fastapi.responses import JSONResponse
import uvicorn
import jwt
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session


SQLALCHEMY_DATABASE_URL = "postgresql://%(DB_USER)s:%(DB_PASS)s@%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Flower(Base):
    __tablename__ = "flowers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    color = Column(String)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    photo = Column(String, nullable=True)


Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI instance
app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Routes
@app.post("/signup")
async def signup(username: str = Form(...), password: str = Form(...), photo: str = Form(None), db: Session = Depends(get_db)):
    user = User(username=username, password=password, photo=photo)
    db.add(user)
    db.commit()
    db.refresh(user)
    return JSONResponse(status_code=200, content={"message": "User registered successfully"})

@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    token = jwt.encode({"username": user.username}, "secret", algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/profile")
async def profile(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = jwt.decode(token, "secret", algorithms=["HS256"])
    user = db.query(User).filter(User.username == payload["username"]).first()
    return {"username": user.username, "photo": user.photo}

@app.get("/flowers")
async def get_flowers(db: Session = Depends(get_db)):
    flowers = db.query(Flower).all()
    return flowers

@app.post("/flowers")
async def add_flower(title: str = Form(...), color: str = Form(...), db: Session = Depends(get_db)):
    flower = Flower(title=title, color=color)
    db.add(flower)
    db.commit()
    db.refresh(flower)
    return {"id": flower.id}

@app.get("/flowers/{id}")
async def get_flower_by_id(id: int, db: Session = Depends(get_db)):
    flower = db.query(Flower).filter(Flower.id == id).first()
    if flower is None:
        raise HTTPException(status_code=404, detail="Flower not found")
    return flower

@app.post("/cart/items")
async def add_to_cart(request: Request, flower_id: int = Form(...)):
    response = JSONResponse(status_code=200, content={"message": "Flower added to cart"})
    response.set_cookie(key="cart", value=str(flower_id))
    return response

@app.get("/cart/items")
async def get_cart_items(request: Request, db: Session = Depends(get_db)):
    cart = request.cookies.get("cart")
    if not cart:
        return {"items": [], "total": 0}
    flower = db.query(Flower).filter(Flower.id == int(cart)).first()
    if not flower:
        return {"items": [], "total": 0}
    return {"items": [{"id": flower.id, "title": flower.title, "color": flower.color}], "total": 1}

# Run the app
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
