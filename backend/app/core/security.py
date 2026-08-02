# Funções para configurar o JWT de autenticação e hash de senhas

from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Chave para assinar tokens. Em producao SEMPRE defina SECRET_KEY no ambiente.
def _gerar_secret_key():
    import secrets
    return secrets.token_urlsafe(48)

SECRET_KEY = os.getenv("SECRET_KEY") or _gerar_secret_key()
ALGORITHM = "HS256"     # algoritmo de criptografia
ACCESS_TOKEN_EXPIRE_MINUTES = 120    # tempo de vida do token

# Contexto para a hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def criar_token_jwt(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def criar_token_jwt_com_expiry(data: dict, minutes: int):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_senha(senha_plana: str, senha_hash: str):
    return pwd_context.verify(senha_plana, senha_hash)

def hash_senha(senha: str):
    return pwd_context.hash(senha)
