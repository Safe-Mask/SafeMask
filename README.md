<div align="center">

<h1 align="center">SafeMask</h1>

> Projeto acadêmico desenvolvido no **CEUB (Centro Universitário de Brasília)** para a disciplina **Projeto Integrador III** do curso **Ciência da Computação**.

**Software de compliance de documentos on-premise**

O SafeMask é o intermediário dos documentos da empresa: o serviço fica no
servidor da empresa, monitora a pasta base, detecta dados sensíveis com IA
local e entrega a versão censurada adequada ao nível/cargo de quem solicita.
O documento original nunca sai do servidor.

</div>

---

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009485?logo=fastapi&logoColor=white)](https://www.fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-FF6F20?logo=python&logoColor=white)](https://www.sqlalchemy.org/)
[![Tauri](https://img.shields.io/badge/Client-Tauri-orange?logo=tauri&logoColor=white)](https://tauri.app/)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=json-web-tokens&logoColor=white)](https://jwt.io/)

## Como funciona

```
[Servidor da empresa]                        [Desktops]
FastAPI + SQLite (.exe)          <- HTTP ->  Client Tauri (~10 MB)
Watch da pasta base → fila →                 login → pedir documento
scan (NER local + regex) →                   → recebe versão tarjada
coordenadas no banco                         conforme seu cargo
Original cifrado, nunca exposto              admin: config + auditoria
```

1. **Ingestão** — o admin aponta a pasta base na rede; o serviço monitora
   (`watchdog`) e ingere qualquer PDF novo (dedupe por hash)
2. **Scan** — uma única vez por documento: NER local + regex localizam os
   dados sensíveis; coordenadas, tipo e nível mínimo de acesso ficam fichados
   no banco (`DadoSensivel`)
3. **Entrega** — quem pede recebe só as versões que seu cargo enxerga
   (reconstrução por coordenadas, com cache por nível); a IA não roda no download
4. **Auditoria** — todo pedido (concedido ou negado) registra quem, o quê e
   qual versão recebeu

## Estrutura do projeto

```
backend/            Serviço (FastAPI) — objeto da fase atual
├── app/            core (fila, autorizacao, config), models, routes, schemas
├── scanner/        Detector local: regex + validadores + NER (safemask-ner)
└── tests/          337 testes pytest
scripts/            e2e, gerador de PDF de exemplo
documentation/      Relatórios e checklist de sprints
client/             Client desktop (Tauri) — Fase 2 deste plano
```

Detalhamento das fases: [`PLANO_DESKTOP.md`](PLANO_DESKTOP.md)

## Desenvolvimento

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt requirements-dev.txt
.venv/bin/pytest          # roda da raiz backend/ (rootdir correto)
.venv/bin/ruff check .
.venv/bin/uvicorn app.main:app --reload
```

Banco: SQLite por padrão (`DATABASE_URL` opcional para PostgreSQL).

IA local (opcional no dev): `pip install -r requirements-ia.txt` — sem elas o
scanner roda em modo regex-only (veja `backend/scanner/scanner.py`).

## Endpoints principais

| Área | Rotas |
|---|---|
| Auth | `POST /login`, sessão JWT, troca de senha |
| Documentos | `POST /documentos/upload/lote`, `GET /documentos/{id}`, `GET /documentos/{id}/parcial` (versão por nível), `GET /documentos/{id}/original` (nível 3+) |
| Equipes | CRUD de equipes, membros, cargos, política de níveis |
| Auditoria | `GET /auditoria`, export CSV |

Documentação interativa: `http://localhost:8000/docs` com o serviço rodando.

## Conformidade LGPD

- Dados sensíveis localizados automaticamente (NER treinado pelo projeto, 100% offline)
- Entrega por nível de acesso com trilha de auditoria formal
- Originais sob controle do serviço e (Fase 3) criptografados em disco
- Nenhum dado sai da rede da empresa: tudo on-premise
