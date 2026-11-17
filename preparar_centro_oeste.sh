#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" preparar_centro_oeste.py --todos --malhas
"$PYTHON" -m pytest -q tests/test_centro_oeste.py tests/test_pipeline.py
printf '\nComplemento pronto. Confira os CSVs e GeoJSON em data/ e publique os arquivos agregados no GitHub.\n'
