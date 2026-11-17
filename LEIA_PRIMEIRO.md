# LEIA PRIMEIRO — pacote completo SRAG Brasil

Este ZIP foi montado a partir das **duas pastas enviadas** e já inclui:

- Dados nacionais **2019–2026** (`data/cubo_srag_*.csv.gz` e `data/manifest.json`);
- Complementos regionais de **2023–2026** (`temporal_influenza_*.csv.gz`, `municipios_co_*.csv.gz`, `centro_oeste_manifest.json`);
- Malha das 27 UFs e malhas municipais de **MT** e **MS**;
- Dashboard atualizado, com autoria e descrição do SIVEP-Gripe;
- `README.md` com o link direto **https://vrbrasil.streamlit.app/**.

**Não é preciso baixar novamente os arquivos oficiais nem executar os construtores para publicar este snapshot.**

## Testar no Mac

Abra o Terminal na pasta descompactada e execute:

```bash
python3 -m pip install -r requirements.txt
python3 validar_publicacao.py
streamlit run streamlit_app.py
```

## Publicar substituindo o conteúdo do GitHub

Veja **[PUBLICAR_GITHUB.md](PUBLICAR_GITHUB.md)**. A sequência recomendada é clonar o repositório atual, remover **somente os arquivos versionados** com `git rm -r -- .`, copiar os arquivos deste pacote para dentro do clone, revisar `git status` e publicar um único commit. Assim o nome do repositório e a configuração do Streamlit permanecem.

Não envie um ZIP inteiro como único arquivo do repositório: **extraia e publique o conteúdo da pasta**. A pasta `.venv/` do projeto original foi excluída intencionalmente (o Streamlit instala dependências a partir de `requirements.txt`). O pacote **não contém os CSVs brutos de notificações individuais**.

## Atenção à interpretação

- As contagens são **notificações SRAG** e não pessoas únicas, infecções totais ou incidência.
- Dados oficiais: SIVEP-Gripe/Ministério da Saúde. O período de preparo das extrações está registrado nos manifestos.
- O detalhe municipal, a tipagem A/B e as comparações específicas começam em **2023**; os cubos nacionais continuam desde **2019**.
- Os mapas municipais trabalham com recorte **anual**: não aplicam filtros individuais de sexo, idade e semana.
- Os cubos nacionais presentes não incluem os campos `class2_*`; a decomposição exclusiva de “Outro vírus respiratório” ainda depende de reprocessamento das fichas originais.
