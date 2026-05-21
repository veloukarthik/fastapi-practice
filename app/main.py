from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer
from sqlalchemy import create_engine, text
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
import os

app = FastAPI()

# Security scheme
security = HTTPBearer()

# Secret key for JWT (set via env in production)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "24"))

# Database connection (Turso / libSQL or local SQLite)
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

if TURSO_DATABASE_URL:
    engine = create_engine(
        f"sqlite+libsql://{TURSO_DATABASE_URL}?secure=true",
        connect_args={"auth_token": TURSO_AUTH_TOKEN},
        pool_pre_ping=True,
    )
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
        pool_pre_ping=True,
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(authorization: str = Header(None)) -> int:
    """Verify JWT token from Authorization header and return user_id"""
    
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    
    jwt_token = authorization
    
    # Remove 'Bearer ' prefix if present
    if jwt_token.startswith("Bearer "):
        jwt_token = jwt_token[7:]
    
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        # Convert user_id back to integer
        return int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")


async def get_current_user(token: str) -> str:
    """Dependency to get current user from token"""
    return verify_token(token)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/register")
async def user_register(username: str, email: str, password: str):
    with engine.connect() as connection:
        # Check if user already exists
        result = connection.execute(text("select * from users where username = :username"), {"username": username})
        if result.fetchone():
            return {"message": "User already exists"}
        
        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Insert the user
        try:
            connection.execute(text("INSERT INTO users (username, email, password) VALUES (:username, :email, :password)"), 
                             {"username": username, "email": email, "password": hashed_password})
            
            # Commit the transaction
            connection.commit()
            
            return {"message": "User registered successfully"}
        except Exception as e:
            return {"message": f"Registration failed: {str(e)}"}


@app.post("/login")
async def user_login(username: str, password: str):
    with engine.connect() as connection:
        # Get user from database with specific columns
        result = connection.execute(text("select id, username, email, password from users where username = :username"), {"username": username})
        user = result.fetchone()
        
        if not user:
            return {"message": "Invalid username or password"}
        
        user_id = user[0]  # Get user id
        stored_password_hash = user[3]  # Password is the 4th column
        
        try:
            # Convert stored hash to bytes if it's a string
            if isinstance(stored_password_hash, str):
                stored_password_hash = stored_password_hash.encode('utf-8')
            
            if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash):
                # Generate JWT token with user_id as string
                access_token = create_access_token(data={"sub": str(user_id)})
                return {"message": "Login successful", "access_token": access_token, "token_type": "bearer", "user_id": user_id}
        except ValueError as e:
            return {"message": f"Error verifying password: {str(e)}"}
        
    return {"message": "Invalid username or password"}


@app.get("/todos")
async def get_todos(user_id: int = Depends(verify_token)):
    """Get all todos for the authenticated user"""
    
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT id, todo, body, completed FROM todos WHERE created_by = :user_id ORDER BY id DESC"),
                {"user_id": user_id}
            )
            todos = [dict(row._mapping) for row in result]
        return {"todos": todos, "user_id": user_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@app.post("/todos")
async def create_todo(todo: str, body: str = "", user_id: int = Depends(verify_token)):
    """Create a new todo for the authenticated user"""
    
    with engine.connect() as connection:
        try:
            connection.execute(
                text("INSERT INTO todos (todo, body, created_by, completed) VALUES (:todo, :body, :created_by, :completed)"),
                {"todo": todo, "body": body, "created_by": user_id, "completed": 0}
            )
            connection.commit()
            return {"message": "Todo created successfully"}
        except Exception as e:
            return {"message": f"Failed to create todo: {str(e)}"}


@app.put("/todos/{todo_id}")
async def update_todo(todo_id: int, todo: str = None, body: str = None, completed: int = None, token: str = None, user_id: int = Depends(verify_token)):
    """Update a todo (owner only)"""
    
    with engine.connect() as connection:
        # Check if todo belongs to the user
        result = connection.execute(
            text("SELECT id FROM todos WHERE id = :id AND created_by = :user_id"),
            {"id": todo_id, "user_id": user_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")
        
        # Build dynamic update query
        updates = []
        params = {"id": todo_id, "user_id": user_id}
        
        if todo is not None:
            updates.append("todo = :todo")
            params["todo"] = todo
        if body is not None:
            updates.append("body = :body")
            params["body"] = body
        if completed is not None:
            updates.append("completed = :completed")
            params["completed"] = completed
        
        if updates:
            update_query = f"UPDATE todos SET {', '.join(updates)} WHERE id = :id AND created_by = :user_id"
            try:
                connection.execute(text(update_query), params)
                connection.commit()
                return {"message": "Todo updated successfully"}
            except Exception as e:
                return {"message": f"Failed to update todo: {str(e)}"}
        else:
            return {"message": "No fields to update"}


@app.delete("/todos/{todo_id}")
async def delete_todo(todo_id: int, token: str = None, user_id: int = Depends(verify_token)):
    """Delete a todo (owner only)"""
    
    with engine.connect() as connection:
        # Check if todo belongs to the user
        result = connection.execute(
            text("SELECT id FROM todos WHERE id = :id AND created_by = :user_id"),
            {"id": todo_id, "user_id": user_id}
        )
        if not result.fetchone():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found or unauthorized")
        
        try:
            connection.execute(
                text("DELETE FROM todos WHERE id = :id AND created_by = :user_id"),
                {"id": todo_id, "user_id": user_id}
            )
            connection.commit()
            return {"message": "Todo deleted successfully"}
        except Exception as e:
            return {"message": f"Failed to delete todo: {str(e)}"}
