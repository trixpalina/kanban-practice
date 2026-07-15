from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, BoardMember, Role
from .config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Невалидный токен")
    except JWTError:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user

def check_board_role(required_role: str):
    def role_checker(board_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
        membership = db.query(BoardMember).filter(
            BoardMember.user_id == current_user.id,
            BoardMember.board_id == board_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="Нет доступа к этой доске")
            
        role = db.query(Role).filter(Role.id == membership.role_id).first()
        
        role_hierarchy = {"owner": 3, "writer": 2, "reader": 1}
        if role_hierarchy.get(role.name, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(status_code=403, detail=f"Недостаточно прав. Требуется роль: {required_role}")
            
        return current_user
    return role_checker