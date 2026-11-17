# Observatório de Vírus Respiratórios — SIVEP-Gripe/SRAG Brasil

Aplicativo Streamlit inspirado no explorador de Orthoherpes da pesquisa, **usando exclusivamente o SIVEP-Gripe (SRAG)**. O site **não acessa a internet**: todos os dados de consulta são gerados e compactados previamente por um processamento único local. O objetivo é publicar os dados agregados no GitHub para hospedar no Streamlit Community Cloud.

> **Estado deste pacote:** contém o aplicativo, o pipeline completo e uma **amostra real de 2026** (212.278 notificações, arquivo originalmente obtido em **14/09/2026** no material enviado). **Não afirmar que os oito anos foram baixados**: devido à indisponibilidade de acesso aos downloads oficiais neste ambiente, os anos de 2019–2025 precisam ser obtidos pelo comando de construção abaixo. O arquivo 2026 do pacote também será substituído pela versão mais recente do portal quando o comando for executado.

## 1. Rodar a construção uma vez (macOS)

Abra o Terminal, entre na pasta extraída e execute:

```bash
bash preparar_tudo.sh
```

Esse comando cria um ambiente virtual, instala os pacotes, baixa e processa os **oito anos oficiais (2019–2026)**, prepara os dados para GitHub e valida a integridade. O processamento só precisa ser repetido quando você quiser atualizar as bases vivas. A conexão com a internet é necessária **apenas durante a construção**. Recomenda-se ter vários GB de espaço livre durante o download dos CSVs anuais; o script exclui os brutos após cada ano para não encher o repositório.

