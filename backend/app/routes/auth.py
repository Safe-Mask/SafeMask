from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core import tenancy
from app.core.audit import (
    ACAO_CADASTRO,
    ACAO_LOGIN,
    ACAO_LOGIN_BLOQUEADO,
    ACAO_LOGIN_FALHO,
    ACAO_RESET_SENHA,
    ACAO_RESET_SENHA_SOLICITACAO,
    ip_do_cliente,
    registrar,
)
from app.core.config import RESET_TOKEN_EXPIRE_MINUTES
from app.core.current_user import get_current_user
from app.core.email import enviar_email_recuperacao
from app.core.security import (
    TIPO_RESET,
    criar_token_jwt,
    criar_token_jwt_com_expiry,
    hash_senha,
    verificar_senha,
)
from app.database import get_db
from app.models.cargo import Cargo
from app.models.equipe import Equipe
from app.models.log_auditoria import LogAuditoria
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from app.schemas.auth import RecuperarSenhaRequest, ResetSenhaRequest
from app.schemas.usuario import UsuarioCreate, UsuarioLogin

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Limite de tentativas de login. Sem isso, `/auth/login` unlimited + senha
# fraca = credential stuffing. Contagem por e-mail E por IP: uma delas cobre
# o ataque distribuido, a outra o alvo concentrado.
# E-mail da conta que absorve tentativas de login sem cadastro,
# porque `log_auditoria.user_id` nao aceita nulo.
_EMAIL_SENTINEL = "__login_desconhecido__@safemask.invalid"

MAX_TENTATIVAS_LOGIN = 5
JANELA_TENTATIVAS_MINUTOS = 15

# Hash descartavel de senha cualquiera. Faz o bcrypt rodar no caminho de
# "usuario nao encontrado" para que o tempo de resposta nao diferencie os dois.
_HASH_SENHA_QUALQUER = hash_senha("senha-que-nao-existe")


def _registrar_login_falho(
    db: Session, request: Request, user_id: int | None, email: str
) -> None:
    """Grava a tentativa falhada, inclusive para e-mail inexistente.

    `log_auditoria.user_id` tem FK NOT NULL, então o e-mail desconhecido não
    tem linha onde se apoiar. Para continuar contando tentativas por e-mail,
    a tentativa orfa é gravada na conta sentinel `-1`, criada uma vez.
    """
    alvo = user_id
    if alvo is None:
        sentinel = db.query(Usuario).filter(Usuario.email == _EMAIL_SENTINEL).first()
        if sentinel is None:
            sentinel = Usuario(nome="__tentativa_desconhecida__", email=_EMAIL_SENTINEL,
                               senha_hash=_HASH_SENHA_QUALQUER)
            db.add(sentinel)
            try:
                db.commit()
            except Exception:
                db.rollback()
                return
        alvo = sentinel.user_id

    registrar(db, request, alvo, ACAO_LOGIN_FALHO)


def _excedeu_tentativas(db: Session, request: Request, email: str) -> bool:
    """True se o par (e-mail, IP) estourou o limite dentro da janela.

    Falhas anteriores a um login bem-sucedido nao contam. Sem isso, quem
    digita a senha errada duas vezes, acerta na terceira e digita errado de
    novo cinco vezes na mesma hora fica trancado fora da propria conta. O
    `log_auditoria` continua append-only: o corte e por janela de tempo, nao
    apagando registro.
    """
    desde = datetime.utcnow() - timedelta(minutes=JANELA_TENTATIVAS_MINUTOS)
    ip = ip_do_cliente(request)

    ultimo_sucesso = (
        db.query(func.max(LogAuditoria.data_hora))
        .join(Usuario, Usuario.user_id == LogAuditoria.user_id)
        .filter(LogAuditoria.acao == ACAO_LOGIN, Usuario.email == email)
        .scalar()
    )
    if ultimo_sucesso:
        desde = max(desde, ultimo_sucesso)

    falhas = (
        db.query(func.count(LogAuditoria.log_id))
        .join(Usuario, Usuario.user_id == LogAuditoria.user_id)
        .filter(
            LogAuditoria.acao == ACAO_LOGIN_FALHO,
            LogAuditoria.data_hora >= desde,
        )
        .filter(or_(Usuario.email == email, LogAuditoria.ip_origem == ip))
        .scalar()
        or 0
    )
    return falhas > MAX_TENTATIVAS_LOGIN


def cargo_efetivo(db: Session, user_id: int, organizacao_id: int | None = None) -> dict | None:
    """Cargo de maior nivel do usuario entre as equipes da organizacao.

    O papel viaja na resposta do login para o frontend montar o menu. Como um
    usuario pode estar em varias equipes com cargos diferentes, vale o maior
    nivel: esconder itens do menu e cosmético, a autorizacao real acontece em
    cada endpoint.

    Quando `organizacao_id` vem informado, os vinculos de outras organizacoes
    sao ignorados: o papel de um tenant nao pode conceder acesso em outro.
    """
    consulta = (
        db.query(Cargo.nome, Cargo.nivel)
        .join(UsuarioEquipe, UsuarioEquipe.cargo_id == Cargo.cargo_id)
        .filter(UsuarioEquipe.user_id == user_id)
    )
    if organizacao_id is not None:
        consulta = consulta.join(
            Equipe, Equipe.team_id == UsuarioEquipe.team_id
        ).filter(Equipe.organizacao_id == organizacao_id)

    linha = consulta.order_by(Cargo.nivel.desc()).first()
    if not linha:
        return None
    return {"nome": linha.nome, "nivel": linha.nivel}


