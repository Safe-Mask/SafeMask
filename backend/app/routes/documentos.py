import hashlib
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.core import tenancy
from app.core.audit import (
    ACAO_LISTAR_DOCUMENTOS,
    ACAO_UPLOAD,
    ACAO_UPLOAD_CENSURADO,
    ACAO_VER_CENSURADO,
    ACAO_VER_ORIGINAL,
    ACAO_VER_PARCIAL,
    registrar,
)
from app.core.autorizacao import NIVEL_MIN_DESCENSURA, cargo_na_equipe
from app.core.current_user import get_current_user
from app.core.file_responses import responder_arquivo
from app.core.uploads import ler_e_validar_upload
from app.database import get_db
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from scanner.coordenadas import ESPACO_PDF
from scanner.scanner import DocumentScanner, NenhumaMascaraAplicavel

router = APIRouter(prefix="/documentos", tags=["Documentos"])
logger = logging.getLogger(__name__)

# Criar diretórios de uploads se não existir
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
ORIGINAIS_DIR = UPLOAD_DIR / "originais"
CENSURADOS_DIR = UPLOAD_DIR / "censurados"
ORIGINAIS_DIR.mkdir(parents=True, exist_ok=True)
CENSURADOS_DIR.mkdir(parents=True, exist_ok=True)

scanner_instance = None

def get_scanner():
    global scanner_instance
    if scanner_instance is None:
        scanner_instance = DocumentScanner()
    return scanner_instance


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_documento(
    request: Request,
    file: UploadFile = File(...),
    titulo: str = Form(...),
    nivel_seguranca: int = Form(1),
    teams: str = Form(...),  # JSON array de team_ids como string
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    team_ids = normalizar_team_ids(teams)

    if nivel_seguranca < 1 or nivel_seguranca > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nível de segurança inválido (1-4)."
        )

    usuario_equipes = (
        db.query(UsuarioEquipe)
        .filter(
            UsuarioEquipe.user_id == usuario_atual.user_id,
            UsuarioEquipe.team_id.in_(team_ids)
        )
        .all()
    )
    if not usuario_equipes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao faz parte de nenhuma das equipes selecionadas."
        )

    conteudo, caminho_nome = await ler_e_validar_upload(file, Path(file.filename or ""))
    extensao = caminho_nome.suffix or ".pdf"
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    nome_arquivo = f"{hash_arquivo}{extensao}"
    caminho_original = ORIGINAIS_DIR / nome_arquivo

    with open(caminho_original, "wb") as f:
        f.write(conteudo)

    try:
        # O scanner roda UMA vez e gera o PDF tarjado a partir do primeiro vínculo.
        resultado = get_scanner().scan_and_save(
            file_path=str(caminho_original),
            db=db,
            user_team_id=usuario_equipes[0].user_team_id,
            nome_original=titulo,
            nivel_seguranca=nivel_seguranca,
            dir_original=ORIGINAIS_DIR,
            dir_censurado=CENSURADOS_DIR
        )

        # Compartilha o mesmo documento com as demais equipes selecionadas.
        chave_cripto = gerar_chave_criptografica(hash_arquivo, usuario_atual.user_id)
        docs_compartilhados = []
        for usuario_equipe in usuario_equipes[1:]:
            doc_compartilhado = Documento(
                user_team_id=usuario_equipe.user_team_id,
                nome_original=titulo,
                extensao=extensao.replace(".", ""),
                tamanho_bytes=len(conteudo),
                nivel_seguranca=nivel_seguranca,
                chave_criptografica=chave_cripto,
                hash_documento=hash_arquivo,
                caminho_storage=str(CENSURADOS_DIR / f"{hash_arquivo}_tarjado.pdf"),
                status_processamento="CONCLUIDO"
            )
            db.add(doc_compartilhado)
            docs_compartilhados.append(doc_compartilhado)

        # Sem o flush, as copias ainda nao tem doc_id para receber os itens.
        db.flush()

        # Os itens sensiveis sao vinculados ao doc_id de quem fez o upload.
        # Sem esta copia, /parcial de uma equipe secundaria nao acha nada a
        # cobrir e devolve o PDF original sem censura.
        duplicar_itens_sensiveis(db, resultado["doc_id"], docs_compartilhados)

        db.commit()
        registrar(db, request, usuario_atual.user_id, ACAO_UPLOAD)

        return {
            "mensagem": "Documento processado e censurado com sucesso.",
            "doc_id": resultado["doc_id"],
            "hash": resultado["hash"],
            "total_sensiveis": resultado["total_sensiveis"],
            "cpf_censurados": resultado["cpf_censurados"],
            "status": resultado["status"]
        }

    except Exception as e:
        db.rollback()
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Erro ao processar documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar documento."
        ) from e


