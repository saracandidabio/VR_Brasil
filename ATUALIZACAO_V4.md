# Como atualizar para a versão 4

A pasta contém todo o projeto, incluindo os oito cubos nacionais de SRAG, as tabelas regionais 2023–2026 e os arquivos GeoJSON das 27 UFs e de MT/MS. **Não é necessário reconstruir nem baixar os CSVs oficiais**.

## Correções

1. **Mapa municipal:** o código IBGE agora é preservado como texto ao ler o CSV; as contagens de cada município passam a corresponder ao GeoJSON. O padrão é um mapa estático para evitar falhas de MapLibre no Safari; o mapa interativo permanece opcional.
2. **INFA e INFB:** disponíveis em todos os módulos, com séries separadas na aba temporal e mapas de INFA/INFB em MT/MS. A informação separada cobre 2023–2026 para Brasil, Centro-Oeste, MT e MS, não os outros estados individualmente e nem 2019–2022.
3. **Layout:** títulos acima do Plotly; legenda dentro de área de margem dedicada, reduzindo sobreposições.
4. **PNG 800 dpi reais:** botão de exportação por gráfico. Arquivo estático, criado em Matplotlib e com metadados de DPI. Para cada gráfico, abra o painel “Exportar figura” e pressione “Preparar” e depois “Baixar”.

## Como subir ao GitHub

Abra https://github.com/saracandidabio/VR_Brasil/upload/main e envie **todo o conteúdo de dentro da pasta `VR_Brasil_Mapas_Series_V4`**, mantendo `streamlit_app.py` na raiz. Inclua a pasta oculta `.streamlit/`, a pasta `data/`, `mapas_geo.py`, `figuras_ui.py`, `exportacao.py`, `influenza_contexto.py` e `paginas_centro_oeste.py`.

No Mac, use `Command + Shift + .` no Finder para mostrar arquivos ocultos. O envio substitui arquivos de mesmo nome; arquivos antigos não presentes nesta distribuição podem ser excluídos pelo editor web do GitHub.

Para testar localmente:

```bash
python3 -m pip install -r requirements.txt
python3 validar_publicacao.py
python3 -m pytest -q
streamlit run streamlit_app.py
```

O dashboard público permanece em https://vrbrasil.streamlit.app/.
