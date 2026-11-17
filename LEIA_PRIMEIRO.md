# Observatório SRAG Brasil — V8

**Atualização:** todos os mapas são interativos e utilizam **escala de cor linear** (zero ao maior valor), sem quantis ou raiz quadrada. Ao filtrar uma UF, a página `Distribuição geográfica` passa ao nível **municipal**, com nomes e contagens no cursor, zoom automático e destaque para os limites estaduais.

## Atenção: dados ainda precisam ser preparados para todos os municípios

O ZIP inclui os 8 cubos nacionais (2019–2026), a série regional de 2023–2026 e as malhas municipais já disponíveis para MT e MS. **Não** inclui os microdados originais dos 8 anos, nem as tabelas municipais das demais 25 UFs: os arquivos anuais disponíveis aqui não permitiram gerar o conjunto completo com a mesma extração do painel nacional.

Para gerar os dados municipais das 27 UFs e sincronizar os agregados **uma única vez**, extraia o ZIP e execute, em um Terminal na pasta do projeto:

```bash
bash preparar_brasil_uma_vez.sh
```

Esse comando:

1. Instala dependências de construção em `.venv`.
2. Baixa os CSVs oficiais SIVEP-Gripe **um por ano** (2019–2026).
3. Reprocessa os cubos nacionais a partir da **mesma fonte** usada no complemento municipal, evitando divergências por data de extração.
4. Reconstrói o complemento Centro-Oeste/Influenza (2023–2026) com o mesmo arquivo anual.
5. Gera `data/municipios_brasil_2019.csv.gz` até `...2026.csv.gz` e o manifesto de integridade.
6. Obtém a malha oficial do IBGE por UF (`data/malha_municipios_<UF>.geojson`, incluindo GO).
7. Valida a igualdade de contagens com os cubos nacionais por UF e ano, e exige as 27 malhas.

Os downloads oficiais são feitos na **preparação**, não durante a navegação no Streamlit. Se a conexão cair, execute novamente o mesmo comando: cada ano concluído e malha validada é reaproveitado. O processo pode transferir vários gigabytes temporariamente.

Depois da mensagem **DADOS MUNICIPAIS COMPLETOS**, envie o conteúdo desta pasta ao GitHub, incluindo `data/` e `.streamlit/`, mas não inclua `.venv/` nem `downloads_srag/`.

Link do site: https://vrbrasil.streamlit.app/

## Como usar o mapa

- **Sem UF selecionada:** Brasil por UFs, com dados nacionais de 2019–2026.
- **Com uma ou mais UFs selecionadas:** municípios correspondentes, com ajuste automático do enquadramento.
- **Escala linear:** todos os valores absolutos de zero ao máximo estão igualmente espaçados na escala; municípios pequenos podem ter tonalidades próximas às de zero quando a capital concentra muitos registros. Use tooltip e o ranking para explorar diferenças.
- **Limite:** o mapa municipal é agregado por **ano e município de residência**, sem aplicar filtros de semana, sexo ou idade. Isso é informado na interface.
- **Influenza A/B:** dados municipais dependem da tipagem laboratorial disponível em cada ano. As análises especiais 2023–2026 continuam na aba Influenza A e B.
- **Figuras:** mapas e gráficos mantêm exportação PNG de 800 dpi.

**Advertência:** o número de notificações de SRAG não é incidência populacional, e não identifica pessoas únicas. A malha do IBGE representa a divisão administrativa atual e pode não coincidir integralmente com mudanças municipais históricas.
