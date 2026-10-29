import hashlib
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.core import cifra, fila, politica_niveis, tenancy
from app.core.audit import (
    ACAO_LISTAR_DOCUMENTOS,
    ACAO_UPLOAD,
    ACAO_UPLOAD_LOTE,
    ACAO_VER_CENSURADO,
    ACAO_VER_ORIGINAL,
    ACAO_VER_PARCIAL,
    RESULTADO_FALHA,
    RESULTADO_NEGADO,
    registrar,
)
from app.core.autorizacao import NIVEL_MIN_DESCENSURA, cargo_na_equipe
from app.core.current_user import get_current_user
from app.core.datas import iso_utc
from app.core.file_responses import responder_arquivo
from app.core.uploads import ler_e_validar_upload
from app.database import get_db
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe
from scanner.coordenadas import ESPACO_PDF
from scanner.scanner import DocumentScanner, NenhumaMascaraAplicavel, OcrIndisponivel

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

    if len(team_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Documento tem um dono unico: informe uma equipe so."
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
        registrar(
            db, request, usuario_atual.user_id, ACAO_UPLOAD,
            team_id=team_ids[0], resultado=RESULTADO_NEGADO,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao faz parte da equipe selecionada."
        )

    conteudo, caminho_nome = await ler_e_validar_upload(file, Path(file.filename or ""))
    extensao = caminho_nome.suffix or ".pdf"
    hash_arquivo = hashlib.sha256(conteudo).hexdigest()
    nome_arquivo = f"{hash_arquivo}{extensao}"
    caminho_original = ORIGINAIS_DIR / nome_arquivo

    # O original em disco NASCE cifrado (Fase 3.1): o plaintext vive so no
    # request (aqui) e na copia temporaria de scan, dentro do finally.
    cifra.gravar_original_cifrado(caminho_original, conteudo)

    niveis_principal = politica_niveis.niveis_da_equipe(db, usuario_equipes[0].team_id)
    try:
        arquivo_scan = cifra.materializar_original_para_leitura(caminho_original)
        try:
            # O scanner roda UMA vez e gera o PDF tarjado a partir do primeiro vínculo.
            resultado = get_scanner().scan_and_save(
                file_path=str(arquivo_scan),
                db=db,
                user_team_id=usuario_equipes[0].user_team_id,
                nome_original=titulo,
                nivel_seguranca=nivel_seguranca,
                dir_original=ORIGINAIS_DIR,
                dir_censurado=CENSURADOS_DIR,
                # Nivel exigido de cada tipo de dado: politica da equipe de destino.
                niveis=niveis_principal,
            )
        finally:
            cifra.descartar_material_temporario(arquivo_scan, caminho_original)

        # Confirmacoes do scan ficam visiveis roda queries seguintes.
        db.flush()

        # O scanner tira a extensao do `nome_original`, que aqui e o titulo
        # digitado e nao tem extensao: o principal ficava com ela vazia.
        db.query(Documento).filter(Documento.doc_id == resultado["doc_id"]).update(
            {Documento.extensao: extensao.lstrip(".").lower()}, synchronize_session=False
        )

        db.commit()
        registrar(db, request, usuario_atual.user_id, ACAO_UPLOAD, documento=db.get(Documento, resultado["doc_id"]))

        return {
            "mensagem": "Documento processado e censurado com sucesso.",
            "doc_id": resultado["doc_id"],
            "hash": resultado["hash"],
            "total_sensiveis": resultado["total_sensiveis"],
            "cpf_censurados": resultado["cpf_censurados"],
            "status": resultado["status"]
        }

    except OcrIndisponivel as e:
        # Falta de instalacao no servidor, nao defeito do arquivo: o usuario
        # recebe o motivo em vez do "Erro ao processar documento" generico.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e

    except Exception as e:
        db.rollback()
        logger = __import__('logging').getLogger(__name__)
        logger.error(f"Erro ao processar documento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar documento."
        ) from e


def nome_para_download(nome: str, extensao: str | None) -> str:
    """Nome do arquivo entregue: `<titulo>.<extensao>`.

    A extensao e gravada sem ponto; o titulo digitado normalmente nao tem
    extensao, mas o nome tirado do arquivo pode ja terminar com ela.
    """
    extensao = (extensao or "").lstrip(".")
    if not extensao or nome.lower().endswith(f".{extensao.lower()}"):
        return nome
    return f"{nome}.{extensao}"


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

    # `teams=[1, 1]` criava dois Documentos apontando para o mesmo
    # user_team_id e o mesmo arquivo.
    return sorted(set(team_ids))

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

    candidatos = [
        item for item in sorted(CENSURADOS_DIR.glob(f"{documento.hash_documento}*"))
        # O glob por hash alcanca tambem versoes parciais em cache (que tem
        # `_parcial_` no nome): elas nao sao a versao integralmente censurada.
        if "_parcial_" not in item.name
    ]
    if not candidatos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo censurado nao encontrado no armazenamento.",
        )
    return candidatos[0]


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
    documento = db.query(Documento).filter(
        Documento.doc_id == doc_id,
        # `ativo` era o soft-delete previsto e nenhuma rota o lia: um documento
        # arquivado continuaria sendo servido e listado.
        Documento.ativo.is_(True),
    ).first()
    if not documento:
        return None

    equipe = equipe_do_documento(db, documento)
    if not equipe:
        return None

    organizacao_id = tenancy.exigir_organizacao(usuario)
    if equipe.organizacao_id != organizacao_id:
        return None

    return documento if cargo_na_equipe(db, usuario, equipe.team_id) else None


