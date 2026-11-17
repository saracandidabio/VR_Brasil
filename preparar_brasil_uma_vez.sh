#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
python preparar_municipios_brasil.py --todos
python validar_base.py
python validar_publicacao.py
python validar_municipios_brasil.py --exigir-completo
printf '\nDADOS MUNICIPAIS COMPLETOS: publique o conteúdo de data/ e os arquivos do projeto no GitHub.\n'
