# ESTRUTURA LÓGICA — SafeMask

> Documento único de arquitetura, estrutura, regras de negócio e plano de
> evolução do SafeMask. Substitui o planejamento desktop anterior e concentra
> o estado atual do projeto e as mudanças planejadas para pastas, ACL e níveis
> de acesso.

---

## 1. Visão e escopo

O SafeMask é um software de compliance de documentos **on-premise**:

- **1 instalação = 1 empresa.**
- O serviço central roda no servidor da empresa (FastAPI + SQLite).
- O client desktop roda nas máquinas dos usuários (Tauri + TypeScript).
- O documento original **nunca sai do servidor**; o client recebe a versão
  censurada ou parcial conforme o nível de acesso.
- O scan de dados sensíveis roda **uma vez por documento**, na ingestão.
- O original fica cifrado no storage do serviço.
- Toda entrega, negativa e operação administrativa passa pela auditoria.

O produto não tem frontend web, não hospeda banco em nuvem e não envia
documentos para fora da rede da empresa.

### Arquitetura geral

```text
[Servidor da empresa]                         [Desktops]
+---------------------------------+           +----------------------+
| SafeMask Service (.exe)         |<- HTTP -> | SafeMask Client.exe  |
|  FastAPI + PyInstaller          |           |  Tauri + TypeScript  |
|  SQLite embutido                |           |  login -> pedir doc  |
|  Tesseract por + NER local      |           |  recebe versão       |
|  Watch da pasta base            |           |  censurada/parcial   |
|  Fila de scan                   |           |  admin: gestão       |
|  Original cifrado em disco      |           +----------------------+
+---------------------------------+
        ^ pasta base na rede (admin aponta)
```

### Componentes

| Componente | Responsabilidade |
|---|---|
| Serviço FastAPI | Autenticação, autorização, documentos, equipes, pastas, auditoria, dashboard |
| Scanner | Regex + validadores + NER local para localizar dados sensíveis |
| Fila | Processamento assíncrono dos uploads e da ingestão do watch |
| Watch | Varredura periódica da pasta base e ingestão automática de PDFs |
| Storage cifrado | Originais cifrados e versões censuradas/parciais |
| Client Tauri | Interface do usuário, administração e downloads autenticados |
| SQLite | Metadados, usuários, equipes, pastas, níveis, coordenadas e auditoria |

---

## 2. Estrutura atual do projeto

