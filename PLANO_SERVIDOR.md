# PLANO SERVIDOR — SafeMask como serviço documental da empresa

> **Supersedes `PLANO_AVANCADO.md`** (multi-tenant SaaS). Nova direção acordada com o professor.
> Última revisão: 2026-10-22 · estado do repo: `main @ 87d8157`, 326 testes verdes, ruff limpo.

---

## 1. A virada (o que é o produto agora)

Antes: app web onde pessoas sobem PDFs, IA tarja tudo igual pra todo mundo, download por necessidade.

Agora: **SafeMask é o intermediário dos documentos da empresa**.

- A empresa instala o serviço no próprio servidor (1 instalação = 1 empresa)
- Os documentos ficam **centralizados e sob o controle do sistema** (originais nunca expostos direto)
- Quando alguém **pede** um documento, o sistema identifica o **nível/cargo** da pessoa
  (login próprio mantido) e entrega a **versão censurada adequada** para ela
- Auditoria de "quem pediu o quê e que versão recebeu" é requisito de venda
- Frontend existe, mas é **painel administrativo simples, por empresa** — não é o produto
- Deploy cloud (Render/Vercel) **cortado** — tudo on-premise

### Fundação que já existe e sustenta o modelo

| Peça | Onde | Por que importa |
|---|---|---|
| Mapa estruturado dos dados sensíveis | `DadoSensivel` (`coordenadas`, `espaco_coordenadas`, `nivel_requerido`) | Permite reconstruir o doc conforme o nível de quem pede |
| Reconstrução por persona | `DocumentScanner.gerar_pdf_parcial()` + `GET /documentos/{id}/parcial` | **Já é o fluxo pedido pelo professor** — só falta virar o fluxo padrão |
| Política de visibilidade | `PoliticaNivel` (tipo_entidade → nivel_requerido, por equipe) | Ajuste fino sem código |
| RBAC/níveis | `Cargo` (membro=1, supervisor=2, líder=3), `UsuarioEquipe`, `autorizacao.py` | "Quem pede" já tem identificação segura |
| Auditoria | `log_auditoria` (+ rotas consulta/CSV) | Trilha pronta, falta formalizar no download |
| Detector 100% local | regex + validadores de dígito + NER treinado pelo projeto (`scanner/safemask-ner/`) | Roda offline no servidor do cliente, zero API paga |
| Migrações no boot | `database.py` (`criar_tabelas` + `garantir_schema_*`) | Instalação "roda e pronto" |

---

## FASE 1 — Fluxo de documentos no centro  ← EM ANDAMENTO (prioridade)

> Objetivo: bulk upload + fila + download dinâmico como a entrega padrão.

- [x] **1.1 Bulk upload**
  - `POST /documentos/upload/lote` — multipart com vários PDFs numa requisição
  - Validação (magic bytes `%PDF-`, 20 MB) reaproveitada de `core/uploads.py`
  - Retorna `doc_id` + status inicial para cada arquivo
- [x] **1.2 Fila de processamento**
  - ThreadPoolExecutor (1–2 workers — scan/OCR são pesados) em `core/fila.py` (novo)
  - `status_processamento`: `pendente → processando → pronto | erro`, progresso persistido por doc
  - Endpoint de status (`GET /documentos/{id}` já existe — só expor fila/retry nos metadados)
  - Falha isolada por arquivo: um PDF quebrado não trava o lote
- [x] **1.3 Download dinâmico como padrão**
  - `GET /parcial` promove a entrega principal (original só nível ≥ 3, tarjado fixo como fallback defensivo)
  - **Cache real de versões** por `(doc_id, nivel)`: `gerar_pdf_parcial` reutiliza `_parcial_nivel{N}.pdf` existente em vez de regenerar; invalidação quando política/original muda
- [x] **1.4 Auditoria formalizada**
  - Todo download registra: `doc_id, nivel_cargo_requisitante, versao_entregue (n/n), motivo`
  - Acesso negado também (já há `registrar_acesso_negado` — padronizar mensagens)
- [x] **1.5 Testes do fluxo**
  - `test_upload_lote.py`: lote com 3 PDFs (1 quebrado de propósito), fila processa, status correto
  - `test_entrega_niveis.py`: mesmo doc pedido por 3 cargos → 3 versões certas + cache reutilizável
  - e2e (`scripts/e2e.py`) atualizado com o fluxo lote→scan→pedidos por nível
