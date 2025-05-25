from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from jose import JWTError, jwt

import crud
import models
import schemas
from models import engine, get_db

SECRET_KEY = "mailguard@2025"  # Replace with a secure random key in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

models.Base.metadata.create_all(bind=engine) # Create database tables

app = FastAPI(
    title="MailGuard BE",
    description="A FastAPI backend simulating basic Gmail functionalities using SQLite.",
    version="0.1.0"
)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# --- User Endpoints ---
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/users/login",  tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    #write documentation
    """

    Authenticates a user and returns an access token.
    - **username**: The email of the user.
    - **password**: The password of the user.

    """ 
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.User, tags=["Users"])
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# --- Email Endpoints ---

@app.post("/emails/send", response_model=schemas.Email, status_code=status.HTTP_201_CREATED, tags=["Emails"])
def send_email(email: schemas.EmailCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    sender = current_user
    receiver = crud.get_user_by_email(db, email=email.receiver_email)
    if not receiver:
        raise HTTPException(status_code=404, detail=f"Receiver with email {email.receiver_email} not found.")
    created_email = crud.create_email(db=db, email=email, sender_id=sender.id)
    if not created_email:
         raise HTTPException(status_code=400, detail="Could not send email. Receiver might not exist.")
    return created_email

@app.get("/emails/inbox", response_model=List[schemas.Email], tags=["Emails"])
def get_inbox(skip: int = 0, limit: int = 20, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    emails = crud.get_received_emails(db, user_id=current_user.id, skip=skip, limit=limit)
    return emails

@app.get("/emails/sent", response_model=List[schemas.Email], tags=["Emails"])
def get_sent_mail(skip: int = 0, limit: int = 20, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    emails = crud.get_sent_emails(db, user_id=current_user.id, skip=skip, limit=limit)
    return emails

@app.get("/emails/{email_id}", response_model=schemas.Email, tags=["Emails"])
def read_email(email_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    email = crud.get_email(db, email_id=email_id, user_id=current_user.id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found or you don't have permission to view it.")
    # If the current user is the receiver and the email hasn't been read, mark it as read.
    if email.receiver_id == current_user.id and not email.is_read:
        crud.mark_email_as_read(db, email_id=email_id, user_id=current_user.id)
        db.refresh(email) # Refresh to get the updated is_read status
    return email

@app.patch("/emails/{email_id}/read", response_model=schemas.Email, tags=["Emails"])
def mark_as_read(email_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    email = crud.mark_email_as_read(db, email_id=email_id, user_id=current_user.id)
    if email is None:
        raise HTTPException(status_code=404, detail="Email not found or you are not the receiver.")
    return email


# A simple root endpoint
@app.get("/", tags=["Root"])
async def root():
    return {"message": "Welcome to MailGuard-BE API. Visit /docs for API documentation."}


# To run the app (from the project root directory):
# uvicorn main:app --reload
#
# Before running, ensure you have created at least one user (e.g., with ID 1)
# if you are using the hardcoded current_user_id for testing.
# Example: POST to /users/ with body: {"email": "user1@example.com", "password": "securepassword1"}
# Then, you can test email endpoints assuming you are user1@example.com (ID 1).