```text
SafeMask/
├── backend/
│   ├── app/
│   │   ├── main.py                    # aplicação FastAPI, CORS, boot e watch
│   │   ├── database.py                # engine, sessão, create_all e migrações idempotentes
│   │   ├── run_service.py             # entrada do serviço empacotado
│   │   ├── core/
│   │   │   ├── audit.py               # registro central de auditoria
│   │   │   ├── auth.py                # JWT, criação/validação de token
│   │   │   ├── autorizacao.py         # cargos, vínculos e regras de acesso
│   │   │   ├── cifra.py               # cifra e materialização do original
│   │   │   ├── config.py              # limites, magic bytes e configurações gerais
│   │   │   ├── current_user.py        # dependência do usuário autenticado
│   │   │   ├── datas.py               # normalização de datas/UTC
│   │   │   ├── email.py               # envio de e-mail de recuperação
│   │   │   ├── fila.py                # fila de processamento
│   │   │   ├── file_responses.py      # respostas de arquivo com background task
│   │   │   ├── http_headers.py        # headers de segurança
│   │   │   ├── ingestao_pasta.py      # watch, validação e ingestão da pasta base
│   │   │   ├── politica_niveis.py     # política de níveis por equipe (atual)
│   │   │   ├── security.py            # hash de senha
│   │   │   ├── seed_instalacao.py     # organização, admin e equipe padrão
│   │   │   ├── service_config.py      # leitura do service.yaml
│   │   │   ├── tenancy.py             # organização única
│   │   │   ├── troca_senha.py         # troca obrigatória de senha
│   │   │   └── uploads.py             # validação de upload
│   │   ├── models/
│   │   │   ├── cargo.py               # cargos e níveis
│   │   │   ├── dado_sensivel.py       # ocorrências e coordenadas
│   │   │   ├── documentos.py          # documento, hash, storage e status
│   │   │   ├── equipe.py              # equipes da organização
│   │   │   ├── log_auditoria.py       # trilha de auditoria
│   │   │   ├── organizacao.py         # empresa única
│   │   │   ├── politica_nivel.py      # níveis ajustados por equipe (atual)
│   │   │   ├── usuario.py             # usuário, senha e flags
│   │   │   └── usuario_equipe.py      # vínculo usuário-equipe-cargo
│   │   ├── routes/
│   │   │   ├── auth.py                # login, sessão, senha e recuperação
│   │   │   ├── auditoria.py           # consulta e exportação CSV
│   │   │   ├── dashboard.py           # overview e métricas
│   │   │   ├── documentos.py          # upload, listagem, censurado, parcial, original
│   │   │   └── equipes.py             # equipes, membros, cargos e política
│   │   └── schemas/
│   │       ├── auth.py
│   │       ├── documento.py
│   │       ├── equipe.py
│   │       ├── usuario.py
│   │       └── usuario_equipe.py
│   ├── scanner/
│   │   ├── scanner.py                 # orquestra regex, NER, OCR e tarjas
│   │   ├── patterns.py                # padrões regex
│   │   ├── validadores.py             # CPF, CNPJ, CNS etc.
│   │   ├── coordenadas.py             # conversão de coordenadas
│   │   ├── redaction.py               # geração do PDF censurado/parcial
│   │   └── safemask-ner/              # modelo NER local
│   ├── tests/                         # suíte pytest do backend
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── requirements-ia.txt
│   ├── pytest.ini
│   ├── ruff.toml
│   └── safemask_service.spec          # empacotamento PyInstaller
├── client/
│   ├── src/
│   │   ├── main.ts                    # bootstrap do app
│   │   ├── api.ts                     # tipos e chamadas HTTP
│   │   ├── app.ts                     # shell, telas e estado da UI
│   │   ├── demo.ts                    # backend fictício do modo demonstração
│   │   └── app.css                    # design system e layout
│   ├── src-tauri/                     # configuração, Rust e ícones do Tauri
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── scripts/
│   ├── e2e.py                         # smoke test da API
│   └── gerar_pdf_exemplo.py           # PDFs de exemplo
├── docs/
│   └── instalacao.md                  # instalação, configuração e checklist
├── documentation/                     # relatórios, sprints e documentos acadêmicos
├── README.md
├── estrutura_logica.md                # este documento
└── .github/workflows/ci-backend.yml   # CI do backend
```

Artefatos gerados não fazem parte da estrutura lógica: `node_modules/`,
`client/src-tauri/target/`, `client/dist/`, `backend/build/`, `backend/dist/`,
`backend/uploads/`, `.venv/`, `__pycache__/` e caches.

---

## 3. Modelo de domínio atual

```text
Organizacao (única por instalação)
└── Equipe
    └── UsuarioEquipe (usuário + cargo)
        └── Documento (dono atual: user_team_id)
            └── DadoSensivel
```

### Entidades

| Entidade | Campos principais | Papel |
|---|---|---|
| `Organizacao` | `organizacao_id`, `nome` | Empresa dona da instalação |
| `Equipe` | `team_id`, `nome`, `descricao`, `organizacao_id` | Agrupamento de usuários |
| `Cargo` | `cargo_id`, `nome`, `nivel` | Membro=1, supervisor=2, líder=3 |
| `Usuario` | `user_id`, `nome`, `email`, `senha_hash`, flags | Conta de acesso |
| `UsuarioEquipe` | `user_team_id`, `user_id`, `team_id`, `cargo_id` | Vínculo e cargo na equipe |
| `Documento` | `doc_id`, `user_team_id`, `nome_original`, `hash_documento`, `status_processamento`, `caminho_storage` | Documento ingerido |
| `DadoSensivel` | `doc_id`, `tipo_entidade`, `nivel_requerido`, `coordenadas`, `espaco_coordenadas` | Ocorrência detectada |
| `PoliticaNivel` | `team_id`, `tipo_entidade`, `nivel_requerido` | Ajuste de nível por equipe |
| `LogAuditoria` | usuário, ação, documento, equipe, resultado, detalhe, data | Trilha central |

