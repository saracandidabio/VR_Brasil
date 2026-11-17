# Como publicar a V8 no GitHub

1. **Antes de publicar como versão municipal completa**, execute no Mac: `bash preparar_brasil_uma_vez.sh`.
2. Verifique a mensagem de validação: `8/8 anos sincronizados; 27/27 UFs com polígonos`.
3. Abra https://github.com/saracandidabio/VR_Brasil/upload/main.
4. Envie o **conteúdo interno** desta pasta, incluindo `data/`, `.streamlit/` e todos os arquivos `.py`. Não envie um ZIP nem crie uma subpasta extra.
5. Confira que `streamlit_app.py`, `requirements.txt` e `README.md` estão na raiz.
6. Faça **Commit changes** e verifique https://vrbrasil.streamlit.app/.

Não envie `.venv/`, CSVs brutos `INFLUD*.csv` nem `downloads_srag/`. Se algum upload via navegador exceder os limites do GitHub, envie em lotes ou use GitHub Desktop/Git.

**Antes da preparação:** a V8 ainda funciona com os dados anteriores e mostra aviso para UFs/anos sem municípios. Não significa que os municípios de todas as UFs estejam completos.
