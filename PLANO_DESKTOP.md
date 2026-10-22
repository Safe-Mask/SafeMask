# PLANO DESKTOP — SafeMask como software de compliance on-premise

> **Supersedes `PLANO_SERVIDOR.md`** (apagado junto com `PLANO_AVANCADO.md`; historico no git).
> Virada acordada em 2026-10-22: abandonar front web + deploy cloud.
> Produto agora = **client desktop (Tauri) + servico central (.exe PyInstaller)**.
> Estado no momento da virada: branch `lucas`, 299 testes verdes (operacoes removidas levaram os proprios testes junto), ruff limpo.
> Commit da virada apenas na branch `lucas`/`origin/Lucas` — transicao para a `main` decidida com a equipe quando o prototipo do MVP estiver pronto.

---

## 1. O produto agora

- Servico instalado no servidor da empresa (1 instalacao = 1 empresa),
  empacotado como `.exe` (PyInstaller) com SQLite embutido e zero dependencias
  de TI (sem Docker, sem Postgres obrigatorio)
- **Watch de pasta e o fluxo principal de ingestao**: o admin aponta a pasta
  base na rede; qualquer PDF que cair la e ingerido automaticamente
  (dedupe por hash) → fila → scan → auditoria. Upload manual via client
  fica como opcao secundaria
- Client desktop em **Tauri (~10 MB)**, UI reescrita do zero; fala HTTP com o
  servico pela URL configurada no 1o uso; um exe unico para usuario comum + admin
- Original **nunca sai do servidor** — client apenas pede e recebe a versao
  censurada do seu nivel, com auditoria centralizada em um ponto so

### Arquitetura

```
[Servidor da empresa]                        [Desktops]
+--------------------------------+           +----------------------+
| SafeMask Service (.exe)        |<- HTTP -> | SafeMask Client.exe  |
|  FastAPI (atual) + PyInstaller |           |  Tauri, UI do zero   |
|  SQLite embutido               |           |  login -> pedir doc  |
|  Tesseract por + NER local     |           |  recebe versao tarj. |
|  Watch da pasta base (dedupe   |           |  admin: config/audit |
|  Original cifrado, nunca exposto|          +----------------------+
+--------------------------------+
        ^ pasta base na rede (admin aponta)
```

## 2. Papel da IA (modelo NER treinado no Colab)

- `safemask-ner` roda **exclusivamente no servico** e **apenas na ingestao**:
  doc novo chega (watch/upload) → scan uma vez → grava em `DadoSensivel`
  (coordenadas, tipo, `nivel_requerido`) → a IA dorme.
  Pedidos futuros sao matematica pura sobre as coordenadas ja fichadas
  (`gerar_pdf_parcial` nao toca no modelo; ha cache por `(doc_id, nivel)`)
- Empacotamento sem `checkpoint-*` (lixo de treino); import tardio de
  `transformers` vira **fallback regex-first** — se o modelo nao carregar,
  o servico escaneia com regex+validadores e o painel admin exibe aviso
- **NAO ESQUECER (pos-MVP): converter BERT -> ONNX quantizado**
  (~433 MB model.safetensors -> ~110 MB, dispensa torch) para o pack de
  instalacao ficar leve. Nao bloqueia o MVP.

## 3. Reaproveitar vs descartar

| | Itens |
|---|---|
| Reaproveita | `backend/app` (routes, models, autorizacao, fila, uploads), `scanner/` (regex+validadores+NER), testes pytest |
| Adapta | SQLite default (`DATABASE_URL` opcional p/ Postgres); seed de instalacao no boot; API pura (sem estaticos) |
| Descarta | `frontend/`, `index.html`, `render.yaml`, `vercel.json`, `scripts/warmup.sh`, multi-org (`tenancy.py`), upload multi-equipes + `duplicar_itens_sensiveis`, `POST /documentos/salvar-censurado` |

## FASE 0 — Virada documental e limpeza ← CONCLUIDA

