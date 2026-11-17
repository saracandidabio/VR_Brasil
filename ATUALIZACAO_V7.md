# Atualização V7 — correções de interface

- Retirada a página **Co-detecções** da navegação, mantendo os indicadores existentes nos arquivos agregados.
- Criada a aba **Influenza A e B**: indicadores, evolução temporal, temporadas sobrepostas, subtipos/linhagens, perfil por idade/sexo, mapas de MT/MS e classificação final.
- Retirados os cartões repetitivos de Influenza A/B de outras páginas.
- Corrigido o `KeyError` da seleção de Influenza A/B em **Séries temporais → Temporadas sobrepostas**: o formatador agora reconhece o dicionário estendido.
- Corrigida a ordem temporal da comparação multialvo, inclusive quando INFA/INFB não possuem dados em 2019–2022.
- Mapas municipais: escalas **Quantis**, **Raiz quadrada** e **Linear**; bordas realçadas e ranking com maiores municípios.
- Conservados os arquivos nacionais 2019–2026, complementos 2023–2026, malhas e opção PNG 800 dpi.

### Atenção ao cálculo

`CLASSI_FIN=1` não especifica INFA ou INFB. O cruzamento *classificado como influenza sem resultado laboratorial* ainda não está disponível nos cubos agregados fornecidos; o aplicativo avisa em vez de fabricar contagens.

### Limitação de validação

A sintaxe Python, os testes automatizados, o processamento de mapas e a integridade dos arquivos foram verificados localmente. Não foi possível abrir a interface Streamlit com navegador neste ambiente de execução; valide a experiência final após publicar.