### Como o acesso funciona hoje

- `Documento.user_team_id` aponta para o vínculo de equipe dona do documento.
- O usuário precisa pertencer à equipe dona para ver o documento.
- O cargo do usuário nessa equipe define o que ele vê:
  - membro (1);
  - supervisor (2);
  - líder (3).
- `NIVEL_MIN_DESCENSURA = NIVEL_LIDER`: hoje o líder recebe o original integral.
- A política de níveis é aplicada no upload, conforme a equipe de destino.
- O original é cifrado em disco, mas é entregue ao líder via
  `/documentos/{id}/original` e via `/documentos/{id}/parcial`.

---

## 4. Estrutura lógica alvo

A evolução substitui o acesso por equipe dona do documento por acesso por
**pasta compartilhada**.

```text
Organização (empresa)
├── Equipes
│   ├── Financeiro
│   ├── Jurídico
│   └── RH
│
└── Pastas
    └── Documentos da empresa          (admin global)
        ├── Financeiro                 (ACL: Financeiro ler)
        │   ├── Contratos              (ACL: Financeiro ler + Jurídico gerenciar)
        │   └── Folha                  (ACL: Financeiro gerenciar)
        └── Jurídico                   (ACL: Jurídico gerenciar)
            └── Processos              (herda Jurídico)
```

Regras:

- Um documento pertence a **uma pasta**.
- O acesso vem da pasta, não mais da equipe de origem do documento.
- Para duas equipes verem o mesmo documento, compartilha-se a pasta.
- Subpastas são ilimitadas.
- Subpasta herda a ACL do pai por padrão.
- `herda_acl = false` quebra a herança e permite uma subpasta privada.
- Só o admin global altera ACL, move pastas ou quebra herança.
- Líderes com `gerenciar` cuidam do conteúdo da pasta.

### Novas entidades e colunas

```text
Pasta
- pasta_id
- organizacao_id
- parent_id
- nome
- caminho_rede          # opcional; liga à subpasta física da rede
- herda_acl             # default true
- criado_em

PastaEquipe
- pasta_id
- team_id
- permissao             # ler | gerenciar

Documento
- pasta_id              # novo, obrigatório após migração
- criado_por_user_id    # novo
- equipe_origem_id      # opcional; apenas procedência

Usuario
- admin_organizacao     # novo: admin global da empresa

PoliticaNivel
- pasta_id              # passa a ser a chave
- tipo_entidade
- nivel_requerido       # 1..4
```

`Documento.user_team_id` deixa de decidir acesso. Ele permanece apenas como
procedência histórica até ser substituído por `equipe_origem_id`.

### Permissões

| Quem | Pode |
|---|---|
| Admin global | Ver tudo, criar/mover/compartilhar pastas, enviar, baixar original, ajustar qualquer nível |
| Equipe com `gerenciar` | Membros leem; líderes enviam documentos e criam/renomeiam subpastas |
| Equipe com `ler` | Membros leem os documentos da pasta |
| Equipe sem ACL | Não vê a pasta nem os documentos |

Definições operacionais:

- `gerenciar` inclui leitura.
- Upload exige admin global ou líder de equipe com `gerenciar`.
- Criar/renomear subpasta exige admin global ou líder com `gerenciar`.
- Mover pasta, alterar ACL, quebrar herança e excluir pasta: somente admin global.
- Excluir pasta com documentos ou subpastas é bloqueado; a saída é arquivar.

### Cálculo do acesso efetivo

1. Se `Usuario.admin_organizacao = true`, acesso total e nível efetivo 4.
2. Senão, calcular a ACL efetiva da pasta:
   - `herda_acl = true`: unir a ACL dos ancestrais;
   - `herda_acl = false`: usar somente a ACL própria.