- [ ] **1.6 Painel (mínimo necessário)**
  - Wizard de upload aceita múltiplos arquivos + fila visível (status em tempo real, polling)
  - Lista de documentos passa a priorizar "abrir versão conforme meu nível" (comportamento atual já ok — revisar textos pra cara de painel admin, não app de usuário)

## FASE 2 — On-premise de verdade (dep. Fase 1)

- [ ] **2.1 Docker-compose**: container backend+frontend + Postgres local + Tesseract `por` no build; NER embutido
- [ ] **2.2 Frontend servido pelo backend**: FastAPI estático a partir da raiz (landing `index.html` incluso) — `config.js` detecta mesmo host
- [ ] **2.3 Seed de instalação**: script/flag no boot cria organização única + usuário admin (senha inicial forçada a trocar no 1º login)
- [ ] **2.4 Suporte a `DATABASE_URL` local** (Postgres no compose; SQLite p/ dev rápido se der)
- [ ] **2.5 Limpeza cloud**: remover `render.yaml`, `vercel.json`, `scripts/warmup.sh`, referências Neon/Render de `docs/` e README
- [ ] **2.6 E-mail opcional**: Brevo só com env ativa; recuperação de senha por admin do painel (ou desativada)
- [ ] **2.7 Guia de instalação**: `docs/instalacao.md` — requisitos, compose up, seed, Tesseract, primeiro acesso

## FASE 3 — Watch de pasta (dep. Fase 2)

- [ ] **3.1** Worker com `watchdog` (ou cron/polling) monitorando pasta configurável
- [ ] **3.2** Ingestão automática → mesma fila/dedupe por hash → mesma auditoria
- [ ] **3.3** Config no `.env` (`WATCH_DIR`, organização/padrão de equipe, política padrão) — off por default

## FASE 4 — Simplificação e polimento (dívida do modelo antigo)

- [ ] **4.1** Cortar multi-org (`tenancy.py`, `garantir_schema_organizacoes`, backfill) — 1 org fixa
- [ ] **4.2** Cortar upload multi-equipes + `duplicar_itens_sensiveis` (item tem 1 dono)
- [ ] **4.3** Cortar `POST /documentos/salvar-censurado` (upload de PDF já tarjado fora; inconsistente com "original sob controle")
- [ ] **4.4** Tarja em camada de texto (pypdf/reportlab) como opção — não rasterizar sempre; PDF menor e pesquisável
- [ ] **4.5** Métricas de uso no painel (docs por nível, acessos negados, top tipos censurados) — alimento pro professor/apresentação
- [ ] **4.6** Limpar legados: `chave_criptografica` sem uso, raster 150 dpi default enquanto 4.4 não existe

## Descartados deliberadamente (não fazer)

- Multi-tenant SaaS / isolamento por organização nas rotas (aqui 1 instalação = 1 empresa) — ver plano antigo em `PLANO_AVANCADO.md`
- Firewalls de rede, DLP de sistema de arquivos, monitorar máquina usada — fora de escopo
- Frontend mobile/desktop — painel web simples basta
- CI/CD Render; free-tier warmup

## Riscos / decisões abertas

- [x] Identidade = login próprio (decidido com usuário) → auth atual fica
- [x] Ingestão = bulk agora, watch depois (decidido)
- [x] Deploy = só on-premise, cloud cortado (decidido)
- [ ] Demo pro professor: rodar em servidor local/VM com compose (segurar 2 containers + OCR) — definir host antes da apresentação
- [ ] "Nunca guardar original legível no disco": hoje original fica em `uploads/originais/`; se exigência do cliente, cifra por chave gerida no boot — decidir na Fase 2
- [ ] Grande volume (milhares de PDFs): OCR sequencial pode demorar dias — avaliar workers paralelos por página na Fase 1.2 se caso real pedir

## Convenções mantidas

- Testes com pytest (backend/.venv), ruff check em `backend/`
- Migrações idempotentes no boot — não introduzir Alembic
- Commits em pt-BR sem acentos (padrão do histórico)
- Rodar `.venv/bin/pytest` a partir de `backend/` (rootdir correto)
