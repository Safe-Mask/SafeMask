"""Dados de demonstracao (PI-III #232).

`python -m app.tarefas.popular_demo` cria organizacao, equipe, contas e
documentos ficticios. A senha e gerada na hora e mostrada so no terminal;
rodar de novo nao duplica nada.
"""

import pytest

from app.core.security import verificar_senha
from app.models.dado_sensivel import DadoSensivel
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.usuario import Usuario


@pytest.fixture
def popular(seed, monkeypatch, tmp_path):
    from app.routes import documentos as documentos_routes
    from app.tarefas import popular_demo

    db = seed["db"]
    for pasta in ("originais", "censurados"):
        (tmp_path / pasta).mkdir(exist_ok=True)
    monkeypatch.setattr(documentos_routes, "ORIGINAIS_DIR", tmp_path / "originais")
    monkeypatch.setattr(documentos_routes, "CENSURADOS_DIR", tmp_path / "censurados")
    monkeypatch.setattr(popular_demo, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    return popular_demo


def _contas(db, popular):
    return db.query(Usuario).filter(Usuario.email.in_([e for _, e, _ in popular.CONTAS])).all()


def _senha(saida):
    return saida.split("Senha das contas: ")[1].split()[0]


def test_cria_organizacao_equipe_contas_e_documentos(seed, popular, capsys):
    db = seed["db"]
    assert popular.main([]) == 0
    saida = capsys.readouterr().out

    contas = _contas(db, popular)
    assert len(contas) == 3
    equipe = db.query(Equipe).filter_by(nome=popular.EQUIPE).one()
    assert {c.organizacao_id for c in contas} == {equipe.organizacao_id}
    assert equipe.organizacao_id != seed["organizacao"].organizacao_id  # organizacao propria
    titulos = [titulo for titulo, *_ in popular.DOCUMENTOS]
    docs = db.query(Documento).filter(Documento.nome_original.in_(titulos)).all()
    assert len(docs) == len(titulos)
    assert db.query(DadoSensivel).filter(DadoSensivel.doc_id.in_([d.doc_id for d in docs])).count() >= 6
    assert "senha" in saida.lower()


def test_senha_so_no_terminal_e_gravada_como_hash(seed, popular, capsys):
    popular.main(["--nova-senha"])
    senha = _senha(capsys.readouterr().out)
    assert len(senha) >= 12
    for conta in _contas(seed["db"], popular):
        assert conta.senha_hash != senha
        assert verificar_senha(senha, conta.senha_hash)


def test_rodar_de_novo_nao_duplica(seed, popular, capsys):
    popular.main([])
    popular.main([])
    saida = capsys.readouterr().out
    db = seed["db"]
    assert len(_contas(db, popular)) == 3
    titulos = [titulo for titulo, *_ in popular.DOCUMENTOS]
    assert db.query(Documento).filter(Documento.nome_original.in_(titulos)).count() == len(titulos)
    assert "já existem" in saida


def test_nova_senha_troca_a_senha(seed, popular, capsys):
    popular.main(["--nova-senha"])
    primeira = _senha(capsys.readouterr().out)
    popular.main(["--nova-senha"])
    segunda = _senha(capsys.readouterr().out)
    assert primeira != segunda
    assert all(verificar_senha(segunda, c.senha_hash) for c in _contas(seed["db"], popular))
