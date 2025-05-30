from sqlalchemy.orm import Session
from passlib.context import CryptContext
import models
import schemas
from passlib.context import CryptContext
import joblib, os
import re
import string
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Load the trained model
model_path = "./model/spam_pipeline.pkl"

# check if the path exists
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model file not found at {model_path}")

model = joblib.load(model_path)


# Password hashing utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# Filter ultilities
def clean_text(text: str) -> str:
    """Basic text cleaning function"""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_texts(texts: List[str]) -> List[str]:
    """Clean a list of texts"""
    return [clean_text(t) for t in texts]

# Spam filter utility
def filter_emails(email_content: str) -> float:
    cleaned = clean_text(email_content)
    probability = model.predict_proba([cleaned])[0][1]  # Probability of spam
    return probability

# User CRUD operations
def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_email)
    return db_email

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

# Email CRUD operations
def create_email(db: Session, email: schemas.EmailCreate, sender_id: int):
    receiver = get_user_by_email(db, email.receiver_email)
    if not receiver:
        return None # Or raise an exception

    full_content = f"{email.body}"
    spam_probability = filter_emails(full_content)
    logger.info(f"Spam probability for '{full_content}': {spam_probability}")
    is_spam_prob = spam_probability >= 0.7  # Threshold can be adjusted
    
    db_email = models.Email(
        sender_id=sender_id,
        receiver_id=receiver.id,
        subject=email.subject,
        body=email.body,
        is_spam=is_spam_prob,
    )
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email

def get_received_emails(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Email).filter(models.Email.receiver_id == user_id).order_by(models.Email.timestamp.desc()).offset(skip).limit(limit).all()

def get_sent_emails(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Email).filter(models.Email.sender_id == user_id).order_by(models.Email.timestamp.desc()).offset(skip).limit(limit).all()

def get_email(db: Session, email_id: int, user_id: int):
    """Fetches a specific email if the user is either the sender or receiver."""
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if email and (email.sender_id == user_id or email.receiver_id == user_id):
        return email
    return None

def mark_email_as_read(db: Session, email_id: int, user_id: int):
    email = db.query(models.Email).filter(models.Email.id == email_id, models.Email.receiver_id == user_id).first()
    if email:
        email.is_read = True
        db.commit()
        db.refresh(email)
        return email
    return None