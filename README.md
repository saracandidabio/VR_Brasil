# Observatório de Vírus Respiratórios — SRAG Brasil

**[Acessar o dashboard online — vrbrasil.streamlit.app](https://vrbrasil.streamlit.app/)**  
[Código-fonte no GitHub](https://github.com/saracandidabio/VR_Brasil)

**Idealização:** Sara Cândida Ferreira dos Santos.  
**Fonte exclusiva:** Ministério da Saúde — SIVEP-Gripe/SRAG (dados oficiais públicos).

Painel exploratório em Streamlit para notificações de Síndrome Respiratória Aguda Grave (SRAG) e respectivos marcadores virais, desfechos e distribuição espacial. Notificações não são pessoas únicas, não equivalem a incidência populacional e não garantem deduplicação individual.

## Organização — versão 7

O painel possui as áreas: Visão geral; Agentes virais; Séries temporais; Distribuição geográfica; Centro-Oeste · MT e MS; **Influenza A e B**; Perfil epidemiológico; Explorador de dados; Métodos e auditoria.

- **Nacional 2019–2026:** oito arquivos anuais agregados, mantendo os recortes de ano, semana epidemiológica, UF, sexo e faixa etária.
- **Centro-Oeste, MT e MS 2023–2026:** complementos que guardam Influenza A/B, subtipos/linhagens e mapas municipais de MT/MS por ano.
- **Aba Influenza A e B:** reúne em um só lugar indicadores, séries temporais, subtipos, linhagens, perfis, mapas municipais, classificações finais e exportação CSV. O quadro repetido de A/B foi retirado das demais abas. A aba de co-detecções foi removida temporariamente.
- **Mapas municipais:** escolha entre quantis (padrão), raiz quadrada e escala linear. As cores podem realçar diferenças entre municípios, mas o valor absoluto original continua disponível no mapa interativo, no ranking e na tabela CSV. Limites municipais e estaduais mais destacados. No mapa nacional, o zoom por UF conserva as fronteiras estaduais; o detalhamento **municipal** somente existe para MT/MS na base incluída.
- **Exportação científica:** PNG gerado pelo Matplotlib com metadados de resolução de 800 dpi.

### Limitações metodológicas importantes

A tipagem laboratorial INFA/INFB está disponível apenas no complemento **2023–2026**, para Brasil, Centro-Oeste, MT, MS e MT+MS. Não significa zero para 2019–2022 nem oferece A/B por outras UFs individualmente. `CLASSI_FIN=1` significa classificação final por influenza, mas **não distingue A de B**.

A métrica *classificado como influenza sem resultado laboratorial registrado* só pode ser calculada nos microdados, cruzando `CLASSI_FIN` e resultados de PCR/antígeno. Os cubos incluídos ainda não contêm essa coluna. A aba de influenza avisa a indisponibilidade em vez de mostrar zero ou inferir um valor. Reconstruir os agregados oficiais com os scripts `construir_base.py` e `preparar_centro_oeste.py` será necessário apenas para preencher esse indicador adicional. O mesmo cuidado vale para as demais classificações sem resultado laboratorial.

Mapas municipais são anuais e não seguem filtros de sexo, idade e semana (evita inferências sobre pequenos grupos). Nos gráficos temporais, usar `SEM_PRI` e verificar cobertura do período. O painel não consulta o SIVEP-Gripe durante a navegação e não se atualiza automaticamente.

## Executar e validar

Instale Python 3.10+ e execute na pasta do projeto:

```bash
python3 -m pip install -r requirements.txt
python3 validar_publicacao.py
python3 -m pytest -q
streamlit run streamlit_app.py
```

Todos os CSV agregados e GeoJSON necessários para esta versão estão em `data/`. **Não publique CSVs brutos com notificações individuais.**

### Atualizar o repositório

Consulte [LEIA_PRIMEIRO.md](LEIA_PRIMEIRO.md) ou [PUBLICAR_GITHUB.md](PUBLICAR_GITHUB.md). Faça o upload de todo o **conteúdo** da pasta descompactada para a raiz do repositório, sem criar subpasta e sem enviar `.venv`, caches ou arquivos locais de download.

### Referências de origem

- [Ministério da Saúde — SRAG 2019–2026](https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026)
- [IBGE — malhas geográficas](https://servicodados.ibge.gov.br/api/v3/malhas)
