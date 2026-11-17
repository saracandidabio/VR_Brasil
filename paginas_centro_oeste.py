"""Páginas regionais e mapas municipais; leitura somente de arquivos locais.

Não adiciona notificações ao cubo original. Um polígono representa o município
oficial do IBGE; o valor corresponde ao município de residência no SIVEP-Gripe.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

UF_DETAIL = ('MT','MS')
CO_UFS = ('MT','MS','GO','DF')
BLUE = '#23617D'
ORANGE = '#D68952'
TEAL = '#287C73'
YEARS_FOCUS = {2023,2024,2025,2026}


def num(v):
    return f'{int(v):,}'.replace(',','.')


def count(data, field):
    return int(data[field].sum()) if field in data else 0


def chart(fig, h=440):
    fig.update_layout(height=h, margin=dict(l=4,r=4,t=35,b=18),
                      paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                      font_family='Arial',font_size=12)
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo':False,'scrollZoom':False})


@st.cache_data(show_spinner=False)
def load_complement(data_dir: str, years: tuple[int,...], kind: str):
    prefix = 'municipios_co' if kind == 'municipios' else 'temporal_influenza'
    frames = []
    for year in years:
        file = Path(data_dir)/f'{prefix}_{year}.csv.gz'
        if file.exists():
            frames.append(pd.read_csv(file, compression='gzip',
                        dtype={'municipio':'string','uf':'string','sexo':'string',
                               'faixa_etaria':'string','escopo':'string'},low_memory=False))
    return pd.concat(frames,ignore_index=True) if frames else pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_polygons(data_dir: str, uf: str):
    p = Path(data_dir)/f'malha_municipios_{uf}.geojson'
    if not p.exists():
        return None
    try:
        geo = json.loads(p.read_text(encoding='utf-8'))
        feats = geo.get('features', [])
        if not feats or any('codigo_sivep' not in f.get('properties',{}) for f in feats):
            return None
        return geo
    except (OSError, json.JSONDecodeError):
        return None


def apply_filters(data, years, week, sex, ages):
    if data.empty:
        return data.copy()
    out = data[data.ano.isin(years) & data.semana.between(*week)].copy()
    if sex:
        out = out[out.sexo.isin(sex)]
    if ages:
        out = out[out.faixa_etaria.isin(ages)]
    return out


def municipal_map(mun: pd.DataFrame, ufs: list[str], agent: str, data_dir: str, height=590):
    """Retorna False e explica o motivo se faltam geometria ou cubo municipal."""
    polys = []
    for uf in ufs:
        g = load_polygons(data_dir,uf)
        if g:
            polys.extend(g['features'])
    if not polys:
        st.info('O mapa municipal depende dos GeoJSON do IBGE. Execute '
                '`python preparar_centro_oeste.py --apenas-malhas` e publique os arquivos gerados em `data/`.')
        return False
    if mun.empty:
        st.info('O complemento municipal ainda não está publicado. '
                'Execute `python preparar_centro_oeste.py --todos` e envie os arquivos de `data/`.')
        return False
    metric = 'notificacoes' if agent == 'todos' else 'v_'+agent
    if metric not in mun.columns:
        st.warning('A variável selecionada não consta da agregação municipal.')
        return False
    frame = mun[mun.uf.isin(ufs)]
    sums = frame.groupby('municipio', observed=True, dropna=False)[metric].sum().to_dict()
    rows = [{'Código':f['properties']['codigo_sivep'],
             'Município':f['properties'].get('nome',f['properties']['codigo_sivep']),
             'Registros':int(sums.get(f['properties']['codigo_sivep'],0))}
            for f in polys]
    if not rows:
        return False
    df = pd.DataFrame(rows)
    fig = px.choropleth(df, geojson={'type':'FeatureCollection','features':polys},
                        locations='Código',featureidkey='properties.codigo_sivep',
                        color='Registros',hover_name='Município',
                        hover_data={'Código':True,'Registros':':,'},
                        color_continuous_scale='Blues',
                        labels={'Registros':'Notificações'})
    fig.update_geos(fitbounds='locations',visible=False,projection_type='mercator',
                    showcoastlines=False,showland=True,landcolor='#e8eff2')
    fig.update_traces(marker_line_color='#edf2f5',marker_line_width=.7)
    fig.update_layout(coloraxis_colorbar=dict(title='Registros',thickness=13,len=.75))
    chart(fig,height)
    unknown = count(frame[frame.municipio.eq('Não informado')],metric)
    st.caption(f'Municípios de residência (CO_MUN_RES) · malha IBGE · '
               f'{num(unknown)} notificações sem município válido não foram localizadas. '
               'Mapa municipal é ANUAL (não responde a filtros de semana, sexo ou faixa etária). Contagens absolutas.')
    with st.expander('Tabela de municípios'):
        table = df.sort_values('Registros',ascending=False)
        st.dataframe(table[['Município','Registros']],use_container_width=True,hide_index=True,height=370)
        st.download_button('Exportar municípios (CSV)',table.to_csv(index=False).encode('utf-8-sig'),
                           'municipios_srag_filtro.csv','text/csv')
    return True


def regional_page(national_filtered: pd.DataFrame, mun: pd.DataFrame, timeline: pd.DataFrame,
                  years: list[int], selected_ufs: list[str], focus: str, data_dir: str):
    st.header('Centro-Oeste · MT e MS')
    st.caption('Vigilância de SRAG no Centro-Oeste, com detalhamento de influenza A/B e mapas municipais de MT e MS.')
    if mun.empty or timeline.empty:
        st.warning('**Falta preparar o complemento regional.** Os cubos nacionais atuais não guardam '
                   'municípios, influenza A/B nem mês de início dos sintomas. Rode no Mac: '
                   '`python preparar_centro_oeste.py --todos --malhas`. '
                   'Esse processo não altera as tabelas nacionais já publicadas.')
        frame=national_filtered[national_filtered.uf.isin(CO_UFS)]
        if not frame.empty:
            view=frame.groupby('uf',observed=True)[['notificacoes','v_influenza']].sum().reset_index()
            st.dataframe(view.rename(columns={'uf':'UF','notificacoes':'Notificações SRAG',
                                 'v_influenza':'Influenza (marcador positivo)'}),
                         use_container_width=True,hide_index=True)
        return
    if selected_ufs and any(uf not in CO_UFS for uf in selected_ufs):
        st.info('Esta página tem recorte específico no Centro-Oeste. Seleções de UF fora dessa região '
                'não alteram os indicadores regionais; use a página Geografia para outros estados.')
    elif selected_ufs and any(uf in ('GO','DF') for uf in selected_ufs):
        st.caption('A comparação regional está organizada em Centro-Oeste, MT e MS. '
                   'GO/DF estão incluídos no total Centro-Oeste, sem mapa municipal dedicado.')
    supplementary_manifest = Path(data_dir)/'centro_oeste_manifest.json'
    if supplementary_manifest.exists():
        try:
            meta = json.loads(supplementary_manifest.read_text(encoding='utf-8'))
            mismatch = [year for year, item in meta.get('anos',{}).items()
                        if item.get('compativel_com_cubo_nacional') is False and int(year) in years]
            if mismatch:
                st.warning('Atenção: complemento e cubo nacional foram construídos com snapshots diferentes '
                           'nos anos '+', '.join(mismatch)+'. Para comparar as páginas diretamente, '
                           'é necessário sincronizar as extrações.')
        except (ValueError, OSError):
            pass
    extra = set(timeline.ano.unique())
    missing = sorted((YEARS_FOCUS & set(years))-extra)
    if missing:
        st.warning('Anos ainda sem complemento: '+', '.join(str(v) for v in missing)+'. '
                   'Os gráficos não representam a série completa até esses anos serem preparados.')
    options=['Centro-Oeste','MT','MS']
    initial = selected_ufs[0] if len(selected_ufs)==1 and selected_ufs[0] in UF_DETAIL else 'Centro-Oeste'
    area=st.radio('Escopo regional',options,index=options.index(initial),horizontal=True)
    temp=timeline[timeline.escopo.eq(area)]
    cards=st.columns(4)
    for col, label, field in zip(cards,
        ['Notificações SRAG','Influenza A','Influenza B','A(H3N2) confirmada'],
        ['notificacoes','influenza_a','influenza_b','a_h3n2']):
        with col:
            st.metric(label,num(count(temp,field)))
    st.caption('Influenza A/B: marcadores laboratoriais tipados positivos; '
               'H3N2: subtipo informado em PCR. Não somar A e B indiscriminadamente por possibilidade de codetecção.')

    st.subheader('Evolução semanal — 2023 a 2026')
    labels={'influenza_a':'Influenza A','influenza_b':'Influenza B',
            'a_h1n1':'Influenza A(H1N1)pdm09','a_h3n2':'Influenza A(H3N2)',
            'b_victoria':'Influenza B/Victoria','b_yamagata':'Influenza B/Yamagata'}
    choice=st.selectbox('Tipo ou subtipo',list(labels),format_func=labels.get)
    years_week=temp[temp.semana.between(1,53)].groupby(['ano','semana'],observed=True)[choice].sum().reset_index()
    if not years_week.empty:
        years_week['Temporada']=years_week.ano.astype(str)
        fig=px.line(years_week,x='semana',y=choice,color='Temporada',
                    labels={'semana':'Semana epidemiológica',choice:'Detecções'},
                    title=labels[choice]+' · temporadas sobrepostas')
        fig.update_layout(hovermode='x unified')
        chart(fig,435)

    left,right=st.columns([1.1,1],gap='large')
    with left:
        st.subheader('Março de cada ano')
        march=temp[temp.mes.eq(3)].groupby('ano',observed=True)[['influenza_a','influenza_b']].sum().reset_index()
        march=march.melt('ano',var_name='Tipo',value_name='Detecções')
        march['Tipo']=march.Tipo.map({'influenza_a':'Influenza A','influenza_b':'Influenza B'})
        if not march.empty:
            march['Ano']=march.ano.astype(str)
            fig=px.bar(march,x='Ano',y='Detecções',color='Tipo',barmode='group',text='Detecções',
                       color_discrete_map={'Influenza A':BLUE,'Influenza B':ORANGE},
                       title='Março de 2023 a 2026')
            chart(fig,395)
    with right:
        st.subheader('Subtipos e linhagens')
        vals=[('a_h1n1','A(H1N1)pdm09'),('a_h3n2','A(H3N2)'),
              ('a_nao_subtipada','A não subtipada'),('b_victoria','B/Victoria'),('b_yamagata','B/Yamagata')]
        sub=pd.DataFrame([{'Identificação':name,'Detecções':count(temp,key)} for key,name in vals])
        fig=px.bar(sub.sort_values('Detecções'),x='Detecções',y='Identificação',orientation='h',
                   text='Detecções',color_discrete_sequence=[TEAL])
        fig.update_traces(textposition='outside',cliponaxis=False)
        chart(fig,395)

    with st.expander('Tabela: março de 2023–2026 no Brasil, Centro-Oeste, MT e MS'):
        table=timeline[timeline.mes.eq(3)].groupby(['escopo','ano'],observed=True)[[
            'notificacoes','influenza_a','influenza_b','a_h1n1','a_h3n2','b_victoria','b_yamagata']].sum().reset_index()
        st.dataframe(table.sort_values(['escopo','ano']),use_container_width=True,hide_index=True)
        st.download_button('Exportar comparação de março',table.to_csv(index=False).encode('utf-8-sig'),
                           'influenza_marco_brasil_co.csv','text/csv')

    with st.expander('Abril de 2025 × março de 2026 · Brasil, Centro-Oeste, MT e MS'):
        selected = timeline[((timeline.ano.eq(2025)) & (timeline.mes.eq(4))) |
                            ((timeline.ano.eq(2026)) & (timeline.mes.eq(3)))]
        compare = selected.groupby(['escopo','ano','mes'],observed=True)[[
            'notificacoes','influenza_a','influenza_b','a_h1n1','a_h3n2','b_victoria','b_yamagata']].sum().reset_index()
        if not compare.empty:
            compare['Período'] = compare['ano'].astype(str)+' / '+compare['mes'].map({3:'Março',4:'Abril'})
            compare['A por 100 notificações SRAG'] = (100*compare.influenza_a / compare.notificacoes.where(compare.notificacoes.ne(0))).round(2)
            compare['B por 100 notificações SRAG'] = (100*compare.influenza_b / compare.notificacoes.where(compare.notificacoes.ne(0))).round(2)
            st.dataframe(compare[['escopo','Período','notificacoes','influenza_a','influenza_b',
                                  'a_h1n1','a_h3n2','b_victoria','b_yamagata',
                                  'A por 100 notificações SRAG','B por 100 notificações SRAG']],
                         use_container_width=True,hide_index=True)
            st.caption('Esses percentuais têm como denominador todas as notificações SRAG no recorte; '
                       'não representam positividade laboratorial entre testados nem incidência populacional.')
        else:
            st.info('Esses períodos ainda não estão disponíveis no complemento.')

    st.subheader('Cartografia municipal')
    st.caption('Dados municipais por ano (sem estratificação individual adicional). Na barra lateral, ao selecionar apenas MT ou MS, o mapa da página Geografia também se amplia '
               'automaticamente para os municípios do(s) estado(s).')
    selected=[area] if area in UF_DETAIL else ['MT','MS']
    municipal_map(mun,selected,focus,data_dir,650)

    with st.expander('Contexto dos resultados das expedições — estudo NAVIO'):
        st.markdown('''Estes achados são **dados do estudo**, apresentados separadamente das notificações oficiais:

- **Influenza A:** 14 resultados positivos, sendo 3 em abril de 2025 e 11 em março de 2026 (H3N2 nos resultados de março).
- **Influenza B:** 12 resultados positivos em março de 2026, caracterizados como linhagem Victoria.

Os números do estudo **não foram somados** aos indicadores oficiais do SIVEP-Gripe.''')
    st.caption('Os dados SIVEP-Gripe cobrem SRAG e não todos os quadros de influenza. '
               'O mês é calculado por DT_SIN_PRI; a semana por SEM_PRI. '
               'Anos recentes estão sujeitos a revisão, atraso de notificação e mudanças de testagem.')
