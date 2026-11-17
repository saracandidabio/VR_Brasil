## Classificação final sem resultado laboratorial — atualização V6

As novas métricas `classe_influenza_sem_resultado_laboratorial`, `classe_covid_sem_resultado_laboratorial` e `classe_outro_virus_sem_resultado_laboratorial` são calculadas nos microdados, por notificação. Uma ficha entra na métrica apenas quando a classificação final correspondente existe, não há PCR/antígeno com resultado registrado (positivo/negativo/inconclusivo) nos campos `PCR_RESUL`/`RES_AN`, e não há nenhum marcador viral positivo nos grupos do painel. Isso não equivale a 'exame não realizado'; valores ausentes e pendências podem coexistir. Essas notificações são exibidas **separadamente**, não adicionadas ao total de detecções virais. `CLASSI_FIN=1` identifica influenza sem especificar A/B.

**Os dados agregados antigos não têm esse cruzamento.** Para preencher as novas colunas, é necessário reexecutar o processamento dos CSVs oficiais com `python construir_base.py --todos --reprocessar` e `python preparar_centro_oeste.py --todos --reprocessar` (ver as instruções do projeto). Caso os arquivos de origem históricos estejam disponíveis localmente, prefira `--arquivo-local ... --ano-local ...` para cada ano. Não publique downloads brutos. O aplicativo exibirá uma mensagem de indisponibilidade enquanto os cubos não forem reconstruídos.

## Atualização V5

- reforço visual dos mapas municipais com contorno estadual mais evidente;
- zoom automático por UF na distribuição geográfica geral, preservando as delimitações estaduais;
- nova aba **Co-detecções**;
- ajustes de títulos/legendas para reduzir sobreposição;
- manutenção da exportação de figuras em **800 dpi**.

# Observatório de Vírus Respiratórios — SRAG Brasil

### 🌐 [Acessar o dashboard online — vrbrasil.streamlit.app](https://vrbrasil.streamlit.app/)

[**Atualização V4: correções e instalação**](ATUALIZACAO_V4.md)