def registrar_acesso_negado(db: Session, request, usuario: Usuario, doc_id: int, acao: str) -> None:
    """Registra a tentativa de quem e da organizacao mas nao da equipe do documento.

    Documento inexistente ou de outra organizacao nao gera evento: o
    historico da organizacao dona nao deve receber nomes de outra empresa, e
    para quem tentou a resposta continua 404.
    """
    documento = db.query(Documento).filter(Documento.doc_id == doc_id).first()
    if not documento:
        return
    equipe = equipe_do_documento(db, documento)
    if not equipe or equipe.organizacao_id != usuario.organizacao_id:
        return
    registrar(
        db, request, usuario.user_id, acao,
        documento=documento, team_id=equipe.team_id, resultado=RESULTADO_NEGADO,
    )

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

    registrar(
        db, request, usuario_atual.user_id, ACAO_LISTAR_DOCUMENTOS,
        detalhe="censurados",
    )

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
                "criado_em": iso_utc(row.criado_em),
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
        registrar_acesso_negado(db, request, usuario_atual, doc_id, ACAO_VER_CENSURADO)
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

    registrar(db, request, usuario_atual.user_id, ACAO_VER_CENSURADO, documento=documento)

    return {
        "doc_id": documento.doc_id,
        "nome_original": documento.nome_original,
        "extensao": documento.extensao,
        "tamanho_bytes": documento.tamanho_bytes,
        "nivel_seguranca": documento.nivel_seguranca,
        # `hash_documento` e `caminho_storage` ficam no servidor. O hash e a
        # chave de glob que localiza os arquivos (documentos.py:458 e ss.), e o
        # caminho entrega o layout do disco: quem tem documento teu nao tem por
        # que saber onde ele mora. `chave_criptografica` segue exposta porque a
        # tela a mostra, mas nenhum caminho do codigo criptografa com ela.
        "chave_criptografica": documento.chave_criptografica,
        "criado_em": iso_utc(documento.criado_em),
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
        registrar_acesso_negado(db, request, usuario_atual, doc_id, ACAO_VER_CENSURADO)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo não encontrado ou sem acesso.",
        )

    caminho = Path(documento.caminho_storage)
    if not caminho.is_absolute():
        caminho = Path.cwd() / caminho

    if not caminho.exists():
        registrar(
            db, request, usuario_atual.user_id, ACAO_VER_CENSURADO,
            documento=documento, resultado=RESULTADO_FALHA,
            detalhe="arquivo_ausente",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo físico não encontrado.",
        )

    registrar(
        db, request, usuario_atual.user_id, ACAO_VER_CENSURADO,
        documento=documento, detalhe="censurado_tarjado",
    )
    return responder_arquivo(
        caminho,
        nome_para_download(documento.nome_original, documento.extensao),
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
        registrar_acesso_negado(db, request, usuario_atual, doc_id, ACAO_VER_ORIGINAL)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado ou sem acesso.",
        )

    equipe = equipe_do_documento(db, documento)
    cargo = cargo_na_equipe(db, usuario_atual, equipe.team_id) if equipe else None
    if not cargo or cargo["nivel"] < NIVEL_MIN_DESCENSURA:
        registrar(
            db, request, usuario_atual.user_id, ACAO_VER_ORIGINAL,
            documento=documento, resultado=RESULTADO_NEGADO,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seu cargo nao permite acessar a versao original do documento.",
        )

    # O original dorme cifrado (Fase 3.1); response le a copia legivel e a
    # apaga quando a resposta termina (BackgroundTask do starlette).
    candidatos = list(ORIGINAIS_DIR.glob(f"{documento.hash_documento}*"))
    if not candidatos:
        registrar(
            db, request, usuario_atual.user_id, ACAO_VER_ORIGINAL,
            documento=documento, resultado=RESULTADO_FALHA,
            detalhe="arquivo_ausente",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo original nao encontrado no armazenamento.",
        )

    caminho_cifrado = candidatos[0]
    arquivo_legivel = cifra.materializar_original_para_leitura(caminho_cifrado)
    registrar(
        db, request, usuario_atual.user_id, ACAO_VER_ORIGINAL,
        documento=documento, detalhe="original_integral",
    )
    resposta = responder_arquivo(
        arquivo_legivel,
        f"{documento.nome_original}_original.pdf",
    )
    resposta.background = BackgroundTask(
        cifra.descartar_material_temporario, arquivo_legivel, caminho_cifrado
    )
    return resposta


