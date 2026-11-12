#!/bin/sh
# Inicio do container da API (PI-III #232).
#
# Sem SECRET_KEY no ambiente, gera uma na primeira vez e guarda no volume
# /segredos, separado dos dados. Nenhuma chave vem do repositorio. Em
# producao, informe SECRET_KEY pelo ambiente.
set -e

mkdir -p /segredos /dados

if [ -z "$SECRET_KEY" ]; then
    if [ ! -s /segredos/secret_key ]; then
        python -c "import secrets; print(secrets.token_urlsafe(48))" > /segredos/secret_key
        echo "SECRET_KEY gerada em /segredos (volume segredos)."
    fi
    SECRET_KEY="$(cat /segredos/secret_key)"
    export SECRET_KEY
fi

exec "$@"
