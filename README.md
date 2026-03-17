<div align="center">

<p align="center">
   <img src="frontend/images/safemask-logo-transparente.png" alt="SafeMask" width="72" /><br>
   <h1>SafeMask</h1>
</p>

> Projeto acadêmico desenvolvido no **CEUB (Centro Universitário de Brasília)** para a disciplina **Projeto Integrador III**.

**Proteção Inteligente de Dados Sensíveis com IA**

Detecte e censure automaticamente informações confidenciais em documentos, garantindo conformidade total com a LGPD e segurança de dados.

[![Python](https://img.shields.io/badge/Python-3.9-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009485?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-FF6F20?logo=python&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=json-web-tokens&logoColor=white)](https://jwt.io/)
[![HTML5](https://img.shields.io/badge/HTML5-E34C26?logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

</div>

## Status atual do sistema

O que ja esta implementado e funcional hoje:

- Cadastro e login de usuarios com senha hasheada (bcrypt/passlib)
- Em cada novo cadastro, criacao automatica da equipe inicial "Minha equipe"
- Associacao do usuario ao cargo de lider na equipe criada
- Emissao de token JWT no cadastro e no login
- Endpoint para verificar disponibilidade de email
- Endpoint autenticado de dashboard com metricas e documentos recentes
- Frontend com fluxos de login, cadastro e dashboard consumindo API FastAPI
- Banco PostgreSQL hospedado no Neon
- Deploy do frontend com dominio no Vercel
- GitHub Actions configurado para publicar no Vercel quando ha merge na branch main (fluxo de PR aprovado/aceito)

## Stack tecnologico

### Backend
- Python 3.9+
- FastAPI
- SQLAlchemy 2.x
- Pydantic 2.x
- python-jose (JWT)
- passlib + bcrypt
- psycopg2-binary

### Frontend
- HTML5
- CSS3
- JavaScript (vanilla)

### Infraestrutura
- Banco: Neon (PostgreSQL)
- Backend: Render (configurado em render.yaml)
- Frontend: Vercel (com dominio customizado)
- CI/CD frontend: GitHub Actions + Vercel

## Estrutura do projeto

```text
SafeMask/
|- .github/
|  |- workflows/
|     |- vercel-merge.yml
|- backend/
|  |- app/
|  |  |- core/
|  |  |  |- auth.py
|  |  |  |- current_user.py
|  |  |  |- security.py
|  |  |- models/
|  |  |  |- cargo.py
|  |  |  |- documentos.py
|  |  |  |- equipe.py
|  |  |  |- usuario.py
|  |  |  |- usuario_equipe.py
|  |  |- routes/
|  |  |  |- auth.py
|  |  |  |- dashboard.py
|  |  |- schemas/
|  |  |  |- documento.py
|  |  |  |- usuario.py
|  |  |  |- usuario_equipe.py
|  |  |- database.py
|  |  |- main.py
|  |- requirements.txt
|- frontend/
|  |- css/
|  |- html/
|  |  |- auth/
|  |- js/
|  |- images/
|- render.yaml
|- index.html
```

## Endpoints disponiveis hoje

Base local: http://127.0.0.1:8000

### Publicos

- POST /auth/login
- POST /auth/cadastro
- GET /auth/verificar-email/{email}

### Protegidos por JWT

- GET /dashboard/overview

### Health check

- GET /

## Como rodar localmente

### 1) Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
# source venv/bin/activate

pip install -r requirements.txt
```

Crie o arquivo .env em backend/ com:

```env
DATABASE_URL=postgresql://usuario:senha@host:5432/database?sslmode=require
SECRET_KEY=sua-chave-secreta
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
```

Observacao: o projeto converte automaticamente postgresql:// para postgresql+psycopg2:// quando necessario.

Suba a API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger: http://127.0.0.1:8000/docs

### 2) Frontend

```bash
cd frontend
python -m http.server 8080
```

Acesse: http://127.0.0.1:8080

## Deploy e infraestrutura

### Frontend (Vercel)

- Frontend publicado no Vercel
- Dominio customizado ja configurado por voce
- Pipeline automatizado pelo workflow .github/workflows/vercel-merge.yml

O workflow atual dispara em push para main e usa:

- VERCEL_TOKEN
- ORG_ID
- PROJECT_ID

### Backend (Render)

Configurado via render.yaml:

- rootDir: backend
- buildCommand: pip install uv && uv sync
- startCommand: uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT

### Banco de dados (Neon)

- PostgreSQL hospedado no Neon
- Conexao fornecida por DATABASE_URL (com SSL)

## Seguranca implementada

- Hash de senha com bcrypt
- Tokens JWT para autenticacao
- Middleware CORS habilitado
- Uso de ORM (SQLAlchemy) para reduzir risco de SQL injection

## Observacoes e proximos passos

- O dashboard ja consome dados reais do banco
- O modulo completo de upload/censura de documentos ainda pode evoluir com novos endpoints dedicados
- Se quiser, posso na proxima iteracao atualizar este README com:
  - URL publica exata do dominio Vercel
  - URL publica do backend no Render
  - secao de troubleshooting com erros comuns de deploy