def chave_dos_itens(itens_para_cobrir: dict) -> str:
    """Assinatura do conjunto de caixas a cobrir.

    O cache de versao tem que mudar quando o que se cobre muda (mesmo nivel
    mesmo doc): se a politica ajusta itens, entregar o PDF antigo seria
    servir cache desatualizado. A chave deriva do conteudo das caixas, e nao
    do nivel sozinho.
    """
    import json

    normalizado = sorted(
        (pagina, espaco, list(coordenadas if coordenadas is not None else []))
        for pagina, caixas in itens_para_cobrir.items()
        for coordenadas, espaco in caixas
    )
    return hashlib.sha256(
        json.dumps(normalizado, sort_keys=True).encode()
    ).hexdigest()[:12]


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
        registrar_acesso_negado(db, request, usuario_atual, doc_id, ACAO_VER_PARCIAL)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado ou sem acesso.",
        )

    equipe = equipe_do_documento(db, documento)
    cargo = cargo_na_equipe(db, usuario_atual, equipe.team_id) if equipe else None
    if not cargo:
        registrar(
            db, request, usuario_atual.user_id, ACAO_VER_PARCIAL,
            documento=documento, resultado=RESULTADO_NEGADO,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao faz parte da equipe deste documento.",
        )

    # Lider (ou cargo de nivel suficiente) recebe o original integral.
    if cargo["nivel"] >= NIVEL_MIN_DESCENSURA:
        candidatos = list(ORIGINAIS_DIR.glob(f"{documento.hash_documento}*"))
        if not candidatos:
            registrar(
                db, request, usuario_atual.user_id, ACAO_VER_ORIGINAL,
                documento=documento, resultado=RESULTADO_FALHA,
                detalhe="arquivo_ausente",
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Arquivo original nao encontrado no armazenamento.",
            )
        caminho_cifrado = candidatos[0]
        arquivo_legivel = cifra.materializar_original_para_leitura(caminho_cifrado)
        registrar(
            db, request, usuario_atual.user_id, ACAO_VER_ORIGINAL,
            documento=documento, detalhe="original_integral",
        )
        resposta = responder_arquivo(
            arquivo_legivel,
            f"{documento.nome_original}_original.pdf",
        )
        resposta.background = BackgroundTask(
            cifra.descartar_material_temporario, arquivo_legivel, caminho_cifrado
        )
        return resposta

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
        registrar(
            db, request, usuario_atual.user_id, ACAO_VER_PARCIAL,
            documento=documento, resultado=RESULTADO_FALHA,
            detalhe="arquivo_ausente",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Arquivo original nao encontrado no armazenamento.",
        )

    # Nenhum item acima do nivel do usuario: nao ha regiao a cobrir, mas
    # entregamos a versao tarjada. Servir o original aqui vazaria o documento
    # sempre que o scan nao encontrou nada.
    if not itens_para_cobrir:
        caminho_censurado = caminho_armazenado(documento)
        registrar(
            db, request, usuario_atual.user_id, ACAO_VER_PARCIAL,
            documento=documento, detalhe=f"parcial_nivel{nivel}",
        )
        return responder_arquivo(
            caminho_censurado,
            f"{documento.nome_original}_censurado.pdf",
        )

    try:
        nome_saida = (
            f"{documento.hash_documento}_parcial_nivel{nivel}_"
            f"{chave_dos_itens(itens_para_cobrir)}.pdf"
        )
        caminho_parcial = CENSURADOS_DIR / nome_saida

        # Cache da versao (doc, nivel, caixas): regenerar um PDF rasterizado
        # de 150 dpi por pedido custa caro em servidor de empresa. O nome ja
        # carrega a assinatura das caixas, entao cache desatualizado nao
        # acontece: itens diferentes caem em arquivo diferente.
        if caminho_parcial.is_file():
            registrar(
                db, request, usuario_atual.user_id, ACAO_VER_PARCIAL,
                documento=documento, detalhe=f"parcial_nivel{nivel}_cache",
            )
            return responder_arquivo(
                caminho_parcial,
                f"{documento.nome_original}_parcial_nivel{nivel}.pdf",
            )

        # Rasterizar o original: leitura temporaria legivel do cifrado em
        # disco; com o PDF parcial feito, a copia some (finally).
        original_legivel = cifra.materializar_original_para_leitura(caminhos_originais[0])
        try:
            caminho_parcial = get_scanner().gerar_pdf_parcial(
                file_path=str(original_legivel),
                itens_para_cobrir=itens_para_cobrir,
                dir_destino=CENSURADOS_DIR,
                nome_saida=nome_saida,
            )
        finally:
            cifra.descartar_material_temporario(original_legivel, caminhos_originais[0])
    except NenhumaMascaraAplicavel:
        # Havia item a cobrir, mas nenhuma caixa era utilizavel. Servir o
        # parcial assim seria o original sem nenhuma tarja; a versao
        # integralmente censurada e mais restritiva e ainda entrega algo
        # honesto ao usuario.
        logger.warning(
            f"Doc {documento.doc_id}: nenhuma caixa aplicavel na descensura "
            "parcial; servindo a versao censurada."
        )
        registrar(db, request, usuario_atual.user_id, ACAO_VER_PARCIAL, documento=documento)
        return responder_arquivo(
            caminho_armazenado(documento),
            f"{documento.nome_original}_censurado.pdf",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Falha ao gerar a descensura parcial.",
        ) from e

    registrar(
        db, request, usuario_atual.user_id, ACAO_VER_PARCIAL,
        documento=documento, detalhe=f"parcial_nivel{nivel}",
    )
    return responder_arquivo(
        caminho_parcial,
        f"{documento.nome_original}_parcial_nivel{nivel}.pdf",
    )


