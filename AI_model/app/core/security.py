# Funções para configurar o JWT de autenticação e hash de senhas

from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-padrao")    # chave para assinar
ALGORITHM = "HS256"     # algoritmo de criptografia
ACCESS_TOKEN_EXPIRE_MINUTES = 120    # tempo de vida do token

# Contexto para a hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def criar_token_jwt(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_senha(senha_plana: str, senha_hash: str):
    return pwd_context.verify(senha_plana, senha_hash)

def hash_senha(senha: str):
    return pwd_context.hash(senha)
