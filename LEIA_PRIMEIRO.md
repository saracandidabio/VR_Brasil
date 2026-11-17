# Observatório SRAG Brasil — atualização V3

**Acesse:** https://vrbrasil.streamlit.app/

Este ZIP é a versão consolidada para o repositório `VR_Brasil`.
Contém toda a base agregada já preparada (2019–2026), complementar Centro-Oeste (2023–2026),
malhas GeoJSON e código corrigido para mapas responsivos.

**Não é necessário baixar os CSVs oficiais nem reexecutar o pipeline.**

Leia `COMO_ATUALIZAR.md` para publicar. Não copie a pasta `.venv`.
O novo arquivo `mapas_geo.py` é obrigatório para os mapas aparecerem.

Em relação à versão anterior:
- mapas das 27 UFs e dos municípios de MT/MS renderizados pela camada MapLibre;
- zoom baseado nos polígonos das UFs selecionadas;
- séries temporais comparativas por vírus, em escala nacional e Centro-Oeste;
- rótulos da série cronológica e dos principais gráficos revisados.

Para testar localmente: `python validar_publicacao.py` e
`python -m pytest tests/ -q`. No Streamlit, o arquivo principal é `streamlit_app.py`.