# Upload em lote: cada arquivo fica como Documento AGUARDANDO; a fila
# (core.fila) processa em background. Mais que isto por lotes satura a
# resposta e o OCR de maquinas pequenas.
MAX_ARQUIVOS_POR_LOTE = 50
STATUS_AGUARDANDO = "AGUARDANDO"
STATUS_RECUSADO = "RECUSADO"


@router.post("/upload/lote", status_code=status.HTTP_202_ACCEPTED)
async def upload_documentos_lote(
    request: Request,
    files: list[UploadFile] = File(...),
    team_id: int = Form(...),
    nivel_seguranca: int = Form(1),
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user)
):
    """Ingestao em volume: varios PDFs numa so requisicao.

    Valida cada arquivo cedo (formato/magic bytes); os validos ganham um
    Documento AGUARDANDO e entram na fila de scan; os invalidos sao recusados
    nominalmente, sem travar o lote inteiro. O corpo responde antes do
    processamento: o status vira PROCESSANDO/CONCLUIDO pela fila, visivel nos
    metadados e listagens do documento.

    Lote vai para uma equipe so: cada documento tem um dono unico, igual ao
    upload individual (que agora exige exatamente uma equipe).
    """
    if nivel_seguranca < 1 or nivel_seguranca > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nível de segurança inválido (1-4)."
        )

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie ao menos um arquivo.",
        )
    if len(files) > MAX_ARQUIVOS_POR_LOTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite de {MAX_ARQUIVOS_POR_LOTE} arquivos por lote.",
        )

    vinculo = (
        db.query(UsuarioEquipe)
        .filter(
            UsuarioEquipe.user_id == usuario_atual.user_id,
            UsuarioEquipe.team_id == team_id,
        )
        .first()
    )
    if not vinculo:
        registrar(
            db, request, usuario_atual.user_id, ACAO_UPLOAD_LOTE,
            team_id=team_id, resultado=RESULTADO_NEGADO,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voce nao faz parte dessa equipe.",
        )

    itens: list[dict] = []
    criados: list[Documento] = []

    for arquivo in files:
        nome_seguro = Path(arquivo.filename or "").name
        try:
            conteudo, caminho_nome = await ler_e_validar_upload(arquivo, Path(nome_seguro))
        except HTTPException as erro:
            itens.append({
                "nome": nome_seguro,
                "doc_id": None,
                "status": STATUS_RECUSADO,
                "motivo": erro.detail,
            })
            continue

        extensao = caminho_nome.suffix or ".pdf"
        hash_arquivo = gerar_hash_arquivo(conteudo)
        nome_arquivo = f"{hash_arquivo}{extensao}"
        caminho_original = ORIGINAIS_DIR / nome_arquivo
        cifra.gravar_original_cifrado(caminho_original, conteudo)

        titulo = caminho_nome.stem or nome_seguro
        documento = Documento(
            user_team_id=vinculo.user_team_id,
            nome_original=titulo,
            extensao=extensao.lstrip(".").lower(),
            tamanho_bytes=len(conteudo),
            nivel_seguranca=nivel_seguranca,
            chave_criptografica=gerar_chave_criptografica(hash_arquivo, usuario_atual.user_id),
            hash_documento=hash_arquivo,
            caminho_storage="",
            status_processamento=STATUS_AGUARDANDO,
            cpf_censurados=0,
        )
        db.add(documento)
        criados.append(documento)
        itens.append({
            "nome": nome_seguro,
            "titulo": titulo,
            "doc_id": None,  # preenchido apos o flush
            "status": STATUS_AGUARDANDO,
            "motivo": None,
        })

    if not criados:
        return {
            "mensagem": "Nenhum arquivo valido foi aceito.",
            "total_recebido": len(files),
            "total_aceito": 0,
            "itens": itens,
        }

    db.commit()
    itens_aceitos = [item for item in itens if item["status"] == STATUS_AGUARDANDO]
    for documento, item in zip(criados, itens_aceitos, strict=True):
        item["doc_id"] = documento.doc_id
        registrar(
            db, request, usuario_atual.user_id, ACAO_UPLOAD,
            documento=documento, detalhe=f"lote_{STATUS_AGUARDANDO.lower()}",
        )

    for documento in criados:
        fila.agendar(processar_upload_da_fila, documento.doc_id)

    return {
        "mensagem": "Lote recebido; processamento em fila.",
        "total_recebido": len(files),
        "total_aceito": len(criados),
        "itens": itens,
    }


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
        registrar(
            db, request, usuario_atual.user_id, ACAO_LISTAR_DOCUMENTOS,
            team_id=team_id, resultado=RESULTADO_NEGADO,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não faz parte dessa equipe."
        )

    # Listar documentos
    user_team_ids = [ue.user_team_id for ue in usuario_equipe_list]
    documentos = db.query(Documento).filter(
        Documento.user_team_id.in_(user_team_ids),
        Documento.ativo.is_(True),
    ).all()

    registrar(db, request, usuario_atual.user_id, ACAO_LISTAR_DOCUMENTOS, team_id=team_id)

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