- [x] Escrever este plano
- [x] Apagar `PLANO_SERVIDOR.md` e `PLANO_AVANCADO.md`
- [x] Remover cloud: `render.yaml`, `vercel.json`, `scripts/warmup.sh`,
      workflow `vercel-merge.yml`, README reescrito, comments `requirements*.txt`/`e2e.py`
      (URLs de front atual em `config.py` ficam para a Fase 2 trocar por CORS do Tauri)
- [x] Arquivar front web: `frontend/` e `index.html` (substituidos pelo client Tauri)
- [x] Cortar multi-org: `tenancy.criar/buscar_ou_criar` fora; 1 instalacao = 1
      organizacao (`carregar_organizacao_unica` no cadastro); backfill agora
      junta orfas na organizacao unica; testes de tenant apagados, persona
      "fora da equipe" mantida
- [x] Cortar upload multi-equipes + `duplicar_itens_sensiveis` +
      `aplicar_politica_da_equipe` (documento tem 1 dono; o scan ja aplica a
      politica da equipe dona, e o `ScannerFalso` agora reproduz isso)
- [x] Cortar `POST /documentos/salvar-censurado` + 2 testes ys dele
- [x] SQLite como default (`sqlite:///./safemask.db`; JSONB->JSON registrado
      no dialeto sqlite no proprio `database.py`; Postgres continua aceito)
- [x] pytest + ruff verdes pos-cortes (299 passed)
- [x] Commit da virada (branch `lucas` apenas)

## FASE 1 — Servico empacotavel (o coracao)

- [ ] **1.1 Watch de pasta**: `watchdog` monitorando pasta configuravel +
      fallback de polling por hash; ingestao -> mesma fila/auditoria
- [ ] **1.2 Seed de instalacao**: no 1o boot cria organization unica + usuario
      admin com senha inicial forcada a trocar
- [ ] **1.3 Config de instalacao**: `service.yaml` (pasta base, porta, equipe padrao)
- [ ] **1.4 PyInstaller**: spec embutindo Tesseract (`tessdata por`) + scanner +
      `safemask-ner` (sem checkpoints); servico Windows (NSSM ou pywin32)

## FASE 2 — Client Tauri (UI do zero)

- [ ] **2.1** Scaffold Tauri (Rust + webview, UI >= 10 MB)
- [ ] **2.2** UI nova: sidebar, login, lista de docs, pedir versao por nivel,
      download, status da fila
- [ ] **2.3** 1o uso: tela de config apontando URL do servico (ex. `http://srv-empresa:8000`)
- [ ] **2.4** Admin no mesmo exe: pasta base, equipes/niveis (`PoliticaNivel`),
      consultar/exportar auditoria
- [ ] **2.5** CORS do servico para origem `tauri://`

## FASE 3 — Fechamento de compliance

- [ ] **3.1** Cifra do original em disco (chave gerida no boot)
- [ ] **3.2** Metricas no painel admin (docs por nivel, acessos negados, top tipos)
- [ ] **3.3** Auditoria em 100% dos fluxos (download, negado, ingestao via watch)

## FASE 4 — Instalacao e demo

- [ ] **4.1** `docs/instalacao.md`: requisitos, rodar exe, apontar pasta, 1o acesso
- [ ] **4.2** Teste em VM Windows com pasta de rede real + 2 clients
- [ ] **4.3** Demo pro professor: servico rodando em servidor local + client instalado

## Pos-MVP (nao esquecer)

- [ ] Converter BERT -> ONNX quantizado (leveza do pack de instalacao)

## Riscos

- Tesseract no PyInstaller e a maior dor — plano B: instalador checa/instala
  Tesseract antes de subir
- Watch em share de rede perde eventos as vezes → polling por hash como backup
- UI nova sem testes automatizados no MVP — validacao manual em VM;
  backend continua com pytest + ruff

## Convencoes mantidas

- Testes com pytest (`backend/.venv`), ruff check em `backend/`
- Migrações idempotentes no boot — nao introduzir Alembic
- Commits em pt-BR sem acentos (padrao do historico)
- Rodar `.venv/bin/pytest` a partir de `backend/` (rootdir correto)
