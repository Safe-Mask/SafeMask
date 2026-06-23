from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
import mimetypes
from pathlib import Path

from app.database import get_db
from app.core.current_user import get_current_user
from app.models.usuario import Usuario
from app.models.equipe import Equipe
from app.models.documentos import Documento
from app.models.usuario_equipe import UsuarioEquipe
from scanner.scanner import DocumentScanner

router = APIRouter(prefix="/documentos", tags=["Documentos"])

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
    file: UploadFile = File(...),
    titulo: str = Form(...),
    nivel_seguranca: int = Form(1),
    team_id: int = Form(...),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos PDF sao aceitos."
        )

    usuario_equipe = db.query(UsuarioEquipe).filter(
        UsuarioEquipe.user_id == usuario_atual.user_id,
        UsuarioEquipe.team_id == team_id
    ).first()

    if not usuario_equipe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao faz parte dessa equipe."
        )

    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio."
        )

    extensao = Path(file.filename).suffix or ".pdf"
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    nome_arquivo = f"{hash_arquivo}{extensao}"
    caminho_original = ORIGINAIS_DIR / nome_arquivo

    with open(caminho_original, "wb") as f:
        f.write(conteudo)

    try:
        scanner = get_scanner()
        resultado = scanner.scan_and_save(
            file_path=str(caminho_original),
            db=db,
            user_team_id=usuario_equipe.user_team_id,
            nome_original=titulo,
            nivel_seguranca=nivel_seguranca,
            dir_original=ORIGINAIS_DIR,
            dir_censurado=CENSURADOS_DIR
        )

        db.commit()

        return {
            "mensagem": "Documento processado e censurado com sucesso.",
            "doc_id": resultado["doc_id"],
            "hash": resultado["hash"],
            "total_sensiveis": resultado["total_sensiveis"],
            "status": resultado["status"]
        }

    except Exception as e:
        db.rollback()
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Erro ao processar documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar documento: {str(e)}"
        )


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


def buscar_documento_autorizado(db: Session, user_id: int, doc_id: int):
    return (
        db.query(Documento)
        .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
        .filter(
            Documento.doc_id == doc_id,
            UsuarioEquipe.user_id == user_id,
        )
        .first()
    )


@router.get("/censurados")
def listar_documentos_censurados(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
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
        .filter(UsuarioEquipe.user_id == usuario_atual.user_id)
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
    doc_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    documento = buscar_documento_autorizado(db, usuario_atual.user_id, doc_id)

    if not documento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado ou sem acesso.",
        )

    usuario_equipe = (
        db.query(UsuarioEquipe)
        .filter(UsuarioEquipe.user_team_id == documento.user_team_id)
        .first()
    )

    equipe = None
    if usuario_equipe:
        equipe = db.query(Equipe).filter(Equipe.team_id == usuario_equipe.team_id).first()

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
        "equipe": {
            "team_id": equipe.team_id if equipe else None,
            "nome": equipe.nome if equipe else None,
        },
        "preview_url": f"/documentos/censurados/{documento.doc_id}/arquivo",
    }


@router.get("/censurados/{doc_id}/arquivo")
def obter_arquivo_documento_censurado(
    doc_id: int,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    documento = buscar_documento_autorizado(db, usuario_atual.user_id, doc_id)

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

    media_type, _ = mimetypes.guess_type(caminho.name)
    return FileResponse(
        path=str(caminho),
        media_type=media_type or "application/octet-stream",
        filename=f"{documento.nome_original}{documento.extensao}",
        content_disposition_type="inline",
    )

@router.post("/salvar-censurado", status_code=status.HTTP_201_CREATED)
async def salvar_documento_censurado(
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
        
        # Ler arquivo
        conteudo_arquivo = await file.read()
        if not conteudo_arquivo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Arquivo vazio."
            )
        
        # Extrair extensão
        extensao = Path(file.filename).suffix or ".bin"
        
        # Gerar hash do arquivo
        hash_arquivo = gerar_hash_arquivo(conteudo_arquivo)
        
        # Gerar caminho de armazenamento
        nome_arquivo = f"{hash_arquivo}{extensao}"
        caminho_arquivo = CENSURADOS_DIR / nome_arquivo
        
        # Salvar arquivo
        with open(caminho_arquivo, "wb") as f:
            f.write(conteudo_arquivo)
        
        # Salvar documento para cada equipe selecionada
        documentos_criados = []
        
        for team_id in team_ids:
            # Verificar se usuário faz parte da equipe
            usuario_equipe = db.query(UsuarioEquipe).filter(
                UsuarioEquipe.user_id == usuario_atual.user_id,
                UsuarioEquipe.team_id == team_id
            ).first()
            
            if not usuario_equipe:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Você não faz parte da equipe {team_id}."
                )
            
            # Gerar chave criptográfica
            chave_cripto = gerar_chave_criptografica(hash_arquivo, usuario_atual.user_id)
            
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
            detail=f"Erro ao salvar documento: {str(e)}"
        )

@router.get("/listar/{team_id}")
async def listar_documentos_equipe(
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