def fabrica_sessao_trabalho() -> Session:
    """Sessao do worker da fila, isolada da requisicao que ja respondeu.

    Monkeypatch pelos testes: a fila sincrona deles precisa de uma sessao
    ligada ao banco de teste (e que sobreviva ate a proxima requisicao), e
    nao a SessionLocal de producao, que aponta para outro banco.
    """
    from app.database import SessionLocal

    return SessionLocal()


def processar_upload_da_fila(doc_id: int) -> None:
    """Processa um documento AGUARDANDO do lote (threads fora da requisicao).

    Cada task usa sessao propria: a requisicao HTTP que aceitou o arquivo ja
    encerrou. O status avanca AGUARDANDO -> PROCESSANDO -> CONCLUIDO | ERRO
    sempre comprometido, para que o documento nunca fique preso no meio.
    """
    db = fabrica_sessao_trabalho()
    try:
        documento = db.get(Documento, doc_id)
        if documento is None or documento.status_processamento != STATUS_AGUARDANDO:
            return

        equipe = equipe_do_documento(db, documento)
        niveis = (
            politica_niveis.niveis_da_equipe(db, equipe.team_id) if equipe else {}
        )

        documento.status_processamento = "PROCESSANDO"
        db.commit()

        candidatos = list(ORIGINAIS_DIR.glob(f"{documento.hash_documento}*"))
        if not candidatos:
            raise FileNotFoundError(
                f"Original nao encontrado na fila: {documento.hash_documento}"
            )

        # O original dorme cifrado em disco (Fase 3.1); o scan le a copia
        # temporal legivel, apagada no finally do try abaixo.
        arquivo_scan = cifra.materializar_original_para_leitura(candidatos[0])
        try:
            get_scanner().scan_and_save(
                file_path=str(arquivo_scan),
                db=db,
                user_team_id=documento.user_team_id,
                nome_original=documento.nome_original,
                nivel_seguranca=documento.nivel_seguranca,
                dir_original=ORIGINAIS_DIR,
                dir_censurado=CENSURADOS_DIR,
                niveis=niveis,
                documento=documento,
            )
        finally:
            cifra.descartar_material_temporario(arquivo_scan, candidatos[0])
        db.commit()

        if documento.status_processamento == "ERRO" or not documento.caminho_storage:
            # Scan concluso com Falha (sem paginas, OCR vazio): o commit de cima
            # persistiu ERRO; nada mais a fazer aqui.
            logger.error(f"Lote: doc {doc_id} terminou como ERRO.")
    except Exception:
        logger.exception("Lote: falha ao processar doc %s.", doc_id)
        db.rollback()
        _marcar_erro_da_fila(db, doc_id)
    finally:
        db.close()


def _marcar_erro_da_fila(db: Session, doc_id: int) -> None:
    """Deixa o documento do lote explicitamente em ERRO, sempre.

    A marca de ERRO dentro do scan roda antes do rollback do worker e seria
    perdida; aqui o doc e reconsultado na sessao limpa e o status ganha
    commit proprio. Se o doc ja virou ERRO, a operacao e idempotente.
    """
    documento = db.get(Documento, doc_id)
    if documento is None or documento.status_processamento == "ERRO":
        db.commit()
        return
    documento.status_processamento = "ERRO"
    db.commit()
