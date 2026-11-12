"""Dados de demonstracao (PI-III #232).

Cria a "Organizacao Demonstracao", a "Equipe Demonstracao", tres contas
ficticias (lider, supervisor e membro) e documentos ficticios ja processados
(com tarja), para testar o sistema em poucos minutos. Executar de dentro de
backend/ (ou no container da API):

    python -m app.tarefas.popular_demo
    python -m app.tarefas.popular_demo --nova-senha   # troca a senha das contas

A senha e gerada na hora e aparece SO no terminal; no banco fica o hash.
Rodar de novo nao duplica nada. Os documentos passam pelo mesmo caminho do
upload (deteccao, tarja e auditoria). Nenhum dado e de pessoa real.
"""

import argparse
import asyncio
import io
import json
import secrets
import sys

from fastapi import UploadFile

from app.core.comprovante import gerar_pdf
from app.core.security import hash_senha
from app.database import SessionLocal
from app.models.cargo import Cargo
from app.models.documentos import Documento
from app.models.equipe import Equipe
from app.models.organizacao import Organizacao
from app.models.usuario import Usuario
from app.models.usuario_equipe import UsuarioEquipe

ORGANIZACAO = "Organização Demonstração"
EQUIPE = "Equipe Demonstração"
CONTAS = [
    ("Lia Líder (demo)", "lider.demo@safemask.example.com", "lider"),
    ("Saulo Supervisor (demo)", "supervisor.demo@safemask.example.com", "supervisor"),
    ("Mara Membro (demo)", "membro.demo@safemask.example.com", "membro"),
]
# (titulo, nivel de seguranca, linhas do PDF)
DOCUMENTOS = [
    ("Contrato de prestação de serviços (demo)", 1, [
        "Contratante: Pessoa Fictícia da Silva, CPF 529.982.247-25",
        "Contratada: Exemplo Consultoria Ltda, CNPJ 11.222.333/0001-81",
        "Contato: contato@exemplo.com.br - Telefone (61) 99876-5432",
        "Processo administrativo 0001234-56.2026.8.07.0001",
    ]),
    ("Ficha cadastral (demo)", 2, [
        "Nome: Pessoa Fictícia da Silva",
        "RG: 12.345.678-9 - CNH 02650306461, categoria B",
        "Endereço: SQS 308 Bloco A, CEP 70355-010, Brasília/DF",
        "Pagamento: cartão 4111 1111 1111 1111",
        "Protocolo 20261234 (não é dado pessoal)",
    ]),
]


def _pdf(titulo: str, linhas: list[str]) -> bytes:
    return gerar_pdf(titulo, [("Documento fictício para demonstração", linhas)], "SafeMask - dados de demonstração")


def _organizacao_e_equipe(db):
    org = db.query(Organizacao).filter_by(nome=ORGANIZACAO).first()
    if org is None:
        org = Organizacao(nome=ORGANIZACAO)
        db.add(org)
        db.flush()
    equipe = db.query(Equipe).filter_by(nome=EQUIPE, organizacao_id=org.organizacao_id).first()
    if equipe is None:
        equipe = Equipe(nome=EQUIPE, descricao="Equipe fictícia criada por app.tarefas.popular_demo",
                        organizacao_id=org.organizacao_id)
        db.add(equipe)
        db.flush()
    return org, equipe


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Cria contas, equipe e documentos ficticios de demonstracao.")
    parser.add_argument("--nova-senha", action="store_true", help="gera uma senha nova para as contas de demonstracao")
    args = parser.parse_args(argv)

    from app.routes.documentos import upload_documento  # carrega o scanner so quando preciso

    db = SessionLocal()
    try:
        cargos = {c.nome: c for c in db.query(Cargo).all()}
        if not {"lider", "supervisor", "membro"} <= set(cargos):
            print("Cargos nao encontrados: inicie a API uma vez antes (ela cria as tabelas e os cargos).")
            return 1
        org, equipe = _organizacao_e_equipe(db)

        existentes = {u.email: u for u in db.query(Usuario).filter(Usuario.email.in_([e for _, e, _ in CONTAS]))}
        senha = secrets.token_urlsafe(12) if args.nova_senha or len(existentes) < len(CONTAS) else None
        usuarios = {}
        for nome, email, cargo in CONTAS:
            usuario = existentes.get(email)
            if usuario is None:
                usuario = Usuario(nome=nome, email=email, senha_hash=hash_senha(senha),
                                  organizacao_id=org.organizacao_id)
                db.add(usuario)
                db.flush()
            elif args.nova_senha:
                usuario.senha_hash = hash_senha(senha)
            if not db.query(UsuarioEquipe).filter_by(user_id=usuario.user_id, team_id=equipe.team_id).first():
                db.add(UsuarioEquipe(user_id=usuario.user_id, team_id=equipe.team_id, cargo_id=cargos[cargo].cargo_id))
            usuarios[cargo] = usuario
        db.commit()

        criados = 0
        for titulo, nivel, linhas in DOCUMENTOS:
            ja_existe = (
                db.query(Documento.doc_id)
                .join(UsuarioEquipe, UsuarioEquipe.user_team_id == Documento.user_team_id)
                .filter(Documento.nome_original == titulo, UsuarioEquipe.team_id == equipe.team_id)
                .first()
            )
            if ja_existe:
                continue
            arquivo = UploadFile(file=io.BytesIO(_pdf(titulo, linhas)), filename="demo.pdf")
            asyncio.run(upload_documento(
                None, file=arquivo, titulo=titulo, nivel_seguranca=nivel, teams=json.dumps([equipe.team_id]),
                ignorar="[]", trechos_extras="[]", db=db, usuario_atual=usuarios["lider"],
            ))
            criados += 1

        print(f"Equipe: {EQUIPE}")
        for _nome, email, cargo in CONTAS:
            print(f"  {cargo:<10} {email}")
        if senha:
            print(f"Senha das contas: {senha}")
            print("Anote agora: ela nao fica gravada em lugar nenhum (no banco fica so o hash).")
        else:
            print("As contas já existem: use a senha mostrada na primeira execução, ou rode com --nova-senha.")
        print(f"Documentos criados agora: {criados} (já existem: {len(DOCUMENTOS) - criados}).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
