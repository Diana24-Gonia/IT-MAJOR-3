from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import pymysql
import bcrypt

app = FastAPI()

# Database connection configuration
def db_conn():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="your_password",  # Update with your MySQL password
        database="wattpad_app",
        cursorclass=pymysql.cursors.DictCursor
    )

# Models
class User(BaseModel):
    id: Optional[int] = None  # Optional ID for returned data
    username: str
    email: str
    password: str

class Story(BaseModel):
    id: Optional[int] = None  # Optional ID for returned data
    title: str
    content: str
    author_id: int
    category_id: int

class Category(BaseModel):
    id: Optional[int] = None  # Optional ID for returned data
    name: str

class Comment(BaseModel):
    id: Optional[int] = None  # Optional ID for returned data
    story_id: int
    user_id: int
    content: str

class Like(BaseModel):
    id: Optional[int] = None  # Optional ID for returned data
    story_id: int
    user_id: int

# User Registration
@app.post("/users/register", response_model=User)
def register_user(user: User):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (user.username, user.email))
        existing_user = cursor.fetchone()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already registered.")

    # Hash the password before storing it
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())

    # Insert the new user into the database
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", 
            (user.username, user.email, hashed_password)
        )
        conn.commit()
        user_id = cursor.lastrowid

    conn.close()
    return {**user.dict(exclude={"password"}), "id": user_id}

# User Login
@app.post("/users/login")
def login_user(username: str, password: str):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
    
    conn.close()
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    return {"message": "Login successful", "user_id": user["id"]}

# Get User Profile
@app.get("/users/{user_id}", response_model=User)
def get_user_profile(user_id: int):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, username, email FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Add a New Story
@app.post("/stories/add", response_model=Story)
def add_story(story: Story):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO stories (title, content, author_id, category_id) VALUES (%s, %s, %s, %s)",
            (story.title, story.content, story.author_id, story.category_id)
        )
        conn.commit()
        story_id = cursor.lastrowid
    conn.close()
    return {**story.dict(), "id": story_id}

# Get All Stories
@app.get("/stories", response_model=List[Story])
def get_all_stories():
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM stories")
        stories = cursor.fetchall()
    conn.close()
    return stories

# Comment on a Story
@app.post("/stories/{story_id}/comment", response_model=Comment)
def add_comment(story_id: int, comment: Comment):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute(
            "INSERT INTO comments (story_id, user_id, content) VALUES (%s, %s, %s)",
            (story_id, comment.user_id, comment.content)
        )
        conn.commit()
        comment_id = cursor.lastrowid
    conn.close()
    return {**comment.dict(), "id": comment_id}

# Like a Story
@app.post("/stories/{story_id}/like", response_model=Like)
def like_story(story_id: int, like: Like):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM likes WHERE story_id = %s AND user_id = %s",
            (story_id, like.user_id)
        )
        existing_like = cursor.fetchone()
        
        if existing_like:
            raise HTTPException(status_code=400, detail="User already liked this story")
        
        cursor.execute(
            "INSERT INTO likes (story_id, user_id) VALUES (%s, %s)",
            (story_id, like.user_id)
        )
        
        cursor.execute(
            "UPDATE stories SET likes = likes + 1 WHERE id = %s",
            (story_id,)
        )
        conn.commit()
        like_id = cursor.lastrowid
    conn.close()
    return {**like.dict(), "id": like_id}

# Get Comments for a Story
@app.get("/stories/{story_id}/comments", response_model=List[Comment])
def get_comments(story_id: int):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM comments WHERE story_id = %s", (story_id,))
        comments = cursor.fetchall()
    conn.close()
    return comments

# Get Like Count for a Story
@app.get("/stories/{story_id}/likes")
def get_likes(story_id: int):
    conn = db_conn()
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) as likes_count FROM likes WHERE story_id = %s", (story_id,))
        likes_count = cursor.fetchone()
    conn.close()
    return likes_count