Para executar as etapas separadamente:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
python construir_base.py --todos
python validar_base.py
streamlit run streamlit_app.py
```

Se a conexão cair, repita `python construir_base.py --todos`: os anos concluídos são preservados e os downloads parciais com suporte a `Range` são retomados quando possível. Para atualizar dados que já foram preparados, use `python construir_base.py --todos --reprocessar` (pode exigir baixar novamente arquivos anuais). Os arquivos originais **não** precisam ser copiados para o GitHub.

Para verificar um recorte específico: `python construir_base.py --anos 2025 2026`. Para usar CSV local: `python construir_base.py --arquivo-local /caminho/arquivo.csv --ano-local 2025`. Até ter os oito anos completos, `python validar_base.py --permitir-parcial` permite validar o material que já estiver presente.

## 2. O que aparece no site

- **Visão geral:** notificações de SRAG, marcadores virais, UTI, óbitos e série temporal.
- **Agentes virais:** influenza, SARS-CoV-2, VSR, rinovírus e outros, com distribuição etária e codetecção.
- **Séries temporais:** evolução semanal, sobreposição de temporadas e resumos por ano.
- **Distribuição geográfica:** UFs de residência, tabela e mapa. O preparador tenta baixar uma malha vetorial do IBGE para mapa por UF. Se a API estiver indisponível, o mapa mostra marcadores nas capitais, explicitamente identificados como representações da UF, não locais individuais.
- **Perfil epidemiológico:** faixa etária, sexo, classificação final, internações, UTI e óbitos.
- **Explorador:** consultas filtradas, agregações e exportação CSV.
- **Métodos e auditoria:** fonte, contagens por arquivo e hashes de integridade.

Os filtros de **ano, UF, sexo, faixa etária e semana epidemiológica** são aplicados à tabela agregada; o agente selecionado muda o indicador em foco sem eliminar o denominador de notificações. A semana `0` indica ausência de preenchimento válido e permanece incluída nos totais. Não se infere resultado de teste a partir da classificação final.

## 3. Publicação no GitHub e Streamlit Community Cloud

**Só publique como base completa quando `python validar_base.py` terminar sem erros**, exibindo os anos 2019–2026.

1. Crie um repositório GitHub com o conteúdo desta pasta. Inclua **`data/cubo_srag_2019.csv.gz` até `data/cubo_srag_2026.csv.gz`**, `data/manifest.json` e, se obtido, `data/malha_uf.geojson`.
2. Inclua `streamlit_app.py`, `requirements.txt` e `.streamlit/config.toml`.
3. **Não envie** `downloads_srag/`, `.venv/` nem CSVs brutos com notificações individuais. Esses caminhos estão no `.gitignore`.
4. No [Streamlit Community Cloud](https://share.streamlit.io/), crie um aplicativo a partir do repositório; selecione a branch e configure `streamlit_app.py` como entrada.
5. O aplicativo publicado funciona somente com os arquivos compactados versionados. Não roda `construir_base.py`, não consulta o portal do Ministério da Saúde e não faz download de dados na nuvem.

Para testar o site localmente após a construção, rode `streamlit run streamlit_app.py`. Se você publicar antes de preparar os oito anos, o site exibirá um alerta explícito de **base parcial**.

## 4. Fonte e recorte

Portal oficial: <https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026>. De 2019 a 2024 os recursos CSV oficiais são arquivos anuais disponibilizados em março de 2026. Para 2025 e 2026, o programa lê a página do recurso para buscar a versão publicada; se não conseguir, utiliza uma URL de contingência cuja versão é de 16/11/2026 e registra o endereço efetivamente usado. Fontes são tratadas **por ano de arquivo epidemiológico**, e **não** combinadas com e-SUS Notifica ou SG Sentinela. Os arquivos originais são validados por hash SHA256, registrado no manifesto.

A API de Malhas Geográficas do IBGE é usada apenas na preparação, quando disponível, e a malha é armazenada em `data/malha_uf.geojson`.

### O que significa "evitar duplicações"

Garantimos **um arquivo de SRAG por ano** e não misturamos sistemas. Não há uma regra segura de deduplicação automática de pessoas usando somente o arquivo publicado; o preparador **não elimina notificações internas** e os totais devem ser chamados de *notificações*, não indivíduos únicos. A equipe técnica deve definir eventuais regras de deduplicação antes de divulgar estimativas de pessoas infectadas.

### Cuidados na interpretação

- Detecção laboratorial: um dos campos de agente correspondente igual a `1` na ficha. Campos vazios, negativos ou não testados não são confundidos.
- A contagem de detecções pode superar o número de notificações, pois os grupos virais não são mutuamente exclusivos.
- Óbito SRAG: `EVOLUCAO=2`; sem ajuste de atraso de encerramento, e diferente de óbito por outras causas.
- Mudanças nas estratégias de notificação, diagnóstico e testagem dificultam comparar diretamente 2019 com 2020–2026.
- **Não calcular incidência** nem positividade entre testados com o denominador total de notificações.
- Tabelas de publicação são agregadas por ano, semana, UF, sexo e faixa etária; não contêm identificadores, municípios ou datas individuais. Isso não corresponde a uma garantia formal de anonimização, especialmente para células pequenas.
- As bases vivas de 2025/2026 podem receber correções oficiais posteriores à data de download: o snapshot do GitHub **não é um painel em tempo real**.

## 5. Organização

```text
srag_brasil_dashboard/
├── streamlit_app.py               # aplicativo apenas de leitura dos dados locais
├── construir_base.py              # construtor local: download, padronização e compactação
├── validar_base.py                # conferência de contagens, hashes, anos e GitHub
├── preparar_tudo.sh               # um único comando no Mac
├── requirements.txt              # dependências do aplicativo online
├── requirements-build.txt        # dependências adicionais do processamento local
├── .streamlit/config.toml
├── data/
│   ├── cubo_srag_2026.csv.gz      # exemplo já incluído (14/09/2026)
│   └── manifest.json              # declara explicitamente o conjunto PARCIAL
└── tests/
```

O instalador não publica no GitHub por conta própria. Após o processamento, os dados permanecem na pasta `data/`; só será necessário enviar o projeto para o seu repositório.