3. O usuário precisa pertencer a alguma equipe da ACL efetiva.
4. O cargo efetivo é o maior cargo do usuário entre as equipes com acesso.
5. O acesso à pasta é `ler` ou `gerenciar`, conforme a permissão da equipe.
6. Documentos herdam o acesso da pasta.

Importante: cargo de uma equipe **sem acesso** à pasta não conta para o
cargo efetivo.

---

## 5. Níveis de dados e original

### Escala

| Nível | Quem vê | Uso |
|---|---|---|
| 1 | Membro, supervisor, líder, admin | Dados de baixa sensibilidade |
| 2 | Supervisor, líder, admin | Dados pessoais comuns |
| 3 | Líder, admin | Dados sensíveis operacionais |
| 4 | Somente admin global | Dados críticos |

`NIVEL_MAXIMO = 4`. Admin global tem nível efetivo 4.

### Dados nível 4

Passam a exigir admin global:

- CPF;
- RG;
- CNH;
- CNS;
- CID-10;
- CRM.

CNH fica fixa em nível 4 no mapa do NER. Os demais aparecem na política da
pasta. Líder de equipe pode ajustar níveis 1–3; nível 4 só o admin global
ajusta. Líder não pode rebaixar um tipo crítico para 3.

### Original e parcial

- `GET /documentos/{id}/original` exige `admin_organizacao`.
- `GET /documentos/{id}/parcial` sempre aplica censura dos níveis acima do
  cargo efetivo.
- Líder não recebe mais o original integral automaticamente.
- Líder vê dados de nível 1–3; nível 4 permanece tarjado.
- Se um documento não tiver dados acima do cargo, a parcial pode revelar todo
  o conteúdo não crítico; isso é esperado.
- O cache de versões continua por documento + conjunto de caixas; mudanças de
  ACL não invalidam o cache, pois ele não depende do usuário.

---

## 6. Política de níveis por pasta

Com pastas compartilhadas, política por equipe gera conflito: duas equipes com
níveis diferentes para o mesmo documento. A política passa a ser **por pasta**.

- `PoliticaNivel.pasta_id` substitui `team_id`.
- Documentos novos usam a política da pasta de destino.
- Documentos antigos mantêm o nível já gravado em `DadoSensivel`.
- Pasta sem ajuste usa o padrão de `configuracoes_regex()`.
- Na migração, a política de cada equipe é copiada para a pasta da equipe.
- O admin global pode ajustar qualquer tipo e nível.
- O líder da equipe gestora pode ajustar níveis 1–3.
- Nível 4 é protegido para não-admin.

---

## 7. Ingestão e watch híbrido

O watch continua sendo o fluxo principal de ingestão, mas agora mapeia
subpastas físicas para pastas lógicas.

```text
pasta_base/Financeiro/Contratos/contrato.pdf
        │
        ▼
procura pasta lógica com caminho_rede = "Financeiro/Contratos"
        │
        ├── encontrou -> usa ACL e política dessa pasta
        │
        └── não encontrou -> cria árvore de pastas automaticamente
                             sem ACL, herda_acl = false
                             visível só para admin global
```

Regras:

- O mapeamento é explícito por `caminho_rede`.
- Auto-criadas quebram herança para não vazar acesso por engano.
- O admin compartilha a pasta depois.
- Dedupe continua global por empresa: o mesmo hash não é ingerido duas vezes.
- O original é copiado e cifrado no storage do serviço.
- O arquivo na pasta base segue sob controle da empresa.
- A ACL do SafeMask é lógica. Permissões do compartilhamento Windows são
  responsabilidade da empresa; quem tiver acesso direto ao share pode ignorar
  o app.

---

## 8. Fluxos principais

### Login e primeiro acesso

1. Client valida a URL do serviço contra `/auth/me`.
2. Usuário faz login e recebe JWT.
3. Admin provisório é obrigado a trocar a senha.
4. Token e flags do usuário são usados nas chamadas seguintes.

### Upload individual