def normalizar_team_ids(teams: str) -> list[int]:
    import json

    try:
        parsed_teams = json.loads(teams)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teams deve ser um array JSON válido.",
        ) from exc

    if not isinstance(parsed_teams, list) or not parsed_teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Teams deve conter ao menos um id de equipe.",
        )

    team_ids: list[int] = []
    for team in parsed_teams:
        try:
            team_ids.append(int(team))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teams deve ser um array JSON de ids válidos.",
            ) from exc

    return team_ids

def gerar_hash_arquivo(conteudo: bytes) -> str:
    """Gera hash SHA256 do arquivo."""
    return hashlib.sha256(conteudo).hexdigest()

def gerar_chave_criptografica(arquivo_hash: str, user_id: int) -> str:
    """Gera uma chave criptográfica baseada no hash e user_id."""
    chave_base = f"{arquivo_hash}:{user_id}:{datetime.utcnow().isoformat()}"
    return hashlib.sha256(chave_base.encode()).hexdigest()


def caminho_armazenado(documento: Documento) -> Path:
    """Caminho do PDF tarjado de um documento, com fallback por hash."""
    if documento.caminho_storage:
        caminho = Path(documento.caminho_storage)
        if caminho.is_file():
            return caminho

    candidatos = sorted(CENSURADOS_DIR.glob(f"{documento.hash_documento}*"))
    if not candidatos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo censurado nao encontrado no armazenamento.",
        )
    return candidatos[0]


def duplicar_itens_sensiveis(db: Session, doc_id_origem: int, documentos_destino: list[Documento]) -> int:
    """Replica os DadoSensivel de um documento para outros Documento copias.

    Documento e uma linha por (arquivo, equipe). DadoSensivel aponta para
    doc_id, entao cada copia precisa dos proprios itens para que a descensura
    por cargo funcione igual em todas as equipes.
    """
    itens = db.query(DadoSensivel).filter(DadoSensivel.doc_id == doc_id_origem).all()
    if not itens:
        return 0

    copiados = 0
    for doc_destino in documentos_destino:
        for item in itens:
            db.add(
                DadoSensivel(
                    doc_id=doc_destino.doc_id,
                    tipo_entidade=item.tipo_entidade,
                    conteudo_hash=item.conteudo_hash,
                    pagina=item.pagina,
                    coordenadas=item.coordenadas,
                    nivel_requerido=item.nivel_requerido,
                )
            )
            copiados += 1
    db.flush()
    return copiados


def equipe_do_documento(db: Session, documento: Documento) -> Equipe | None:
    """Equipe dona do documento, sem atravessar o tenant.

    `Documento.user_team_id` aponta para o vinculo de equipe, nao para a
    equipe; e o primeiro membro desse vinculo que revelava o `team_id`. Um
    vinculo apontando para equipe de outra organizacao nao resolve.
    """
    return (
        db.query(Equipe)
        .join(UsuarioEquipe, UsuarioEquipe.team_id == Equipe.team_id)
        .filter(UsuarioEquipe.user_team_id == documento.user_team_id)
        .distinct()
        .first()
    )


def buscar_documento_autorizado(db: Session, usuario: Usuario, doc_id: int) -> Documento | None:
    """Documento, ou None se o usuario nao puder nem ve-lo.

    Membro de outra equipe/organizacao recebe `None` (a rota transforma em
    404), nunca 403: responder "proibido" confirmaria que o documento existe.
    """
    documento = db.query(Documento).filter(Documento.doc_id == doc_id).first()
    if not documento:
        return None

    equipe = equipe_do_documento(db, documento)
    if not equipe:
        return None

    organizacao_id = tenancy.exigir_organizacao(usuario)
    if equipe.organizacao_id != organizacao_id:
        return None

    return documento if cargo_na_equipe(db, usuario, equipe.team_id) else None

