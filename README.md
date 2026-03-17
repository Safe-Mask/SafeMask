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

---

## 📖 Índice

- [Visão Geral](#-visão-geral)
- [Stack Tecnológico](#-stack-tecnológico)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Instalação](#-instalação)
- [API Endpoints](#-api-endpoints)
- [Desenvolvimento](#-desenvolvimento)
- [Deploy](#-deploy)
- [Conformidade LGPD](#-conformidade-lgpd)

---

## 🎯 Visão Geral

SafeMask é uma plataforma full-stack especializada em proteção de dados sensíveis que permite:

- **Usuários**: Registrar-se, fazer login seguro e gerenciar seus documentos
- **Equipes**: Criar, entrar e gerenciar suas equipes
- **Processamento de Documentos**: Upload e armazenamento seguro de arquivos com múltiplos níveis de segurança
- **Detecção de Dados Sensíveis**: Identificação automática de informações confidenciais (CPF, CNJ, emails, etc.)
- **Censura Automática**: Mascaramento inteligente de dados sensíveis em documentos
- **Integridade de Dados**: Hash de documentos para verificação de integridade
- **Criptografia**: Armazenamento seguro com chaves criptográficas
- **Autenticação JWT**: Sistema de autenticação robusto com tokens JWT e bcrypt
- **Conformidade LGPD**: Garantia de proteção de dados pessoais conforme legislação vigente

---

## 🛠️ Stack Tecnológico

### Backend
- **FastAPI 0.115** (Framework web assíncrono)
- **Python 3.9+** (Linguagem principal)
- **SQLAlchemy 2.0** (ORM)
- **PostgreSQL 15** (Banco de dados)
- **JWT** (JSON Web Tokens - Autenticação)
- **Passlib + Bcrypt** (Hash e verificação de senhas)
- **Pydantic 2.0** (Validação de dados)
- **python-jose** (Suporte a JWT)
- **CORS Middleware** (Controle de origem cruzada)

### Frontend
- **HTML5** (Estrutura)
- **CSS3** (Estilização responsiva)
- **JavaScript Vanilla** (Interatividade e requisições à API)
- **Modern Web APIs** (Fetch, LocalStorage, etc.)

### Database
- **PostgreSQL 15** (Banco de dados relacional)

---

## 📁 Estrutura do Projeto

```
SafeMask/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── auth.py              # Autenticação
│   │   │   ├── security.py          # Funções de segurança JWT e criptografia
│   │   │   └── current_user.py      # Usuário atual autenticado
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── usuario.py           # Modelo de usuário
│   │   │   └── documentos.py        # Modelo de documento
│   │   ├── routes/
│   │   │   └── auth.py              # Rotas de autenticação
│   │   ├── schemas/
│   │   │   ├── usuario.py           # Schema Pydantic para usuário
│   │   │   └── documento.py         # Schema Pydantic para documento
│   │   ├── database.py              # Configuração do banco de dados
│   │   └── main.py                  # Aplicação FastAPI principal
│   └── requirements.txt              # Dependências Python
│
├── frontend/
│   ├── css/
│   │   ├── styles.css               # Estilos da landing page
│   │   └── login.css                # Estilos do sistema de autenticação
│   ├── html/
│   │   └── auth/
│   │       └── login.html           # Página de login/cadastro
│   ├── js/
│   │   ├── script.js                # Scripts gerais
│   │   └── login.js                 # Lógica de autenticação
│   ├── images/                      # Assets e imagens
│   └── index.html                   # Landing page principal
│
└── render.yaml                       # Configuração para deploy no Render
```

---

## 🚀 Instalação

### Pré-requisitos

- Python >= 3.9
- pip >= 21.0
- PostgreSQL >= 15 (local ou em container)

### Passo 1: Clone o repositório

```bash
git clone https://github.com/yourusername/SafeMask.git
cd SafeMask
```

### Passo 2: Inicie o PostgreSQL

**Opção A: Usando Docker**
```bash
docker run --name safemask-postgres -e POSTGRES_PASSWORD=password \
  -e POSTGRES_USER=user -e POSTGRES_DB=safemask_db \
  -p 5432:5432 -d postgres:15
```

**Opção B: PostgreSQL Local**
Certifique-se de que o PostgreSQL está instalado e rodando.

### Passo 3: Configure o Backend

```bash
cd backend

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# No Windows:
venv\Scripts\activate
# No macOS/Linux:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
echo "DATABASE_URL=postgresql://user:password@localhost:5432/safemask_db" > .env
echo "SECRET_KEY=sua-chave-secreta-super-segura-aqui" >> .env

# Inicie o servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend disponível em: `http://localhost:8000`

Documentação interativa da API: `http://localhost:8000/docs`

### Passo 4: Configure o Frontend

```bash
# Abra index.html em um servidor local ou navegador
cd frontend
# Se tiver Python instalado, pode servir com:
python -m http.server 8080
```

Frontend disponível em: `http://localhost:8080`

### Variáveis de Ambiente

**Backend (.env)**
```env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/safemask_db?sslmode=require"

# JWT
SECRET_KEY="sua-chave-super-secreta-mude-isso-em-producao"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=120

# Server
PORT=8000
NODE_ENV=development

# CORS
CORS_ORIGIN="http://localhost:8080"
```

---

## 📚 API Endpoints

### Base URL
```
http://localhost:8000
```

### Documentação Interativa
```
http://localhost:8000/docs  (Swagger UI)
```

### Autenticação

```http
POST   /auth/login              # Login do usuário
POST   /auth/cadastro           # Cadastro de novo usuário
GET    /auth/me                 # Dados do usuário autenticado
```

**Login Request:**
```json
{
  "email": "usuario@example.com",
  "senha_hash": "senha123"
}
```

**Login Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Cadastro Request:**
```json
{
  "nome": "João da Silva",
  "email": "joao@example.com",
  "senha_hash": "senha123"
}
```

### Documentos (A Implementar)

```http
GET    /documentos              # Listar documentos do usuário
GET    /documentos/:id          # Detalhes do documento
POST   /documentos              # Upload de novo documento
PATCH  /documentos/:id          # Atualizar documento
DELETE /documentos/:id          # Deletar documento
```

---

## 💻 Desenvolvimento

### Backend

```bash
# Ativar ambiente virtual
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Desenvolvimento com reload automático
uvicorn app.main:app --reload

# Debug
python -m uvicorn app.main:app --reload --log-level debug

# Testar
pytest  # quando testes forem adicionados

# Atualizar dependências
pip freeze > requirements.txt
```

### Frontend

```bash
# Desenvolvimento local
cd frontend
python -m http.server 8080  # Serve na porta 8080

# Ou use Live Server no VS Code
# ou qualquer outro servidor local
```

### Database Operations

```bash
# Dentro do backend com venv ativado

# Acessar shell interativo do SQLAlchemy
python

# dentro do python:
from app.database import engine
from app.models.usuario import Usuario
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# Consultar usuários
usuarios = session.query(Usuario).all()
```

---

## 🌐 Deploy

### Backend (Render)

1. **Prepare o repositório Git**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Crie Web Service no Render**
   - Acesse [render.com](https://render.com)
   - Clique em "New+" > "Web Service"
   - Conecte seu repositório GitHub

3. **Configure o serviço:**
   - **Name**: `safemask-backend`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install uv && uv sync`
   - **Start Command**: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. **Adicione Variáveis de Ambiente:**
   - `DATABASE_URL`: Sua string de conexão PostgreSQL
   - `SECRET_KEY`: Chave segura aleatória (mude para produção!)
   - `ALGORITHM`: `HS256`
   - `NODE_ENV`: `production`

5. **Deploy automático**
   - Render fará deploy automático a cada push em `main`

### Database (Neon ou Render Postgres)

**Opção A: Neon (Recomendado)**
1. Crie conta em [neon.tech](https://neon.tech)
2. Crie novo projeto
3. Copie a connection string
4. Atualize `DATABASE_URL` no Render

**Opção B: Render Postgres**
1. No Render, crie "PostgreSQL" service
2. Use a connection string gerada

### Frontend (Static)

Se for servir o frontend estaticamente:

**Opção A: Render Static Site**
```bash
cd frontend
# Usar um build simples para minificar assets
npx minify html/**/*.html -o dist/
```

**Opção B: Netlify**
1. Conecte o repositório
2. Deploy automático de `/frontend`

**Opção C: GitHub Pages**
```bash
git subtree push --prefix frontend origin gh-pages
```

---

## 🔐 Segurança

### Melhores Práticas Implementadas

- ✅ **Hash de Senhas**: Bcrypt com passlib
- ✅ **JWT**: Tokens com expiração
- ✅ **CORS**: Middleware configurado
- ✅ **SQL Injection**: Prevenido com ORM
- ✅ **Criptografia de Documentos**: Chaves criptográficas por documento
- ✅ **Integridade**: Hash SHA dos documentos

### Recomendações para Produção

1. **Secret Key**: Gere uma chave aleatória forte
   ```python
   import secrets
   print(secrets.token_urlsafe(32))
   ```

2. **HTTPS**: Sempre use HTTPS em produção

3. **Rate Limiting**: Implemente limitação de taxa para login

4. **Logs**: Configure logging adequado

5. **Backups**: Faça backup regular do banco

---

## 📋 Conformidade LGPD

SafeMask foi desenvolvido com conformidade à Lei Geral de Proteção de Dados (LGPD):

- **Confidencialidade**: Criptografia de dados sensíveis
- **Transparência**: Usuários sabem quais dados são armazenados
- **Consentimento**: Registro de consentimento em cadastro
- **Direito ao Esquecimento**: Exclusão de dados de usuários
- **Portabilidade**: Exportação de dados do usuário
- **Segurança**: Proteção contra acessos não autorizados

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📝 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

---

## 📞 Suporte

Para suporte, abra uma issue no GitHub ou entre em contato através da landing page.

---

## 👥 Equipe Scrum

- **Marcelo Honda Kobayashi** - Product Owner
- **Lucas Vieira Porto** - Developer Team
- **Dimitri Cinnanti** - Scrum Master
- **Paulo Henrique Paniago** - Developer Team
- **Gabriel Bernardo Alves** - Developer Team
- **Victor Oleskovicz** - 

---

<div align="center">

**Desenvolvido com 🔒 e ❤️ para proteção de dados**

[⬆ Voltar ao Topo](#-safemask)

</div>