1. Usuário escolhe a pasta e envia o PDF.
2. Backend valida permissão de `gerenciar` na pasta.
3. Arquivo é validado e o original é cifrado no storage.
4. Scanner roda uma vez e grava `DadoSensivel`.
5. Documento fica vinculado à pasta.
6. Auditoria registra o upload.

### Upload em lote

1. Vários PDFs são validados individualmente.
2. Válidos entram na fila; inválidos são recusados nominalmente.
3. Documentos nascem com `AGUARDANDO` e viram `PROCESSANDO`/`CONCLUIDO`.
4. A lista do client atualiza o status.

### Watch

1. Ciclo periódico varre `pasta_base` por PDFs.
2. Valida magic bytes e tamanho.
3. Calcula hash e evita duplicidade.
4. Resolve a pasta lógica por `caminho_rede`.
5. Se não existir, cria a árvore admin-only.
6. Copia o original cifrado e agenda o scan.
7. Auditoria registra a ingestão.

### Scan

1. Materializa o original temporariamente.
2. Aplica regex, validadores, NER e OCR quando necessário.
3. Grava coordenadas, tipo e nível em `DadoSensivel`.
4. Gera a versão totalmente censurada.
5. Descarta o material temporário.
6. IA não roda novamente no download.

### Download

- **Censurado:** versão com todos os dados sensíveis tarjados.
- **Parcial:** revela somente níveis `<= cargo efetivo`.
- **Original:** somente admin global.
- Toda entrega e negativa gera auditoria.

### Pastas

1. Admin cria a pasta raiz e as pastas das equipes.
2. Admin compartilha pastas com equipes e define `ler`/`gerenciar`.
3. Líder com `gerenciar` cria subpastas e envia documentos.
4. Subpasta herda ACL ou quebra herança.
5. Admin move, arquiva ou exclui pastas vazias.

---

## 9. Backend

### Responsabilidades por módulo

| Módulo | Responsabilidade |
|---|---|
| `app/main.py` | Montagem da API, CORS, boot, seed, migrações e watch |
| `app/database.py` | Engine, sessão, criação de tabelas e migrações idempotentes |
| `app/core/auth.py` | JWT e autenticação |
| `app/core/current_user.py` | Usuário atual |
| `app/core/autorizacao.py` | Cargos, vínculos, ACL de pasta e acesso a documento |
| `app/core/politica_niveis.py` | Política de níveis por pasta |
| `app/core/ingestao_pasta.py` | Watch e mapeamento de subpastas |
| `app/core/cifra.py` | Cifra e leitura temporária do original |
| `app/core/audit.py` | Registro central de eventos |
| `app/core/fila.py` | Fila de scan |
| `app/core/seed_instalacao.py` | Organização, admin global, equipe e pasta raiz |
| `app/core/tenancy.py` | Organização única |
| `app/routes/documentos.py` | Upload, listagem, censurado, parcial e original |
| `app/routes/equipes.py` | Equipes, membros, cargos e política |
| `app/routes/dashboard.py` | Overview e métricas |
| `app/routes/auditoria.py` | Consulta e exportação |
| `scanner/*` | Detecção, validação, coordenadas e tarjas |

### Endpoints atuais relevantes

```text
POST /auth/login
GET  /auth/me
POST /auth/trocar-senha
POST /documentos/upload
POST /documentos/upload/lote
GET  /documentos/censurados
GET  /documentos/censurados/{doc_id}
GET  /documentos/censurados/{doc_id}/arquivo
GET  /documentos/{doc_id}/parcial
GET  /documentos/{doc_id}/original
GET  /documentos/listar/{team_id}
GET  /equipes/overview
GET  /equipes/{team_id}
POST /equipes
POST /equipes/{team_id}/membros
PATCH /equipes/{team_id}/membros/{user_id}
DELETE /equipes/{team_id}/membros/{user_id}
GET  /equipes/{team_id}/politica-niveis
PUT  /equipes/{team_id}/politica-niveis
GET  /dashboard/overview
GET  /dashboard/metricas
GET  /auditoria
GET  /auditoria/exportar
```

### Endpoints novos/alterados