@router.get("/censurados")
def listar_documentos_censurados(
    request: Request,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    team_ids = [
        row.team_id
        for row in (
            db.query(UsuarioEquipe.team_id)
            .filter(UsuarioEquipe.user_id == usuario_atual.user_id)
            .distinct()
            .all()
        )
    ]

    if not team_ids:
        return {
            "usuario": {
                "user_id": usuario_atual.user_id,
                "nome": usuario_atual.nome,
                "email": usuario_atual.email,
            },
            "total": 0,
            "documentos": [],
        }

    documentos = (
        db.query(
            Documento.doc_id,
            Documento.nome_original,
            Documento.extensao,
            Documento.nivel_seguranca,
            Documento.criado_em,
            Documento.tamanho_bytes,
            Equipe.team_id,
            Equipe.nome.label("equipe_nome"),
            UsuarioEquipe.user_team_id,
        )
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .join(Equipe, Equipe.team_id == UsuarioEquipe.team_id)
        .filter(UsuarioEquipe.team_id.in_(team_ids))
        .order_by(Documento.criado_em.desc())
        .all()
    )

    return {
        "usuario": {
            "user_id": usuario_atual.user_id,
            "nome": usuario_atual.nome,
            "email": usuario_atual.email,
        },
        "total": len(documentos),
        "documentos": [
            {
                "doc_id": row.doc_id,
                "nome_original": row.nome_original,
                "extensao": row.extensao,
                "nivel_seguranca": row.nivel_seguranca,
                "tamanho_bytes": row.tamanho_bytes,
                "criado_em": row.criado_em.isoformat() if row.criado_em else None,
                "team_id": row.team_id,
                "equipe_nome": row.equipe_nome,
                "user_team_id": row.user_team_id,
            }
            for row in documentos
        ],
    }


@router.get("/censurados/{doc_id}")
def obter_documento_censurado(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    documento = buscar_documento_autorizado(db, usuario_atual, doc_id)

    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado ou sem acesso.",
        )

    equipe = equipe_do_documento(db, documento)
    autor = None
    if equipe:
        primeiro_membro = (
            db.query(Usuario)
            .join(UsuarioEquipe, UsuarioEquipe.user_id == Usuario.user_id)
            .filter(UsuarioEquipe.team_id == equipe.team_id)
            .order_by(UsuarioEquipe.user_team_id)
            .first()
        )
        autor = primeiro_membro

    cargo = cargo_na_equipe(db, usuario_atual, equipe.team_id) if equipe else None

    registrar(db, request, usuario_atual.user_id, ACAO_VER_CENSURADO)

    return {
        "doc_id": documento.doc_id,
        "nome_original": documento.nome_original,
        "extensao": documento.extensao,
        "tamanho_bytes": documento.tamanho_bytes,
        "nivel_seguranca": documento.nivel_seguranca,
        "chave_criptografica": documento.chave_criptografica,
        "hash_documento": documento.hash_documento,
        "caminho_storage": documento.caminho_storage,
        "criado_em": documento.criado_em.isoformat() if documento.criado_em else None,
        "status_processamento": documento.status_processamento,
        "autor_nome": autor.nome if autor else None,
        "equipe": {
            "team_id": equipe.team_id if equipe else None,
            "nome": equipe.nome if equipe else None,
        },
        "cargo_usuario": cargo,
        "pode_descensurar": bool(cargo and cargo["nivel"] >= NIVEL_MIN_DESCENSURA),
        "pode_descensura_parcial": bool(cargo),
        "preview_url": f"/documentos/censurados/{documento.doc_id}/arquivo",
    }


@router.get("/censurados/{doc_id}/arquivo")
def obter_arquivo_documento_censurado(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    documento = buscar_documento_autorizado(db, usuario_atual, doc_id)

    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado ou sem acesso.",
        )

    caminho = Path(documento.caminho_storage)
    if not caminho.is_absolute():
        caminho = Path.cwd() / caminho

    if not caminho.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo físico não encontrado.",
        )

    registrar(db, request, usuario_atual.user_id, ACAO_VER_CENSURADO)
    return responder_arquivo(
        caminho,
        f"{documento.nome_original}{documento.extensao}",
        inline=True,
    )


