# Observatório de Vírus Respiratórios — SRAG Brasil

**Acesse o dashboard:** https://vrbrasil.streamlit.app/

**Idealização:** Sara Cândida Ferreira dos Santos.

## Sobre a base

O SIVEP-Gripe, sistema oficial do Ministério da Saúde, recebe registros de vigilância de **Síndrome Respiratória Aguda Grave (SRAG)** hospitalizada e óbitos por SRAG. Este projeto trabalha somente com notificações oficiais agregadas, permitindo comparar vírus respiratórios, distribuição temporal, perfil epidemiológico e distribuição espacial.

**Fonte:** https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026

## Escopos e disponibilidade

- Brasil, todas as UFs: **2019–2026**, em agregados já incluídos na pasta `data/`.
- Influenza A/B e destaque Centro-Oeste, MT e MS: complemento **2023–2026** já incluído.
- Municípios de MT e MS: já possuem malha e complemento anual de 2023–2026.
- Municípios das **27 UFs e de todos os anos 2019–2026**: passam a estar disponíveis depois de executar uma vez `bash preparar_brasil_uma_vez.sh` no seu Mac. Os microdados históricos necessários não acompanham este ZIP.

## Novidades da V8

- Ao filtrar UF na **Distribuição geográfica**, mapa interativo por município de residência (`CO_MUN_RES`); sem UF, mapa por estado.
- Nome da cidade e contagem exata ao passar o mouse, limites estaduais mais fortes, zoom automático e ranking municipal.
- Todos os mapas **interativos** com **escala de cores linear em valores absolutos**, zero como limite inferior.
- Manutenção da aba Influenza A e B, subtipos, linhagens e análises regionais; sem aba de co-detecções na navegação.
- Exportação científica de mapas em **PNG 800 dpi**.

## Preparar completamente no Mac (uma única vez)

```bash
bash preparar_brasil_uma_vez.sh
```

O construtor preserva um único arquivo oficial por ano, gera as tabelas nacionais, municipais e de influenza da **mesma versão** e valida a igualdade de totais. A fonte bruta não é enviada ao GitHub. Após concluir, publique **todos os arquivos da pasta**, inclusive `data/` e `.streamlit/`, na raiz do repositório `VR_Brasil`.

Para iniciar localmente (após instalar as dependências de `requirements.txt`):

```bash
streamlit run streamlit_app.py
```

A versão publicada é um **snapshot**. Ela lê dados e malhas locais, sem baixar os CSVs do SIVEP-Gripe durante a navegação. O fundo cartográfico interativo pode usar mosaicos de mapas externos.

## Limitações epidemiológicas

- Notificações não representam necessariamente indivíduos únicos; o projeto não elimina automaticamente todas as duplicidades internas do SIVEP-Gripe.
- Um marcador laboratorial positivo não equivale a uma classificação final; classificação epidemiológica e resultado de exame são apresentados separadamente.
- Uma notificação pode ter mais de um vírus positivo; as contagens de agentes não são mutuamente exclusivas.
- Municípios são de **residência**, não de coleta ou atendimento. Dados municipais são agregados apenas por município e ano, sem filtros de sexo, idade e semana no mapa.
- Contagens absolutas não são taxas de incidência, prevalência ou positividade entre testados.
- Malhas e códigos municipais podem mudar ao longo dos anos: divergências e locais não mapeáveis são explicitados pelo validador.

**Geometria oficial:** https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html