```text
GET    /pastas/arvore
GET    /pastas/{pasta_id}
POST   /pastas
PATCH  /pastas/{pasta_id}
DELETE /pastas/{pasta_id}
PUT    /pastas/{pasta_id}/equipes
PATCH  /pastas/{pasta_id}/heranca
GET    /pastas/{pasta_id}/politica-niveis
PUT    /pastas/{pasta_id}/politica-niveis
GET    /pastas/{pasta_id}/documentos

POST /documentos/upload          -> pasta_id em vez de teams
POST /documentos/upload/lote     -> pasta_id em vez de team_id
GET  /documentos/censurados      -> filtro opcional pasta_id
GET  /documentos/censurados/{id} -> inclui pasta e caminho
GET  /documentos/{id}/original   -> somente admin global
GET  /documentos/{id}/parcial    -> cargo efetivo da pasta

PATCH /admin/usuarios/{id}/admin-global
```

### Rotas que mudam de regra

- `documentos.py`: upload, listagem, parcial e original deixam de usar
  `user_team_id` como fonte de acesso.
- `equipes.py`: contagens e política passam a considerar pastas.
- `dashboard.py`: métricas passam a contar documentos únicos por pasta/equipe.
- `auditoria.py`: eventos ganham contexto de pasta.
- `politica_niveis.py`: chave muda de equipe para pasta.

---

## 10. Banco de dados

### Tabelas atuais

```text
organizacao
equipe
cargo
usuario
usuario_equipe
documentos
dado_sensivel
politica_nivel
log_auditoria
```

### Tabelas novas

```text
pasta
pasta_equipe
```

### Relacionamentos alvo

```text
organizacao 1---N equipe
organizacao 1---N pasta
pasta       1---N pasta (parent_id)
pasta       1---N pasta_equipe N---1 equipe
pasta       1---N documentos
documentos  1---N dado_sensivel
pasta       1---N politica_nivel
usuario     1---N documentos (criado_por_user_id)
```

### Migração

1. Criar `pasta` e `pasta_equipe`.
2. Adicionar `documentos.pasta_id`, `documentos.criado_por_user_id` e
   `usuario.admin_organizacao`.
3. Adicionar `politica_nivel.pasta_id`.
4. Criar pasta raiz `Documentos da empresa`, sem ACL.
5. Criar uma subpasta para cada equipe existente.
6. Compartilhar cada subpasta com a própria equipe.
7. Copiar a política de níveis da equipe para a pasta dela.
8. Mover os documentos atuais para a pasta da equipe de origem.
9. Preencher `pasta_id` e depois tornar obrigatório.
10. Marcar o admin do seed como `admin_organizacao = true`.
11. Manter fallback temporário para documentos sem pasta durante a migração.

As migrações seguem o padrão de `database.py`: idempotentes, no boot, sem
Alembic. Uma função `garantir_schema_pastas()` deve ser chamada em
`app/main.py` junto das demais.

---

## 11. Client Tauri

### Telas atuais

- Primeiro uso: configuração da URL do serviço.
- Login.
- Troca de senha obrigatória.
- Documentos: lista, status da fila, download censurado/parcial.
- Revisão do documento.
- Equipes: criação, membros, cargos e política.
- Painel: métricas.
- Auditoria: consulta e exportação CSV.
- Menu de conta.
- Modo demonstração.

### Mudanças planejadas

- Árvore de pastas à esquerda na tela de documentos.
- Breadcrumb da pasta atual.
- Upload dentro da pasta atual.
- Botão de upload só para quem pode `gerenciar`.
- Administração de pastas para o admin global:
  - criar, renomear, mover;
  - compartilhar com equipes;
  - ligar/desligar herança;
  - mapear `caminho_rede`;
  - editar política de níveis.
- Revisão mostra pasta, caminho e equipes com acesso.
- Botão “Original integral” só para admin.
- Líderes veem “Versão parcial”; nível 4 continua tarjado.
- Menu de administração só aparece para `admin_organizacao`.
- Modo demonstração ganha pastas fictícias, ACL, herança e flag de admin.

### Arquivos do client