[**Código-fonte no GitHub**](https://github.com/saracandidabio/VR_Brasil) · [**Como substituir os arquivos do repositório de uma vez**](PUBLICAR_GITHUB.md)

**Versão 4 — mapas municipais e figuras científicas:** inclui os oito cubos anuais nacionais (2019–2026), os complementos de influenza de 2023–2026 e as malhas de UFs e municípios de MT/MS. É possível publicar sem baixar novamente os CSVs originais.

Dashboard em **Streamlit**, com fonte exclusiva SIVEP-Gripe/SRAG (Ministério da Saúde), apresentado em visual de pesquisa. Idealização: **Sara Cândida Ferreira dos Santos**. Os dados são públicos, previamente tratados e versionados para que o app não execute downloads durante a consulta.

## Abrangência

- **Brasil, 2019–2026**: 7 páginas originais do projeto, com indicadores de SRAG, detecções laboratoriais, evolução, perfil epidemiológico, mapa por UF, exploração de agregados e auditoria.
- **Centro-Oeste · MT e MS**, nova página: comparação de influenza A/B entre 2023 e 2026; subtipos A(H1N1)pdm09 e A(H3N2), linhagens B/Victoria e B/Yamagata; março de cada ano e abril de 2025 versus março de 2026; mapas municipais de Mato Grosso e Mato Grosso do Sul.
- **Mapa geográfico adaptável**: Brasil por UF; ao escolher somente MT, MS ou ambos no filtro de UF, a aba geográfica muda para a malha municipal correspondente (IBGE) e amplia a área exibida.

## Requisitos

Python 3.10+ (preferencialmente 3.11 ou 3.12), Streamlit, Pandas, NumPy, Plotly, Matplotlib, Pillow e Requests. Os únicos arquivos de dados necessários no servidor são tabelas agregadas (`.csv.gz`) e as malhas (`.geojson`).

## Instalação e construção no Mac

Consulte [LEIA_PRIMEIRO.md](LEIA_PRIMEIRO.md). Como este pacote **já contém os dados preparados**, basta executar:

```bash
python3 -m pip install -r requirements.txt
python3 validar_publicacao.py
streamlit run streamlit_app.py
```

Para reconstruir o complemento em uma **atualização futura** (e apenas quando necessário), utilize `bash preparar_centro_oeste.sh`. O aplicativo publicado não executa essa rotina.

O processamento nacional **não precisa ser refeito**. A preparação complementar, necessária somente em atualizações futuras, lê os CSVs 2023–2026, produzindo dois conjuntos por ano:

1. `temporal_influenza_ANO.csv.gz`: semana, mês de início dos sintomas, estratos de sexo e faixa etária, e quatro escopos: Brasil, Centro-Oeste, MT e MS;
2. `municipios_co_ANO.csv.gz`: município de residência, UF e ano, para MT/MS/GO/DF, em granularidade agregada (sem sexo, idade ou semana).

### Influenza A (INFA) e Influenza B (INFB) em todas as páginas

A versão 4 inclui, em todas as páginas, um painel de tipagem A/B (ou comparações equivalentes): visão geral, agentes virais, séries temporais, distribuição geográfica, Centro-Oeste, perfil epidemiológico, explorador e metodologia. Na aba **Séries temporais**, INFA e INFB também podem ser selecionadas junto com VSR, SARS-CoV-2 e demais vírus.

**Limite da informação:** a separação INFA/INFB vem de `temporal_influenza_ANO.csv.gz` e `municipios_co_ANO.csv.gz`, disponíveis em **2023–2026**. Há escopos Brasil, Centro-Oeste, MT e MS; não há tipagem estadual individual para outras UFs nesta distribuição e os cubos 2019–2022 não possuem A/B desagregado. Os valores não disponíveis aparecem como indisponíveis, **não como zeros**. O mapa municipal permite selecionar INFA ou INFB para MT/MS. O mapa nacional por UF continua exibindo as categorias com cobertura nacional comprovada, sem inventar tipagem estadual.

### Correção dos mapas e exportação científica

Os municípios de MT/MS são cruzados pelo código IBGE de seis dígitos **como texto** (o CSV antes convertia para inteiros). O mapa municipal abre por padrão em uma **versão estática compatível com Safari**, com preenchimento por município e zoom do estado. Também há opção interativa. O mapa nacional por UF continua interativo.

Todos os gráficos têm o painel **Exportar figura · PNG 800 dpi**. Clique primeiro em **Preparar PNG em 800 dpi** e depois em **Baixar PNG · 800 dpi**. A imagem é reconstruída a partir dos dados com Matplotlib, não capturada da tela, e o PNG grava aproximadamente 800 dpi nos metadados físicos. A exportação é uma figura científica estática e não contém os controles interativos do navegador. Não exige Chrome nem Kaleido no Streamlit Cloud.

As séries nacionais `cubo_srag_ANO.csv.gz` não são modificadas. As malhas de MT e MS do IBGE **já estão incluídas** em `data/`. Quando a malha não está presente, o app explica o que falta em vez de apresentar pontos como se fossem localizações de pacientes. Na página geográfica, selecionar exclusivamente MT e/ou MS amplia o mapa para municípios (2023–2026).

## Dados, interpretação e limites

- **Fonte**: SIVEP-Gripe, sistema oficial para registros de SRAG. A vigilância abrange casos hospitalizados e óbitos por SRAG. Não cobre todas as infecções respiratórias na população.
- **A/B**: usa `POS_PCRFLU` + `TP_FLU_PCR`, ou `POS_AN_FLU` + `TP_FLU_AN`. A positividade sem tipo determinado permanece separada.
- **Subtipo e linhagem**: `PCR_FLUASU` e `PCR_FLUBLI`, restritos a registros de PCR positivo e tipagem coerente. H1N1pdm09 (1), H3N2 (2); Victoria (1), Yamagata (2). Outros valores não são convertidos automaticamente em resultados específicos.
- **Ano**: ano de referência do arquivo SIVEP; mês: `DT_SIN_PRI` válido para o mesmo ano; semana: `SEM_PRI`.
- **Localização**: `SG_UF` e `CO_MUN_RES`, ou seja, residência. O IBGE fornece geometrias e nomes das localidades; o código SIVEP de município (6 dígitos) corresponde ao prefixo de 6 dígitos do geocódigo IBGE (7 dígitos).
- **Proporções**: números absolutos de notificações SRAG e, quando exibidos, detecções por 100 notificações SRAG; não são prevalência, incidência nem positividade entre pessoas testadas.
- **Duplicidades**: um único arquivo anual por ano de análise, sem somar as quatro escalas territoriais. Não garante deduplicação individual dentro do SIVEP-Gripe.
- **Privacidade**: tabelas municipais anuais sem combinações por idade, sexo e semana; mesmo tabelas agregadas exigem cautela na publicação.

**Limitação de detalhamento das categorias gerais:** os cubos nacionais presentes nesta distribuição não possuem campos `class2_*`. O gráfico oficial de `CLASSI_FIN=2` permanece genérico; classificá-lo de forma exclusiva por vírus exige reprocessar as fontes individuais, sem inferir a partir de totais agregados.

### Contextualização — NAVIO

Os resultados de expedições citados na nova página são apresentados **à parte** dos dados do SIVEP-Gripe: 14 positivos para influenza A (3 em abril/2025 e 11 em março/2026, estes últimos H3N2), e 12 para influenza B em março/2026 (linhagem Victoria). Esses números vieram do documento de pesquisa fornecido pelo usuário, e não são adicionados aos totais oficiais do painel.

### Reproduzibilidade e atualização

`data/centro_oeste_manifest.json` guarda metadados, fonte, data da preparação e hashes SHA256 dos arquivos processados. Valide todos os arquivos distribuídos com `python3 validar_publicacao.py` antes do envio. `data/manifest.json` mantém o manifesto nacional já existente. O site é um snapshot: **atualização não automática**, exigindo novo processamento local e novo commit quando desejado.

Referências:

- Ministério da Saúde, SRAG 2019–2026: https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026
- Dicionário SIVEP-Gripe com `TP_FLU_PCR`, `PCR_FLUASU` e `PCR_FLUBLI`: https://goias.gov.br/saude/wp-content/uploads/sites/34/2013/08/dicionariodedados-2d1.pdf
- IBGE, malhas: https://servicodados.ibge.gov.br/api/v3/malhas

## Desenvolvimento

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q tests/test_centro_oeste.py tests/test_pipeline.py
streamlit run streamlit_app.py
```

Para reconstruir apenas o complemento de um ano, use `python preparar_centro_oeste.py --anos 2026 --reprocessar`. Para usar um CSV oficial já baixado, use `--arquivo-local CAMINHO --ano-local 2026`. Para baixar só as malhas, use `--apenas-malhas`.


## Atualização de novembro de 2026 — mapas e séries por agente

O dashboard usa `mapas_geo.py` e `plotly.express.choropleth_map` para representar
polígonos das 27 UFs e dos municípios de MT e MS. A câmera é calculada a partir
dos polígonos selecionados, sem depender do enquadramento `fitbounds` do navegador.
A seleção de MT e/ou MS na barra lateral ativa o mapa municipal (2023–2026).
Para outras UFs o mapa dá zoom automático na região selecionada. As malhas
continuam embarcadas na pasta `data/`. O mapa base cartográfico pode buscar
pequenos mosaicos da Carto, mas **não consulta novas notificações**.

A página **Séries temporais → Série temporal por agente** permite comparar
marcadores de influenza, SARS-CoV-2, VSR, rinovírus, adenovírus e outros alvos
entre 2019 e 2026. Na página **Centro-Oeste · MT e MS** também há comparação
semanal de vírus respiratórios, incluindo Influenza A e B, no período 2023–2026.
Os gráficos permitem exportação CSV. Um registro pode ter múltiplos marcadores.

**Como publicar**: mantenha o conteúdo integral deste projeto na raiz do seu
repositório `VR_Brasil`. Envie também `mapas_geo.py`, `data/` e
`tests/test_mapas.py`. **Não** refaça downloads nem substitua o `manifest.json`
por versões mais antigas; esta distribuição já inclui as tabelas preparadas.

A integração com o navegador (renderização visual efetiva) deve ser conferida
no Streamlit após o deploy. Os testes locais verificam a presença das malhas,
seus códigos de ligação e a criação de figuras Plotly compatíveis.
