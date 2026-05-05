"""
Security utilities for Iskra
TeleGuard-inspired: maximum privacy, no personal data collection
"""
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets
import re
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None

def generate_recovery_seed() -> str:
    """Generate BIP39-style recovery phrase for anonymous account recovery"""
    wordlist = [
        "искра", "пламя", "свет", "тень", "волна", "камень", "лес", "река",
        "гора", "небо", "звезда", "луна", "солнце", "ветер", "дождь", "снег",
        "огонь", "вода", "земля", "воздух", "молния", "гром", "тишина", "шум",
        "путь", "дорога", "мост", "дом", "сад", "поле", "лес", "берег",
        "песок", "коралл", "жемчуг", "алмаз", "рубин", "сапфир", "изумруд", "янтарь"
    ]
    return " ".join(secrets.choice(wordlist) for _ in range(12))

def hash_device_fingerprint(user_agent: str, accept_lang: str) -> str:
    """Hash device info for audit logs (NO raw data storage)"""
    data = f"{user_agent}:{accept_lang}"
    return hashlib.sha256(data.encode()).hexdigest()

def sanitize_username(username: str) -> str:
    """Sanitize username - allow letters, numbers, underscores"""
    username = username.lower().strip()
    username = re.sub(r'[^a-z0-9_]', '', username)
    return username[:50]

def is_strong_password(password: str) -> bool:
    """Check password strength"""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True