| Arquivo | Papel |
|---|---|
| `src/main.ts` | Bootstrap |
| `src/api.ts` | Tipos e chamadas HTTP |
| `src/app.ts` | Shell, telas e estado |
| `src/demo.ts` | Backend fictício do modo demonstração |
| `src/app.css` | Design system e layout |
| `src-tauri/tauri.conf.json` | Janela, CSP e bundle |

---

## 12. Configuração e deploy

### service.yaml

```yaml
pasta_base: "C:/SafeMask/inbox"
porta: 8000
equipe_padrao: "Documentos da empresa"
intervalo_watch: 10
```

Variáveis equivalentes:

- `SERVICE_PASTA_BASE`
- `SERVICE_PORTA`
- `SERVICE_EQUIPE_PADRAO`
- `SERVICE_INTERVALO_WATCH`

### Servidor

- `safemask_service.exe` gerado pelo PyInstaller.
- Tesseract 5.x com idioma `por`.
- NSSM opcional para rodar como serviço do Windows.
- SQLite local; `DATABASE_URL` aceita PostgreSQL opcional.
- `chave_original.key` deve ter backup obrigatório.

### Client

```bash
cd client
npm install
npm run tauri dev
npm run tauri build
```

Build do Tauri exige Rust + WebKitGTK (Linux) ou MSVC/WebView2 (Windows).

### Desenvolvimento backend

```bash
cd backend
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/uvicorn app.main:app --reload
```

---

## 13. Histórico migrado do planejamento anterior

### Fase 0 — Virada documental e limpeza

- Plano desktop escrito.
- Remoção do cloud: `render.yaml`, `vercel.json`, `warmup.sh`, workflow
  `vercel-merge.yml`.
- Front web arquivado; produto desktop-only.
- Multi-organização cortada; 1 instalação = 1 organização.
- Upload multi-equipes removido; documento tem um dono.
- `POST /documentos/salvar-censurado` removido.
- SQLite como padrão.
- pytest + ruff verdes após os cortes.

### Fase 1 — Serviço empacotável

- Watch de pasta com polling por hash.
- Seed de instalação: organização, admin provisório e equipe padrão.
- Configuração via `service.yaml`.
- PyInstaller + serviço Windows.
- Commit `a80cc72`.

### Fase 2 — Client Tauri

- Scaffold Tauri 2 + Vite + TypeScript puro.
- UI nova: primeiro uso, login, troca de senha, documentos, equipes,
  auditoria, upload em lote e status da fila.
- CORS para origem Tauri.
- Admin no mesmo executável.

### Fase 3 — Fechamento de compliance

- Cifra do original em disco — commit `30147b4`.
- Métricas no painel admin — commit `b3a8fb9`.
- Auditoria em 100% dos fluxos — commit `52e4761`.

### Fase 4 — Instalação e demo

- `docs/instalacao.md` com requisitos, execução, pasta base e primeiro acesso.
- Modo demonstração no client — commits `e899af7` e `2c116ad`.
- Redesign do client conforme Figma — commit `02e302d`.
- Teste em VM Windows com pasta de rede real e 2 clients: **pendente**.

### Reaproveitar vs descartar

| | Itens |
|---|---|
| Reaproveita | `backend/app`, `scanner/`, testes pytest |
| Adapta | SQLite padrão, seed, API pura, client Tauri |
| Descarta | frontend web, `index.html`, `render.yaml`, `vercel.json`, `warmup.sh`, multi-org, upload multi-equipes, `salvar-censurado` |

---

## 14. Status atual e próximas fases

### Concluído

- Fases 0, 1, 2, 3 e 4.1.
- Modo demonstração.
- Redesign do client.
- Cifra, métricas e auditoria.
- Documentação de instalação.

### Pendente

- Fase 4.2: teste em VM Windows com pasta de rede real e 2 clients.
- Feature de pastas, ACL e níveis 4/admin.

### Fases da feature de pastas

**Fase 1 — Modelo e migração**

