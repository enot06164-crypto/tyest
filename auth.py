"""Authentication router for Iskra"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
import os
import shutil
from typing import Optional

from app.models import get_db
from app.models.user import User, friendships, FriendRequest
from app.schemas import UserCreate, UserLogin, UserResponse, Token, UserUpdate
from app.services import verify_password, get_password_hash, create_access_token, verify_token, generate_key_pair
from app.config import settings

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = verify_token(token)
        if payload:
            user_id_str = payload.get("sub")
            if user_id_str:
                user_id = int(user_id_str)
                return db.query(User).filter(User.id == user_id).first()
    except:
        pass
    return None

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if username exists
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Create user
    db_user = User(
        username=user_data.username,
        display_name=user_data.display_name or user_data.username,
        password_hash=get_password_hash(user_data.password),
        public_key=generate_key_pair(),
        status="New to Iskra 🔥"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Create token
    access_token = create_access_token(data={"sub": db_user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(db_user)
    }

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form login (for API docs/swagger)"""
    user = db.query(User).filter(
        or_(User.username == form_data.username, User.iskra_id == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.is_online = True
    db.commit()

    access_token = create_access_token(data={"sub": user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.post("/login-json", response_model=Token)
async def login_json(user_data: UserLogin, db: Session = Depends(get_db)):
    """JSON login (for frontend)"""
    user = db.query(User).filter(
        or_(User.username == user_data.username, User.iskra_id == user_data.username)
    ).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.is_online = True
    db.commit()

    access_token = create_access_token(data={"sub": user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.is_online = False
    db.commit()
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

@router.put("/me", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_update.display_name is not None:
        current_user.display_name = user_update.display_name
    if user_update.status is not None:
        current_user.status = user_update.status
    if user_update.bio is not None:
        current_user.bio = user_update.bio

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)

@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_ext = file.filename.split(".")[-1]
    filename = f"avatar_{current_user.id}_{os.urandom(4).hex()}.{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    current_user.avatar_url = f"/static/uploads/{filename}"
    db.commit()

    return {"avatar_url": current_user.avatar_url}
