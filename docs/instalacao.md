# Instalacao do servico SafeMask (desktop/on-premise)

Produto: 1 instalacao = 1 empresa. O servidor da empresa roda o servico
central (`safemask_service.exe`); o cliente Tauri (Usuarios) conversa com
ele na rede interna. Nada sai da maquina da empresa: banco e arquivos
moram no servidor, o original nunca sai do servidor, e o cliente recebe so
os PDFs tarjados correspondentes ao nivel da equipe dele.

## 1. O que instalar no servidor

1. `safemask_service/` (saida do PyInstaller, `backend/safemask_service.spec`)
   em uma pasta dedicada, por exemplo `C:\SafeMask\`.
2. Tesseract-OCR 5.x com o idioma `por`
   (https://github.com/UB-Mannheim/tesseract/releases).
   Instale no caminho padrao (`C:\Program Files\Tesseract-OCR`) — o servico
   procura nesse caminho; sem ele, PDFs sem camada de texto falham.
3. (Opcional) NSSM para rodar o exe como servico do Windows:
   `nssm install SafeMask "C:\SafeMask\safemask_service\safemask_service.exe"`.

O pacote ja inclui SQLite e o modelo NER (`safemask-ner`). Nao ha
dependencia de Docker ou de banco Postgres.

## 2. service.yaml

Crie `service.yaml` ao lado do exe:

```yaml
# Pasta de rede onde caem os documentos da empresa (o scanner digitaliza aqui).
pasta_base: "C:/SafeMask/inbox"
# Porta da API na rede interna.
porta: 8000
# Equipe que recebe a ingestao automatica da pasta base.
equipe_padrao: "Documentos da empresa"
# Intervalo entre varreduras completas da pasta (segundos).
intervalo_watch: 10
```

Sem esse arquivo o servico sobe com os padroes (pasta base desligada,
porta 8000). Valores invalidos sao ignorados com aviso no log — o boot
nunca quebra por causa do yaml. Em cada campo vale tambem a variavel de
ambiente correspondente (`SERVICE_PASTA_BASE`, `SERVICE_PORTA`,
`SERVICE_INTERVALO_WATCH`, `SERVICE_EQUIPE_PADRAO`), que sobrepoe o yaml.

## 3. Primeiro acesso (admin)

No primeiro boot, com o banco ainda sem usuarios, o servico cria:

- A organizacao unica (1 instalacao = 1 empresa);
- O admin provisorio `admin@safemask.example.com` com senha temporaria
  aleatoria de 16+ caracteres, impressa somente no log do primeiro boot;
- A equipe `Documentos da empresa` (nome de `service.yaml`) com o admin
  como lider, que recebe a ingestao da pasta base E recebe os docs
  subidos manualmente pelo client.

Enquanto a senha provisoria nao for trocada, TODA chamada fora de
`/auth/*` responde `403 {"detail": "Troque a senha..."}`. O client mostra
a tela de troca de senha no primeiro uso. O aviso so aparece na instalacao nova (seed idempotente).

## 4. Pasta base

- Cada PDF que cair nela (qualquer subpasta) e ingerido automaticamente:
  validado (magic bytes + tamanho), copiado para o storage do servico e
  enviado para o mesmo fluxo de scan dos uploads manuais.
- Nada e reingerido por engano: dedupe por hash do conteudo (inclusive
  documentos ja arquivados).
- Nao-PDF e PDF vazio/corrompido sao ignorados com aviso no log uma vez
  por nome de arquivo.
- A empresa mantem o controle da pasta: subir documento NAO toca o
  arquivo la — apagar/mover e decisao do admin.

## 5. Verificando a instalacao

`http://<ip-do-servidor>:8000/docs` deve abrir. Com o admin logado no
client, o `overview` da equipe mostra os arquivos ingeridos; o log do
servico lista `Ingerido da pasta: <arquivo> -> doc_id=N` por documento.

## 6. Client Tauri (usuarios)

Source em `client/` (Vite + TypeScript + Tauri 2). Para gerar o exe do
client numa maquina com Rust + WebKitGTK (Linux) ou MSVC/WebView2 (Windows):

```
cd client
npm install
npm run tauri build     #saida: client/src-tauri/target/release/bundle/
```

No primeiro uso o client pede a URL do servico (ex. `http://srv-empresa:8000`),
valida contra `/auth/me` e so entao pede login. O admin provisorio logo com
`admin@safemask.example.com` + senha do log e e obrigado a trocar a senha no
mesmo exe.

## 7. Base de dados

SQLite em `backend/safemask.db` (padrao do produto). Se a empresa quiser
instituir Postgres mais tarde, o mesmo servico aceita a variavel
`DATABASE_URL` (Postgres) sem mudanca de codigo.