@router.get("/{doc_id}/original")
def obter_documento_original(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Retorna o PDF original (sem censura) para usuarios com cargo de nivel
    suficiente (ex.: lider). Membros recebem 403.
    """
    documento = buscar_documento_autorizado(db, usuario_atual, doc_id)

    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado ou sem acesso.",
        )

    equipe = equipe_do_documento(db, documento)
    cargo = cargo_na_equipe(db, usuario_atual, equipe.team_id) if equipe else None
    if not cargo or cargo["nivel"] < NIVEL_MIN_DESCENSURA:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu cargo nao permite acessar a versao original do documento.",
        )

    # O original foi salvo como {hash_arquivo}{extensao} em ORIGINAIS_DIR.
    candidatos = list(ORIGINAIS_DIR.glob(f"{documento.hash_documento}*"))
    if not candidatos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo original nao encontrado no armazenamento.",
        )

    caminho = candidatos[0]
    registrar(db, request, usuario_atual.user_id, ACAO_VER_ORIGINAL)
    return responder_arquivo(
        caminho,
        f"{documento.nome_original}_original.pdf",
    )


@router.get("/{doc_id}/parcial")
def obter_documento_parcial(
    request: Request,
    doc_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """Descensura parcial por cargo.

    Revela os dados sensiveis cujo nivel_requerido <= cargo.nivel do usuario;
    os itens de nivel acima continuam cobertos. O lider (nivel >=
    NIVEL_MIN_DESCENSURA) recebe o documento original integral.
    """
    documento = buscar_documento_autorizado(db, usuario_atual, doc_id)
    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado ou sem acesso.",
        )

    equipe = equipe_do_documento(db, documento)
    cargo = cargo_na_equipe(db, usuario_atual, equipe.team_id) if equipe else None
    if not cargo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao faz parte da equipe deste documento.",
        )

    # Lider (ou cargo de nivel suficiente) recebe o original integral.
    if cargo["nivel"] >= NIVEL_MIN_DESCENSURA:
        candidatos = list(ORIGINAIS_DIR.glob(f"{documento.hash_documento}*"))
        if not candidatos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo original nao encontrado no armazenamento.",
            )
        caminho = candidatos[0]
        registrar(db, request, usuario_atual.user_id, ACAO_VER_ORIGINAL)
        return responder_arquivo(
            caminho,
            f"{documento.nome_original}_original.pdf",
        )

    nivel = cargo["nivel"]

    # Itens que devem permanecer cobertos para este nivel de acesso.
    itens = (
        db.query(DadoSensivel)
        .filter(
            DadoSensivel.doc_id == documento.doc_id,
            DadoSensivel.nivel_requerido > nivel,
        )
        .all()
    )

    # (coordenadas, espaco): o espaco ve de DadoSensivel. Sem ele, as caixas de
    # uma pagina escaneada (pixels) seriam reprojetadas como pontos do PDF e a
    # tarja sairia deslocada — o dado ficaria visivel na descensura parcial.
    itens_para_cobrir: dict = {}
    for item in itens:
        itens_para_cobrir.setdefault(item.pagina, []).append(
            (item.coordenadas, item.espaco_coordenadas or ESPACO_PDF)
        )

    caminhos_originais = list(ORIGINAIS_DIR.glob(f"{documento.hash_documento}*"))
    if not caminhos_originais:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo original nao encontrado no armazenamento.",
        )

    # Nenhum item acima do nivel do usuario: nao ha regiao a cobrir, mas
    # entregamos a versao tarjada. Servir o original aqui vazaria o documento
    # sempre que o scan nao encontrou nada.
    if not itens_para_cobrir:
        caminho_censurado = caminho_armazenado(documento)
        registrar(db, request, usuario_atual.user_id, ACAO_VER_PARCIAL)
        return responder_arquivo(
            caminho_censurado,
            f"{documento.nome_original}_censurado.pdf",
        )

    try:
        nome_saida = f"{documento.hash_documento}_parcial_nivel{nivel}.pdf"
        caminho_parcial = get_scanner().gerar_pdf_parcial(
            file_path=str(caminhos_originais[0]),
            itens_para_cobrir=itens_para_cobrir,
            dir_destino=CENSURADOS_DIR,
            nome_saida=nome_saida,
        )
    except NenhumaMascaraAplicavel:
        # Havia item a cobrir, mas nenhuma caixa era utilizavel. Servir o
        # parcial assim seria o original sem nenhuma tarja; a versao
        # integralmente censurada e mais restritiva e ainda entrega algo
        # honesto ao usuario.
        logger.warning(
            f"Doc {documento.doc_id}: nenhuma caixa aplicavel na descensura "
            "parcial; servindo a versao censurada."
        )
        registrar(db, request, usuario_atual.user_id, ACAO_VER_PARCIAL)
        return responder_arquivo(
            caminho_armazenado(documento),
            f"{documento.nome_original}_censurado.pdf",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao gerar a descensura parcial.",
        ) from e

    registrar(db, request, usuario_atual.user_id, ACAO_VER_PARCIAL)
    return responder_arquivo(
        caminho_parcial,
        f"{documento.nome_original}_parcial_nivel{nivel}.pdf",
    )


@router.post("/salvar-censurado", status_code=status.HTTP_201_CREATED)
async def salvar_documento_censurado(
    request: Request,
    file: UploadFile = File(...),
    titulo: str = Form(...),
    nivel_seguranca: int = Form(...),
    observacoes: str = Form(""),
    teams: str = Form(...),  # JSON array de team_ids como string
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Salva um documento censurado nas equipes selecionadas.

    - file: arquivo do documento
    - titulo: nome final do documento
    - nivel_seguranca: nível de proteção (1-4)
    - observacoes: notas internas
    - teams: array JSON de team_ids (ex: "[1, 2, 3]")
    """

    try:
        team_ids = normalizar_team_ids(teams)

        # Validar nível de segurança
        if nivel_seguranca < 1 or nivel_seguranca > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nível de segurança inválido (1-4)."
            )

        # Ler e validar arquivo
        conteudo_arquivo, caminho_nome = await ler_e_validar_upload(
            file, Path(file.filename or "")
        )

        extensao = caminho_nome.suffix or ".pdf"

        # Gerar hash do arquivo
        hash_arquivo = gerar_hash_arquivo(conteudo_arquivo)

        # Gerar caminho de armazenamento
        nome_arquivo = f"{hash_arquivo}{extensao}"
        caminho_arquivo = CENSURADOS_DIR / nome_arquivo

        # Validar TODAS as equipes antes de gravar qualquer coisa em disco:
        # caso contrario um 403 no meio do loop deixa arquivo orfao no storage.
        vinculos = []
        for team_id in team_ids:
            usuario_equipe = db.query(UsuarioEquipe).filter(
                UsuarioEquipe.user_id == usuario_atual.user_id,
                UsuarioEquipe.team_id == team_id
            ).first()

            if not usuario_equipe:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Você não faz parte da equipe {team_id}."
                )
            vinculos.append(usuario_equipe)

        # Salvar arquivo
        with open(caminho_arquivo, "wb") as f:
            f.write(conteudo_arquivo)

        # Salvar documento para cada equipe selecionada
        documentos_criados = []
        chave_cripto = gerar_chave_criptografica(hash_arquivo, usuario_atual.user_id)

        for team_id, usuario_equipe in zip(team_ids, vinculos, strict=True):
            # Criar registro de Documento
            novo_documento = Documento(
                user_team_id=usuario_equipe.user_team_id,
                nome_original=titulo,
                extensao=extensao,
                tamanho_bytes=len(conteudo_arquivo),
                nivel_seguranca=nivel_seguranca,
                chave_criptografica=chave_cripto,
                hash_documento=hash_arquivo,
                caminho_storage=str(caminho_arquivo),
                status_processamento="CONCLUIDO"
            )

            db.add(novo_documento)
            documentos_criados.append({
                "team_id": team_id,
                "titulo": titulo,
                "nivel_seguranca": nivel_seguranca
            })

        # Commit único para todas as mudanças
        db.commit()
        registrar(db, request, usuario_atual.user_id, ACAO_UPLOAD_CENSURADO)

        return {
            "mensagem": "Documento censurado salvo com sucesso.",
            "arquivo_hash": hash_arquivo,
            "documentos_criados": len(documentos_criados),
            "detalhes": documentos_criados
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao salvar documento."
        ) from e

@router.get("/listar/{team_id}")
async def listar_documentos_equipe(
    request: Request,
    team_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """
    Lista documentos de uma equipe específica.
    """

    # Verificar se usuário faz parte da equipe
    usuario_equipe_list = db.query(UsuarioEquipe).filter(
        UsuarioEquipe.user_id == usuario_atual.user_id,
        UsuarioEquipe.team_id == team_id
    ).all()

    if not usuario_equipe_list:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não faz parte dessa equipe."
        )

    # Listar documentos
    user_team_ids = [ue.user_team_id for ue in usuario_equipe_list]
    documentos = db.query(Documento).filter(
        Documento.user_team_id.in_(user_team_ids)
    ).all()

    registrar(db, request, usuario_atual.user_id, ACAO_LISTAR_DOCUMENTOS)

    return {
        "total": len(documentos),
        "documentos": [
            {
                "doc_id": d.doc_id,
                "nome": d.nome_original,
                "tamanho": d.tamanho_bytes,
                "nivel_seguranca": d.nivel_seguranca,
                "status": d.status_processamento,
                "criado_em": d.criado_em
            }
            for d in documentos
        ]
    }
