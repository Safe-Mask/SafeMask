# Como testar o SafeMask em 5 minutos

Roteiro para professores, colegas e avaliadores (trazido do PI-III, CAMPUSCEUB/SafeMask#232). Usa Docker: nada precisa ser instalado além dele, e nenhum dado real é usado.

## 1. Subir (alguns minutos na primeira vez)

Com o [Docker Desktop](https://www.docker.com/products/docker-desktop/) aberto, na pasta do repositório:

```bash
docker compose up -d --build --wait
```

- Telas: <http://localhost:8080>
- API e documentação interativa: <http://localhost:8000/docs>

Portas ocupadas? Escolha outras, por exemplo `SAFEMASK_PORTA_WEB=8090 SAFEMASK_PORTA_API=8030 docker compose up -d --build --wait` (no PowerShell, defina as variáveis com `$env:` antes).

## 2. Criar os dados de demonstração (30 segundos)

```bash
docker compose run --rm api python -m app.tarefas.popular_demo
```

Use `run` (e não `exec`): ele passa pelo script de início do container. O comando cria a **Organização Demonstração**, a **Equipe Demonstração**, três contas fictícias e dois documentos já processados, e mostra a senha **só no terminal**:

| Conta | Cargo |
| --- | --- |
| `lider.demo@safemask.example.com` | líder (vê o original) |
| `supervisor.demo@safemask.example.com` | supervisor (parcial até o nível 2, auditoria) |
| `membro.demo@safemask.example.com` | membro (parcial até o nível 1) |

Rodar de novo não duplica nada. Esqueceu a senha? `--nova-senha` gera outra.

## 3. O que olhar (2 minutos)

1. **Entre como líder.** O dashboard mostra o painel de conformidade: dados protegidos por tipo, tarjas por mês e acessos negados.
2. **Documentos Censurados:** abra "Ficha cadastral (demo)". CPF, RG, CNH, CEP, cartão e telefone estão cobertos; o protocolo, não. Baixe o **comprovante de anonimização**.
3. **Novo Upload:** envie qualquer PDF com texto. Antes de salvar, a tela mostra os dados encontrados, mascarados: desmarque um, acrescente um trecho (um nome) e envie.
4. **Entre como membro** e abra "Ficha cadastral (demo)" (Proteção média): a descensura parcial é recusada, porque o nível do documento exige supervisor. No "Contrato" (Básico), o membro recebe a parcial.
5. **Entre como supervisor** e abra **Auditoria**: as recusas do membro estão lá, com cargo, ação e resultado.

## 4. Desligar

```bash
docker compose down        # mantém banco, arquivos e a SECRET_KEY (volumes)
docker compose down -v     # apaga tudo
```

## Como funciona

- `db`: PostgreSQL 15, com os dados no volume `banco`.
- `api`: imagem de `backend/Dockerfile`, com Tesseract em português (PDF escaneado) e sem o NER. Arquivos no volume `dados` (`SAFEMASK_PASTA_UPLOADS=/dados/uploads`).
- A `SECRET_KEY` é gerada na primeira vez e guardada no volume `segredos`, separado dos arquivos. Nenhuma chave vem do repositório; em produção, informe `SECRET_KEY` pelo ambiente.
- `web`: nginx servindo as telas; o `config.js` aponta para a API da porta escolhida.
- O CI monta a imagem, sobe os três serviços, cria os dados de demonstração, faz login e confere que tudo continua lá depois de reiniciar a API (job `docker compose` em `.github/workflows/ci-backend.yml`).
