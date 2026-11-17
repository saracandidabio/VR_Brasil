# Publicação da versão 7

**Projeto completo:** inclui 2019–2026 nacional, complemento 2023–2026 de MT/MS/CO e malhas do IBGE.

1. Descompacte `VR_Brasil_Influenza_Mapas_V7_Completo.zip`.
2. Entre na pasta `VR_Brasil_Influenza_Mapas_V7`.
3. Para testar: `python3 -m pip install -r requirements.txt`, `python3 validar_publicacao.py` e `streamlit run streamlit_app.py`.
4. Para publicar pelo navegador, acesse [VR_Brasil no GitHub](https://github.com/saracandidabio/VR_Brasil/upload/main). Envie os arquivos **de dentro** da pasta, inclusive as pastas `data/` e `.streamlit/` (pasta oculta). Não envie o ZIP como arquivo único. Verifique a raiz e confirme o commit.
5. Acesse https://vrbrasil.streamlit.app/ e confira a nova aba **Influenza A e B**, as séries temporais e o mapa municipal de MT/MS com a escala de **Quantis**.

A opção de upload do site substitui arquivos com o mesmo nome/caminho, mas **não remove automaticamente arquivos antigos** que não estão no pacote. Use o editor web ou Git para excluir resíduos específicos. O arquivo `streamlit_app.py` atualizado remove a aba de co-detecções da navegação, sem necessidade de apagar os cubos históricos.

**Não recalcule os dados apenas para corrigir o `KeyError` ou o contraste dos mapas.** O novo cálculo de classificação final sem resultado laboratorial ainda depende dos CSVs oficiais completos. Nenhuma contagem desse grupo foi inventada.

Se a aplicação na nuvem apresentar uma exceção, confira os logs do Streamlit e o arquivo `requirements.txt` publicado.