def identidade(db: Session, usuario: Usuario) -> dict:
    cargo = cargo_efetivo(db, usuario.user_id, usuario.organizacao_id)
    return {
        "user_id": usuario.user_id,
        "nome": usuario.nome,
        "email": usuario.email,
        "organizacao_id": usuario.organizacao_id,
        "organizacao_nome": usuario.organizacao.nome if usuario.organizacao else None,
        # Sem equipe o usuario ainda autenticou, mas nao ha papel para o menu.
        "cargo": cargo["nome"] if cargo else None,
        "nivel": cargo["nivel"] if cargo else 0,
    }


# Rota para verificar o login do usuário
@router.post("/login", response_model=dict)
async def login(
    request: Request,
    credenciais: UsuarioLogin,
    db: Session = Depends(get_db),
):
    usuario = db.query(Usuario).filter(Usuario.email == credenciais.email).first()

    # Sem este, um e-mail inexistente responderia ~100ms mais rapido que um
    # existente: o bcrypt so roda no segundo caso, e a diferenca de tempo
    # enumera cadastros mesmo sem `/verificar-email`.
    if usuario is None:
        verificar_senha(credenciais.senha_hash, _HASH_SENHA_QUALQUER)
        _registrar_login_falho(db, request, None, credenciais.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verificar_senha(credenciais.senha_hash, usuario.senha_hash):
        _registrar_login_falho(db, request, usuario.user_id, credenciais.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if _excedeu_tentativas(db, request, credenciais.email):
        registrar(db, request, usuario.user_id, ACAO_LOGIN_BLOQUEADO)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde alguns minutos.",
        )

    registrar(db, request, usuario.user_id, ACAO_LOGIN)
    token = criar_token_jwt(
        {"sub": usuario.email, "nome": usuario.nome, "tv": usuario.token_version or 0}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": identidade(db, usuario),
    }


@router.get("/me", response_model=dict)
async def me(
    usuario_atual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Identidade e cargo do portador do token.

    Permite reidratar a sessao (por exemplo apos um deploy) sem refazer login.
    """
    return identidade(db, usuario_atual)

# Rota para cadastrar o usuário
@router.post("/cadastro", status_code=status.HTTP_201_CREATED)
async def cadastrar(
    request: Request,
    usuario: UsuarioCreate,
    db: Session = Depends(get_db),
):
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado.",
        )

    # Cada cadastro publico abre uma organizacao propria. Sem isso o usuario
    # novo cairia na organizacao legada e enxergaria dados de outros clientes.
    # `criar`, e nao `buscar_ou_criar`: o nome e rotulo, e duas Ana Silva de
    # empresas diferentes caem em tenants distintos.
    organizacao = tenancy.criar(db, f"Organização de {usuario.nome.strip()}")

    db_usuario = Usuario (
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=hash_senha(usuario.senha_hash),
        organizacao_id=organizacao.organizacao_id,
        criado_em=datetime.utcnow()
    )

    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)

    # Criar equipe 'Minha equipe'
    db_equipe = Equipe(
        nome="Minha equipe",
        organizacao_id=organizacao.organizacao_id,
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

    registrar(db, request, db_usuario.user_id, ACAO_CADASTRO)

    # Gerar token JWT para login automático
    token = criar_token_jwt({"sub": db_usuario.email, "nome": db_usuario.nome, "tv": 0})

    return {
        "mensagem": "Usuário criado com sucesso.",
        "id": db_usuario.user_id,
        "access_token": token,
        "token_type": "bearer",
        # Mesmo formato do login: o frontend usa para montar a sessao sem
        # inferir nome pelo e-mail.
        "user": identidade(db, db_usuario),
    }

@router.post("/recuperar-senha")
async def recuperar_senha(
    request: Request,
    dados: RecuperarSenhaRequest,
    db: Session = Depends(get_db),
):
    """Envia as instrucoes de recuperacao.

    A resposta e sempre a mesma, exista o email ou nao: responder 404 para um
    cadastro desconhecido permitiria enumerar quem usa o sistema.
    """
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if not usuario:
        return {
            "mensagem": "Se o email estiver cadastrado, as instruções de recuperação foram enviadas."
        }

    registrar(db, request, usuario.user_id, ACAO_RESET_SENHA_SOLICITACAO)

    try:
        token = criar_token_jwt_com_expiry(
            {"sub": usuario.email}, minutes=RESET_TOKEN_EXPIRE_MINUTES
        )
        enviar_email_recuperacao(usuario.email, usuario.nome, token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recuperação de senha indisponível no momento.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível enviar o email de recuperação.",
        ) from exc

    return {"mensagem": "Se o email estiver cadastrado, as instruções de recuperação foram enviadas."}


@router.post('/reset-senha')
async def reset_senha(request: Request, payload: ResetSenhaRequest, db: Session = Depends(get_db)):
    token = payload.token
    nova_senha = payload.senha

    try:
        # Decodifica o token para obter o email
        from jose import jwt
        from jose.exceptions import ExpiredSignatureError

        from app.core.security import ALGORITHM, SECRET_KEY

        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Um access token decodifica aqui igual. Sem o `typ`, o token de sessao
        # da vitima — que anda no localStorage e vaza em qualquer XSS — viraria
        # senha permanente.
        if decoded.get("typ") != TIPO_RESET:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido.",
            )

        email = decoded.get('sub')
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Token inválido.')

        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Usuário não encontrado.')

        # Atualiza a senha
        usuario.senha_hash = hash_senha(nova_senha)
        # Invalida todo access token emitido antes desta troca: sem isso quem
        # roubou a senha antiga continua autenticado depois da troca.
        usuario.token_version = (usuario.token_version or 0) + 1
        db.add(usuario)
        db.commit()

        registrar(db, request, usuario.user_id, ACAO_RESET_SENHA)

        return {'mensagem': 'Senha atualizada com sucesso.'}
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado."
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Token inválido ou erro ao redefinir a senha.') from exc
