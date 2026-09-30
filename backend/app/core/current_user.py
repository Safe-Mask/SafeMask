from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.security import ALGORITHM, SECRET_KEY, TIPO_ACCESS
from app.database import get_db
from app.models.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível autenticar.",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try :
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception

        # Um token de recuperacao de senha tambem e um JWT valido. Sem esta
        # checagem ele serviria para autenticar na API.
        if payload.get("typ") != TIPO_ACCESS:
            raise credentials_exception

    except JWTError as exc:
        raise credentials_exception from exc

    user = db.query(Usuario).filter(Usuario.email == email).first()
    if user is None:
        raise credentials_exception

    # Senha trocada invalida os tokens emitidos antes dela.
    if payload.get("tv") != (user.token_version or 0):
        raise credentials_exception

    return user
