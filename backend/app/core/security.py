# Funções para configurar o JWT de autenticação e hash de senhas

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from jose import jwt
from passlib.context import CryptContext

# Carrega as variáveis do arquivo .env
load_dotenv()

# Chave para assinar tokens. Em producao SEMPRE defina SECRET_KEY no ambiente.
def _gerar_secret_key():
    import secrets
    return secrets.token_urlsafe(48)


def _ambiente_de_desenvolvimento() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() in {
        "development", "dev", "test", "testing", "local",
    }


def _resolver_secret_key() -> str:
    """Lê SECRET_KEY do ambiente, ou recusa subir fora de desenvolvimento.

    Sem a variavel, cada processo gerava uma chave aleatoria different. Nao e
    quebra criptografica — ninguem adivinha — mas e uma falha silenciosa e
    dificil de diagnosticar: um token emitido por uma instancia e rejeitado
    por outra, entao todo usuario desloga sozinho a cada deploy. Como o
    aplicativo "funciona", ninguem percebe que faltou configurar.
    """
    configurada = os.getenv("SECRET_KEY")
    if configurada:
        return configurada

    if not _ambiente_de_desenvolvimento():
        raise RuntimeError(
            "SECRET_KEY nao definida e ENVIRONMENT nao e de desenvolvimento. "
            "Defina SECRET_KEY no ambiente: sem ela, cada instancia assina "
            "tokens com chave propria e toda sessao morre a cada restart."
        )

    return _gerar_secret_key()


SECRET_KEY = _resolver_secret_key()
ALGORITHM = "HS256"     # algoritmo de criptografia
ACCESS_TOKEN_EXPIRE_MINUTES = 120    # tempo de vida do token

# Assinatura sozinha nao distingue um token de outro: um token de acesso
# valido decodifica no `/auth/reset-senha` e vira uma senha permanente. O
# claim `typ` separa os dois usos, e cada rota exige o seu.
TIPO_ACCESS = "access"
TIPO_RESET = "reset"

# Contexto para a hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def criar_token_jwt(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # `tv` e a versao de senha com que o token foi emitido. O default 0
    # mantem valido quem monta token direto (testes, scripts); o login passa a
    # versao real do usuario.
    to_encode.setdefault("tv", 0)
    to_encode.update({"exp": expire, "typ": TIPO_ACCESS})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def criar_token_jwt_com_expiry(data: dict, minutes: int, tipo: str = TIPO_RESET):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    to_encode.update({"exp": expire, "typ": tipo})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verificar_senha(senha_plana: str, senha_hash: str):
    return pwd_context.verify(senha_plana, senha_hash)

def hash_senha(senha: str):
    return pwd_context.hash(senha)
