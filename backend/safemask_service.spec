# -*- mode: python ; coding: utf-8 -*-
# Spec do PyInstaller para o servico central (Fase 1 de `PLANO_DESKTOP.md`).
#
# Build (no servidor ou maquina de liberacao, com o venv do backend ativo):
#   cd backend && .venv/bin/pyinstaller safemask_service.spec
#
# O pacote sai em `dist/safemask_service/`. Ao lado do exe va o
# `service.yaml` (pasta base, porta, equipe padrao) e, no Windows, o
# Tesseract-OCR + idioma `por` (docs/instalacao.md).
#
# Nao embutimos os `checkpoint-*` do treino: sao apenas para retomar
# treinamento e dobrariam o tamanho do pacote (model.safetensors ~433 MB
# ja e 90% do peso do exe).

import os
from pathlib import Path

prefixo_modelo = Path("scanner") / "safemask-ner"

# O modelo NER (proximo ao modulo `scanner` no bundle, como em dev).
arquivos_modelo = [
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
]
datas = [
    (str(prefixo_modelo / nome), "scanner/safemask-ner")
    for nome in arquivos_modelo
    if (prefixo_modelo / nome).is_file()
]
if "model.safetensors" not in [os.path.basename(c[0]) for c in datas]:
    # Base de codigo sem o modelo: pacote segue regex-first (graceful).
    print("AVISO: safemask-ner sem model.safetensors; pacote sai sem NER.")

a = Analysis(
    ["run_service.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "scanner.scanner",
        "app.core.ingestao_pasta",
        "app.core.seed_instalacao",
        "app.core.service_config",
        "app.core.troca_senha",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Ferramentas de dev que nao rodam no servico (e incham o exe).
        "pytest",
        "matplotlib",
        # Checkpoints de treino ficam de fora (ver cabecalho).
        "transformers.integrations",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="safemask_service",
    console=True,  # log visivel no console da instalacao
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="safemask_service",
)
