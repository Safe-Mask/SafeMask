# Decisão: pasta dos arquivos configurável

**Data:** 28/10/2026 · **Status:** aprovada · **Origem:** PI-III (CAMPUSCEUB/SafeMask#24, ADR 0005 de lá)

## Contexto

O SafeMask guarda dois arquivos por documento: o original (`originais/`) e a versão com tarja (`censurados/`), além das versões parciais em cache. O banco guarda só os metadados e o caminho.

Até aqui havia dois problemas:

1. **A pasta dependia do diretório de execução.** `uploads/` era relativo à pasta de onde a API era iniciada, e a rota do arquivo censurado montava o caminho com `Path.cwd()`. Com a API iniciada fora de `backend/`, ela criava uma pasta vazia no lugar errado e os documentos respondiam "Arquivo físico não encontrado".
2. **A pasta ficava junto do código.** Com a virada para o servidor próprio (`PLANO_SERVIDOR.md`), uma nova versão do código não pode levar os documentos junto.

## Decisão

- A pasta vem da variável `SAFEMASK_PASTA_UPLOADS` (`backend/app/core/armazenamento.py`).
- Sem a variável, a pasta é `backend/uploads`, resolvida a partir do código. Para quem já rodava de dentro de `backend/`, é a mesma pasta de antes, e nada precisa ser movido.
- Um caminho relativo na variável parte de `backend/`.
- O arquivo tarjado é **localizado pelo nome** dentro da pasta configurada. Os registros antigos, com `uploads/censurados/...` ou com caminho absoluto, continuam valendo.
- No servidor, a variável aponta para o disco de dados, fora da pasta do código.

## Alternativas consideradas

| Alternativa | Por que não agora |
| --- | --- |
| Armazenamento de objetos (S3, R2, MinIO) | Exige SDK, credenciais e tratamento de rede em toda leitura e gravação; o produto roda numa única instância |
| PDFs dentro do banco | O banco cresce rápido, e as cópias de segurança ficam pesadas |

## Consequências

- A API pode ser iniciada de qualquer diretório.
- A cópia de segurança dos documentos é a cópia dessa pasta.
- No Windows sem caminhos longos, a pasta precisa ser curta (o nome do arquivo tarjado já ocupa cerca de 76 caracteres do limite de 260).
