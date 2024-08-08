from fastapi import FastAPI, Form, Request, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
from fastapi.responses import JSONResponse
import uvicorn
import jwt

app = FastAPI()

class Flower(BaseModel):
    id: int
    title: str
    color: str


class User(BaseModel):
    username: str
    password: str
    photo: str = None



class FlowersRepository:
    def __init__(self):
        self.flowers = []
        self.next_id = 1

    def get_all(self):
        return self.flowers

    def get_one(self, id):
        for flower in self.flowers:
            if flower.id == id:
                return flower
        return None

    def save(self, flower: Flower):
        flower.id = self.next_id
        self.next_id += 1
        self.flowers.append(flower)
        return flower


class UsersRepository:
    def __init__(self):
        self.users = []

    def save(self, user: User):
        self.users.append(user)

    def get_by_username(self, username):
        for user in self.users:
            if user.username == username:
                return user
        return None


flowers_repo = FlowersRepository()
users_repo = UsersRepository()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")



@app.post("/signup")
async def signup(username: str = Form(...), password: str = Form(...), photo: str = Form(None)):
    user = User(username=username, password=password, photo=photo)
    users_repo.save(user)
    return JSONResponse(status_code=200, content={"message": "User registered successfully"})


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_repo.get_by_username(form_data.username)
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    token = jwt.encode({"username": user.username}, "secret", algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}


@app.get("/profile")
async def profile(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, "secret", algorithms=["HS256"])
    user = users_repo.get_by_username(payload["username"])
    return {"username": user.username, "photo": user.photo}


@app.get("/flowers")
async def get_flowers():
    return flowers_repo.get_all()


@app.post("/flowers")
async def add_flower(title: str = Form(...), color: str = Form(...)):
    flower = Flower(id=0, title=title, color=color)
    flower = flowers_repo.save(flower)
    return {"id": flower.id}

@app.get("/flowers/{id}")
async def get_flower_by_id(id: int):
    flower = flowers_repo.get_one(id)
    if flower is None:
        raise HTTPException(status_code=404, detail="Flower not found")
    return flower

@app.post("/cart/items")
async def add_to_cart(request: Request, flower_id: int = Form(...)):
    response = JSONResponse(status_code=200, content={"message": "Flower added to cart"})
    response.set_cookie(key="cart", value=str(flower_id))
    return response


@app.get("/cart/items")
async def get_cart_items(request: Request):
    cart = request.cookies.get("cart")
    if not cart:
        return {"items": [], "total": 0}
    flower = flowers_repo.get_one(int(cart))
    if not flower:
        return {"items": [], "total": 0}
    return {"items": [{"id": flower.id, "title": flower.title, "color": flower.color}], "total": 1}

