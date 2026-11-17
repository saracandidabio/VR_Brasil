## Atualização V5

- reforço visual dos mapas municipais com contorno estadual mais evidente;
- zoom automático por UF na distribuição geográfica geral, preservando as delimitações estaduais;
- nova aba **Co-detecções**;
- ajustes de títulos/legendas para reduzir sobreposição;
- manutenção da exportação de figuras em **800 dpi**.

# Atualização V3 — mapas e séries de agentes

## Publicar sem perder os dados

1. Descompacte `VR_Brasil_Mapas_Series_V3_Completo.zip`.
2. Abra o repositório `VR_Brasil` no GitHub.
3. Envie o conteúdo da pasta `VR_Brasil_Mapas_Series_V3` **na raiz** do repositório,
   substituindo arquivos existentes.
4. Garanta a presença de `mapas_geo.py` (arquivo novo), `streamlit_app.py`,
   `paginas_centro_oeste.py`, `requirements.txt`, `data/` e `.streamlit/config.toml`.
5. Faça commit. O aplicativo Streamlit usa `streamlit_app.py` como arquivo principal.

O ZIP já contém todos os arquivos agregados: SIVEP-Gripe 2019–2026 e
complementos regionais 2023–2026, além dos polígonos estaduais/municipais.
Não execute os construtores para aplicar apenas estas correções de visualização.

## O que mudou

- Malhas representadas com a camada `choropleth_map` do Plotly (MapLibre).
- Câmera e zoom calculados pelo contorno geográfico selecionado, em vez de `fitbounds`.
- Comparação temporal por múltiplos alvos com CSV na aba nacional.
- Comparação semanal multialvo na aba Centro-Oeste, além de influenza A/B.
- Ajustes nas margens e nos rótulos numéricos dos gráficos.

## Verificações

```bash
python validar_publicacao.py
python -m pytest tests/ -q
streamlit run streamlit_app.py
```

Depois abra **https://vrbrasil.streamlit.app/**.

**Limitações:** os mapas municipais cobrem 2023–2026 e não usam filtros de
sexo/idade/semana. Dados históricos nacionais são agregados por ano e semana;
subtipos A/B só podem ser analisados com o complemento 2023–2026.
