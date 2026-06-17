from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from sqlalchemy.orm import Session

from app.schemas.usuario import UsuarioLogin, UsuarioCreate
from app.schemas.auth import RecuperarSenhaRequest
from app.models.usuario import Usuario
from app.models.equipe import Equipe
from app.models.usuario_equipe import UsuarioEquipe
from app.models.cargo import Cargo
from app.core.security import criar_token_jwt, verificar_senha, hash_senha, criar_token_jwt_com_expiry
from app.core.email import enviar_email_recuperacao
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Rota para verificar o login do usuário
@router.post("/login", response_model=dict)
async def login(credenciais: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == credenciais.email).first()

    if not usuario or not verificar_senha(credenciais.senha_hash, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = criar_token_jwt({"sub": usuario.email, "nome": usuario.nome})

    return {"access_token": token, "token_type": "bearer"}

# Rota para cadastrar o usuário
@router.post("/cadastro", status_code=status.HTTP_201_CREATED)
async def cadastrar(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado.",
        )
    
    db_usuario = Usuario (
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=hash_senha(usuario.senha_hash),
        criado_em=datetime.utcnow()
    )

    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)

    # Criar equipe 'Minha equipe'
    db_equipe = Equipe(
        nome="Minha equipe",
        criado_em=datetime.utcnow()
    )
    db.add(db_equipe)
    db.commit()
    db.refresh(db_equipe)

    # Obter cargo 'lider'
    cargo_lider = db.query(Cargo).filter(Cargo.nome == "lider").first()
    if not cargo_lider:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cargo 'lider' não encontrado.",
        )

    # Associar usuário à equipe como lider
    db_usuario_equipe = UsuarioEquipe(
        user_id=db_usuario.user_id,
        team_id=db_equipe.team_id,
        cargo_id=cargo_lider.cargo_id,
        criado_em=datetime.utcnow()
    )
    db.add(db_usuario_equipe)
    db.commit()

    # Gerar token JWT para login automático
    token = criar_token_jwt({"sub": db_usuario.email, "nome": db_usuario.nome})

    return {"mensagem": "Usuário criado com sucesso.", "id": db_usuario.user_id, "access_token": token, "token_type": "bearer"}

# Rota para verificar se email já existe
@router.get("/verificar-email/{email}")
async def verificar_email(email: str, db: Session = Depends(get_db)):
    usuario_existe = db.query(Usuario).filter(Usuario.email == email).first()
    return {"existe": usuario_existe is not None}


@router.post("/recuperar-senha")
async def recuperar_senha(dados: RecuperarSenhaRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email não encontrado.",
        )

    try:
        # Gera token de recuperação com expiry curto (30 minutos)
        token = criar_token_jwt_com_expiry({"sub": usuario.email}, minutes=30)
        enviar_email_recuperacao(usuario.email, usuario.nome, token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível enviar o email de recuperação.",
        ) from exc

    return {"mensagem": "Se o email estiver cadastrado, as instruções de recuperação foram enviadas."}


@router.post('/reset-senha')
async def reset_senha(payload: dict, db: Session = Depends(get_db)):
    token = payload.get('token')
    nova_senha = payload.get('senha')

    if not token or not nova_senha:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Token e nova senha são obrigatórios.')

    try:
        # Decodifica o token para obter o email
        from jose import jwt
        from jose.exceptions import ExpiredSignatureError
        from app.core.security import SECRET_KEY, ALGORITHM

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = decoded.get('sub')
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Token inválido.')

        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Usuário não encontrado.')

        # Atualiza a senha
        usuario.senha_hash = hash_senha(nova_senha)
        db.add(usuario)
        db.commit()

        return {'mensagem': 'Senha atualizada com sucesso.'}
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Token expirado.')
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Token inválido ou erro ao redefinir a senha.') from exc
