#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
python construir_base.py --todos
python validar_base.py
echo
echo "Pronto: coloque esta pasta (incluindo data/) em seu repositório GitHub."
echo "O Streamlit lerá apenas os arquivos presentes em data/."
