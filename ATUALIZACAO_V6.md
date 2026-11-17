# Atualização V6 — Detecção laboratorial x classificação final

**O ZIP inclui a base agregada anterior, sem reprocessamento histórico.** A classificação sem resultado não pode ser calculada com fidelidade apenas dos agregados existentes.

## O que mudou

1. Adição de três métricas exclusivas da classificação final, sem resultado de PCR/antígeno registrado e sem marcador viral positivo: influenza, COVID-19 e outros vírus respiratórios.
2. Novos painéis na visão geral e perfil epidemiológico para essas métricas (visíveis após regenerar cubos).
3. Separação INFA/INFB continua baseada nos campos de tipagem laboratorial, disponível para 2023–2026 nos escopos complementares. `CLASSI_FIN=1` não informa o tipo A/B.
4. Testes negativos e inconclusivos **não** são tratados como ausência de resultado.

## Atualização de dados necessária

- `python construir_base.py --todos --reprocessar` para 2019–2026
- `python preparar_centro_oeste.py --todos --reprocessar` para o complemento 2023–2026
- Execute `python validar_publicacao.py` e `python -m pytest -q` antes de atualizar o GitHub.

Caso os CSVs oficiais originais não estejam disponíveis, a reconstrução fará download das fontes. Os arquivos `data/*.csv.gz` atuais **não** contêm a informação necessária para obter contagens fidedignas.