- `models/pasta.py`, `models/pasta_equipe.py`.
- `Documento.pasta_id`, `Usuario.admin_organizacao`.
- `PoliticaNivel.pasta_id`.
- Migração/backfill em `database.py`.
- Seed da pasta raiz e admin global.

**Fase 2 — Autorização**

- Helpers em `core/autorizacao.py`:
  - `acesso_pasta`;
  - `equipes_com_acesso`;
  - `pode_gerenciar_pasta`;
  - `nivel_efetivo_documento`;
  - `pode_ver_original`.
- Remover dependência de `Documento.user_team_id` para acesso.
- Restringir original ao admin.
- Nível 4 no scanner e na política.

**Fase 3 — CRUD de pastas**

- Rotas, schemas e validações.
- Herança, quebra de herança e prevenção de ciclo.
- Auditoria de pastas.

**Fase 4 — Documentos e watch**

- Upload por `pasta_id`.
- Listagem por pasta.
- Ingestão híbrida com `caminho_rede`.
- Auto-criação admin-only.
- Política por pasta no scan.

**Fase 5 — Dashboard, equipes e auditoria**

- Contagens sem duplicar documentos compartilhados.
- “Documentos acessíveis” por equipe, com sobreposição explícita.
- Filtros por pasta.

**Fase 6 — Client**

- Árvore, breadcrumb e upload por pasta.
- Administração de pastas e ACL.
- Política por pasta.
- Original só admin.

**Fase 7 — Testes**

- ACL, herança, subpasta privada e admin global.
- Nível 4 e original.
- Migração/backfill.
- Watch híbrido.
- E2E com duas equipes e pasta compartilhada.

### Critérios de aceite da feature de pastas

- Duas equipes leem a mesma pasta compartilhada.
- Equipe sem ACL não vê pasta nem documentos.
- Subpasta com herança quebrada não vaza para a equipe do pai.
- Só líder com `gerenciar` e admin global enviam documentos.
- Só admin global baixa o original.
- Líder não vê CPF/RG/CNH/CNS/CID/CRM via parcial.
- Watch cria pasta admin-only quando não há mapeamento.
- Documento existente continua acessível após a migração.
- Contagens do dashboard não duplicam documento compartilhado.
- pytest, ruff, tsc e build passam.

---

## 15. Riscos e decisões

### Riscos

- Tesseract no PyInstaller é a maior dor; plano B é instalar/checar antes de subir.
- Watch em share de rede perde eventos; polling por hash é o mecanismo garantido.
- UI nova sem testes automatizados no MVP; validação manual em VM.
- Windows ainda não validado.
- CSP do Tauri precisa de `connect-src` para o client real acessar o servidor.
- A ACL do SafeMask não substitui permissões do share Windows.
- Dedupe global impede o mesmo PDF em duas pastas como cópias independentes.
- Excluir pasta com conteúdo deve ser bloqueado para não perder documentos.
- A chave `chave_original.key` precisa de backup; sem ela os originais são ilegíveis.

### Decisões fechadas

- Pastas compartilhadas entre equipes.
- Admin global da empresa.
- Criação híbrida de pastas.
- Subpastas ilimitadas.
- Herança de ACL por padrão, com quebra.
- Upload só por quem gerencia a pasta.
- Original só por admin global.
- Watch sem mapeamento cria pasta admin-only.
- Política de níveis por pasta.
- Nível 4/admin para dados críticos.
- Só admin global altera ACL.
- Documento pertence a uma pasta.
- Dedupe global por empresa.
- Pasta com conteúdo não é excluída de verdade.

---

## 16. Convenções

- Testes com pytest em `backend/.venv`.
- Rodar `.venv/bin/pytest` a partir de `backend/`.
- `ruff check .` em `backend/`.
- Migrações idempotentes no boot; não introduzir Alembic.
- Commits em pt-BR sem acentos, seguindo o histórico.
- Não versionar segredos, `.env`, chave de cifra, banco local ou uploads.
- Client: `npx tsc --noEmit` e `npm run build` antes de commit.
- Tauri: usar `PATH="$HOME/.cargo/bin:$PATH"` em shells não interativos.
