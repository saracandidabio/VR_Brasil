# Enviar a V7 para o GitHub

Repositório: https://github.com/saracandidabio/VR_Brasil  
Dashboard: https://vrbrasil.streamlit.app/

## Pelo navegador

1. Entre na sua conta GitHub.
2. Abra https://github.com/saracandidabio/VR_Brasil/upload/main
3. Descompacte o ZIP e selecione os arquivos e subpastas de **dentro** de `VR_Brasil_Influenza_Mapas_V7`.
4. Envie, substitua os caminhos antigos equivalentes e registre o commit. Preserve as pastas `data/` e `.streamlit/` na raiz.
5. Não envie `.venv`, `downloads_srag/`, `__pycache__`, nem CSVs originais do SIVEP com registros individuais.

## Pelo Terminal, se seu Git já estiver autenticado

```bash
cd ~/Downloads/VR_Brasil_publicacao
# Copie os arquivos da nova pasta descompactada para este repositório,
# preservando a pasta .git local e todos os CSV/GeoJSON agregados do pacote.
python3 validar_publicacao.py
git status
git add -A
git commit -m "Ajusta aba influenza e contraste dos mapas municipais"
git push origin main
```

O commit local não equivale ao envio: `git push` precisa completar sem erro de autenticação.
