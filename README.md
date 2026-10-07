<div align="center">

<p align="center">
   <img src="frontend/images/safemask-logo-transparente.png" alt="SafeMask" width="72" /><br>
   <h1>SafeMask</h1>
</p>

> Projeto acadêmico desenvolvido no **CEUB (Centro Universitário de Brasília)** para a disciplina **Projeto Integrador III** do curso **Ciência da Computação** .

**Proteção Inteligente de Dados Sensíveis com IA**

Detecte e censure automaticamente informações confidenciais em documentos, garantindo conformidade total com a LGPD e segurança de dados.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009485?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-FF6F20?logo=python&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Neon](https://img.shields.io/badge/Neon-Database-92E7DD?logo=postgresql&logoColor=white)](https://neon.tech/)
[![Vercel](https://img.shields.io/badge/Vercel-Deploy-000000?logo=vercel&logoColor=white)](https://vercel.com/)
[![JWT](https://img.shields.io/badge/JWT-Auth-000000?logo=json-web-tokens&logoColor=white)](https://jwt.io/)

</div>

---

## � Acesso Rápido

| Serviço | URL | Status |
|---------|-----|--------|
| 🌐 **Frontend (Vercel)** | [https://safe-mask.vercel.app](https://safe-mask.vercel.app) | ✅ Online |
| 🔙 **Backend (Render)** | [https://safemask-backend.onrender.com](https://safemask-backend.onrender.com) | ✅ Online |
| 🗄️ **API Docs** | [https://safemask-backend.onrender.com/docs](https://safemask-backend.onrender.com/docs) | ✅ Online |
| 💾 **Database (Neon)** | PostgreSQL Serverless | ✅ Conectado |

---

## �📖 Índice

- [Acesso Rápido](#-acesso-rápido)
- [Visão Geral](#-visão-geral)
- [5W do Projeto](#-5w-do-projeto)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Instalação Local](#-instalação-local)
- [API Endpoints](#-api-endpoints)
- [Desenvolvimento](#-desenvolvimento)
- [Conformidade LGPD](#-conformidade-lgpd)

---

## 🎯 Visão Geral

SafeMask é uma plataforma full-stack especializada em proteção de dados sensíveis que permite:

- **Usuários**: Registrar-se, fazer login seguro e gerenciar seus documentos
- **Equipes**: Criar, entrar e gerenciar suas equipes
- **Processamento de Documentos**: Upload e armazenamento seguro de arquivos
- **Detecção de Dados Sensíveis**: Identificação automática de informações confidenciais
- **Censura Automática**: Mascaramento inteligente de dados sensíveis
- **Autenticação JWT**: Sistema robusto com tokens JWT e bcrypt
- **Conformidade LGPD**: Proteção de dados pessoais conforme legislação

---

## 📌 5W do Projeto

| 5W | Resposta |
|----|----------|
| **What (O quê?)** | O SafeMask é uma plataforma web que detecta e censura automaticamente dados sensíveis em documentos usando IA. |
| **Why (Por quê?)** | Para reduzir riscos de vazamento de informações confidenciais, proteger dados pessoais e apoiar a conformidade com a LGPD. |
| **Who (Quem?)** | Usuários, equipes e organizações que precisam armazenar, analisar, compartilhar ou tratar documentos com informações sensíveis. |
| **Where (Onde?)** | Em ambiente web, com frontend hospedado na Vercel, backend FastAPI no Render e banco PostgreSQL serverless na Neon. |
| **When (Quando?)** | Durante o fluxo de upload, análise, armazenamento e compartilhamento de documentos, especialmente antes de disponibilizar arquivos a terceiros. |

---

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI 0.115** (Framework web assíncrono)
- **Python 3.12** (Linguagem principal)
- **SQLAlchemy 2.0** (ORM)
- **PostgreSQL** (via Neon - serverless)
- **JWT + Bcrypt** (Autenticação e criptografia)
- **Pydantic 2.0** (Validação de dados)

### Frontend
- **HTML5** (Estrutura)
- **CSS3** (Estilização responsiva)
- **JavaScript Vanilla** (Interatividade) 

### Deployment
- **Neon** (PostgreSQL serverless - Database)
- **Vercel** (Frontend estático)
- **Render** (Backend FastAPI)

---

## 📁 Estrutura do Projeto

```
SafeMask/
├── index.html
├── README.md
├── render.yaml
├── requirements.txt
├── AI_model/
│   ├── create_admin.py
│   ├── models.py
│   ├── reset_db.py
│   ├── scanner.py
│   ├── README.md
│   ├── requirements.txt
│   └── app/
│       ├── database.py
│       ├── main.py
│       ├── core/
│       │   ├── auth.py
│       │   ├── current_user.py
│       │   └── security.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── documentos.py
│       │   └── usuario.py
│       ├── routes/
│       │   └── auth.py
│       └── schemas/
│           ├── documento.py
│           └── usuario.py
│
├── backend/
│   ├── requirements.txt
│   ├── uploads/
│   └── app/
│       ├── database.py
│       ├── main.py
│       ├── core/
│       │   ├── auth.py
│       │   ├── current_user.py
│       │   ├── email.py
│       │   └── security.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── cargo.py
│       │   ├── dado_sensivel.py
│       │   ├── documentos.py
│       │   ├── equipe.py
│       │   ├── log_auditoria.py
│       │   ├── usuario_equipe.py
│       │   └── usuario.py
│       ├── routes/
│       │   ├── auth.py
│       │   ├── dashboard.py
│       │   ├── documentos.py
│       │   └── equipes.py
│       └── schemas/
│           ├── auth.py
│           ├── documento.py
│           ├── equipe.py
│           ├── usuario_equipe.py
│           └── usuario.py
│
├── documentation/
│   ├── Daily Scrum/
│   └── PDF/
│
└── frontend/
   ├── css/
   │   ├── dashboard.css
   │   ├── loading.css
   │   ├── login.css
   │   ├── styles.css
   │   ├── documentos/
   │   │   ├── censurados.css
   │   │   ├── censurar.css
   │   │   └── descensura.css
   │   └── equipes/
   │       └── equipes.css
   ├── html/
   │   ├── dashboard.html
   │   ├── auth/
   │   │   ├── cadastro.html
   │   │   ├── esqueci_senha.html
   │   │   ├── login.html
   │   │   └── reset_password.html
   │   ├── documentos/
   │   │   ├── censurados.html
   │   │   ├── censurar.html
   │   │   └── descensura.html
   │   └── equipes/
   │       ├── detalhe.html
   │       └── equipes.html
   ├── images/
   └── js/
      ├── cadastro.js
      ├── dashboard.js
      ├── loading.js
      ├── login.js
      ├── script.js
      ├── auth/
      │   ├── esqueci_senha.js
      │   └── reset_password.js
      ├── documentos/
      │   ├── censurados.js
      │   ├── censurar.js
      │   └── descensura.js
      └── equipes/
         ├── detalhe.js
         └── equipes.js
```

---

## 🚀 Instalação Local

> ℹ️ **O projeto já está em produção!** Use esta seção apenas para desenvolvimento local.

### Pré-requisitos

- **Python** >= 3.9
- **pip** >= 21.0
- PostgreSQL local ou Neon database (opcional para dev)

### Passo 1: Clone o repositório

```bash
git clone https://github.com/yourusername/SafeMask.git
cd SafeMask
```

### Passo 2: Configure o Banco de Dados

**Opção A: Neon (Recomendado para Produção)**

1. Acesse [https://neon.tech/](https://neon.tech/)
2. Crie uma conta gratuita
3. Crie um novo projeto
4. Copie a **Connection String**: `postgresql://user:password@host/database?sslmode=require`

**Opção B: PostgreSQL Local (para Desenvolvimento)**

```bash
# Com Docker:
docker run --name safemask-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_USER=user \
  -e POSTGRES_DB=safemask_db \
  -p 5432:5432 -d postgres:15

# Ou instale PostgreSQL localmente
```

### Passo 3: Configure o Backend

```bash
cd backend

# Crie ambiente virtual
python -m venv venv

# Ative o ambiente
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Instale dependências
# Base (igual ao deploy):
pip install -r requirements.txt

# ATENÇÃO: para rodar a rede neural (NER) localmente, instale também as
# dependências de IA. Elas ficam separadas de propósito: no Render Free
# (1 GB de disco) só a base é instalada, e o scanner roda em modo regex-only.
# Detalhes em backend/requirements-ia.txt e backend/scanner/scanner.py.
pip install -r requirements-ia.txt

# Crie arquivo .env
# Windows:
type nul > .env
# macOS/Linux:
touch .env
```

**Configure o .env com estas 2 variáveis apenas:**

```env
DATABASE_URL=postgresql://seu_usuario:sua_senha@seu_host/seu_banco?sslmode=require
SECRET_KEY=gere-uma-chave-aleatoria-forte-aqui
```

**Para gerar uma SECRET_KEY segura:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Exemplo com Neon:**

```env
DATABASE_URL=postgresql://neon_user:abc123@ep-cool-cloud-123456.neon.tech/safemask_db?sslmode=require
SECRET_KEY=kX9pL2mN4oJ8vZ5qR3tU6w7eY1aBcD9fGhIkL0mNoPqRsTuVwXyZ
```

**Teste o Backend:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API em: `http://localhost:8000`
- Swagger Docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

> O scanner carrega a IA automaticamente quando existem os pesos em
> `backend/scanner/safemask-ner/model.safetensors`. Sem os pesos, ele degrada
> para detecção apenas por regex (log de aviso no boot) — mesmo comportamento
> do ambiente de produção.

### Passo 4: Configure o Frontend

No deploy (Vercel) a raiz do site é a **raiz do repositório**: o landing
`index.html` e as páginas do app ficam em `/frontend/html/...`. Para o ambiente
local replicar isso e o CORS funcionar, sirva a raiz do repositório (não a
pasta `frontend/`):

```bash
# Da raiz do repositório:
python -m http.server 8080

# Ou use Live Server do VS Code na raiz do repositório (porta 5501 etc.)
```

Frontend em: `http://localhost:8080` — e o login em
`http://localhost:8080/frontend/html/auth/login.html`

> O `frontend/js/config.js` aponta para `http://localhost:8000` quando o
> hostname é localhost, e para `https://safemask-backend.onrender.com` em
> produção. Em desenvolvimento o backend aceita qualquer porta de
> localhost/127.0.0.1 via CORS.

---

## 💻 Desenvolvimento

### Backend com Reload Automático

```bash
cd backend
venv\Scripts\activate  # Windows
# ou
source venv/bin/activate  # macOS/Linux

uvicorn app.main:app --reload
```

### Frontend com Live Server

```bash
cd frontend
python -m http.server 8080
```

### Database Operations

```bash
# No terminal da pasta backend (venv ativado)
python

# Dentro do Python:
from app.database import engine
from app.models.usuario import Usuario
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# Consultar
usuarios = session.query(Usuario).all()
for u in usuarios:
    print(u.email)
```

---

## 🔐 Segurança

### Implementado

- ✅ Hash de Senhas: Bcrypt + passlib
- ✅ JWT: Tokens com expiração de 120 minutos
- ✅ CORS: Middleware configurado
- ✅ SQL Injection: Prevenido com ORM (SQLAlchemy)

### Recomendações para Produção

1. **Gere SECRET_KEY forte**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Use HTTPS sempre**

3. **Implemente Rate Limiting** para login

4. **Configure logs** adequados

5. **Faça backups** regulares do banco

6. **Mantenha dependências atualizadas**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

---

## 🚀 Deploy

### Frontend (Vercel)

**Pré-requisitos:**
- Conta em [Vercel.com](https://vercel.com/)
- Repositório GitHub

**Passos:**

1. **Push para GitHub**
   ```bash
   git push origin main
   ```

2. **Acesse Vercel Dashboard**
   - [https://vercel.com/dashboard](https://vercel.com/dashboard)
   - Clique em "New Project"
   - Selecione seu repositório SafeMask

3. **Configure Deploy**
   - **Framework**: "Other"
   - **Root Directory**: raiz do repositório (`./`) — o `index.html` (landing) vive na raiz e as páginas do app em `frontend/html/`
   - **Build Command**: deixe em branco
   - **Output Directory**: deixe em branco (site estático, sem build)

4. **Deploy!**
   - Seu frontend está em: `https://safe-mask.vercel.app`

**Atualizações automáticas:** Qualquer push para `main` redeploya (workflow
`.github/workflows/vercel-merge.yml`).

> A URL do backend em produção é resolvida automaticamente por
> `frontend/js/config.js`: `localhost`/`127.0.0.1` → `http://localhost:8000`;
> qualquer outro hostname → `https://safemask-backend.onrender.com`. Não é
> preciso configurar `REACT_APP_API_URL` (o frontend não usa variáveis de
> ambiente).

### Backend (Render.com - Recomendado)

**Pré-requisitos:**
- Conta em [Render.com](https://render.com/)
- Repositório GitHub

**Passos:**

1. **Criar Web Service a partir do Blueprint**
   - Dashboard → "New +" → "Blueprint"
   - Conectar GitHub e selecionar o repositório SafeMask
   - O `render.yaml` na raiz define tudo: `rootDir: backend`, build
     `pip install -r requirements.txt`, start
     `uvicorn app.main:app --host 0.0.0.0 --port $PORT` e os pacotes apt
     (`tesseract-ocr`/`tesseract-ocr-por`) para o OCR.

2. **Environment Variables** (definidas no dashboard do Render)
   ```
   DATABASE_URL=postgresql://seu_usuario:senha@host/banco?sslmode=require
   SECRET_KEY=sua-chave-secreta-super-segura
   ```

3. **Deploy**
   - Backend em: `https://safemask-backend.onrender.com`
   - Toda alteração no `render.yaml` exige "Sync" do Blueprint no dashboard.

### Conectar Frontend ao Backend

Não é preciso editar nada manualmente: `frontend/js/config.js` escolhe a URL
por hostname (ver acima).

---

## 📋 Conformidade LGPD

SafeMask foi desenvolvido seguindo os princípios da LGPD:

- **Confidencialidade**: Criptografia de dados sensíveis
- **Transparência**: Usuários sabem quais dados são coletados
- **Consentimento**: Registro de consentimento no cadastro
- **Direito ao Esquecimento**: Exclusão de dados de usuários
- **Portabilidade**: Exportação de dados do usuário
- **Segurança**: Proteção contra acessos não autorizados

---

## 🤝 Contribuindo

1. Faça um Fork
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit (`git commit -m 'Add MinhaFeature'`)
4. Push (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Licença

MIT License - veja [LICENSE](LICENSE)

---

## 📞 Suporte

Abra uma issue no GitHub para suporte.

---

## 👥 Equipe Scrum

- **[Marcelo Honda Kobayashi](https://github.com/MarceloKobayashi)** - Product Owner
- **[Lucas Vieira Porto](https://github.com/Lucas-vporto)** - Developer
- **[Dimitri Cinnanti](https://github.com/DimitriSCinnanti)** - Scrum Master
- **[Paulo Henrique Paniago](https://github.com/Paulohspaniago)** - Developer
- **[Gabriel Bernardo Alves](https://github.com/Alves56)** - Developer
- **Victor Oleskovicz** - 

---

<div align="center">

**Desenvolvido com 🔒 e ❤️ para proteção de dados**

[⬆ Voltar ao Topo](#-safemask)

</div>
