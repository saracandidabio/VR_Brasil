"""Páginas regionais e mapas municipais; leitura somente de arquivos locais.

Não adiciona notificações ao cubo original. Um polígono representa o município
oficial do IBGE; o valor corresponde ao município de residência no SIVEP-Gripe.
"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from mapas_geo import choropleth_map, geometry_valid
from figuras_ui import chart as chart_figure
from exportacao import mapa_png
from escala_municipal import escala

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
    chart_figure(fig, h)


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



@st.cache_data(show_spinner=False)
def load_state_outlines(data_dir: str, ufs: tuple[str, ...]):
    p = Path(data_dir)/'malha_uf.geojson'
    if not p.exists():
        return None, None
    try:
        geo = json.loads(p.read_text(encoding='utf-8'))
        feats = geo.get('features', [])
        if not feats:
            return None, None
        prop = feats[0].get('properties', {})
        key = next((x for x in ('sigla','SIGLA','uf','UF') if x in prop), None)
        if not key:
            return None, None
        selected = [ft for ft in feats if str(ft.get('properties', {}).get(key)) in set(ufs)]
        return {'type':'FeatureCollection','features':feats}, {'type':'FeatureCollection','features':selected}
    except (OSError, json.JSONDecodeError):
        return None, None


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
    """Mapa com valores conciliados por código IBGE de seis dígitos.

    Exibição estática padrão compatível com Safari; visualização interativa opcional.
    A/B constam apenas no complemento municipal 2023–2026.
    """
    polys=[]
    for uf in ufs:
        g=load_polygons(data_dir,uf)
        if g:polys.extend(g['features'])
    if not polys or mun.empty:
        st.warning('Dados ou malha municipal ausentes. Confira os arquivos em data/.')
        return False
    opts={
        'notificacoes':'Todas as notificações de SRAG',
        'influenza_a':'Influenza A (laboratório)',
        'influenza_b':'Influenza B (laboratório)',
        'influenza_sem_tipo':'Influenza sem tipagem',
        'v_influenza':'Influenza, todos os tipos',
        'a_h3n2':'Influenza A(H3N2)',
        'a_h1n1':'Influenza A(H1N1)pdm09',
        'b_victoria':'Influenza B/Victoria',
        'v_vsr':'VSR',
        'v_sars_cov_2':'SARS-CoV-2',
        'v_rinovirus':'Rinovírus',
    }
    initial = agent if agent in opts else ('v_'+agent if agent!='todos' and 'v_'+agent in opts else 'notificacoes')
    choices=[x for x in opts if x in mun.columns]
    metric=st.selectbox('Indicador no mapa municipal',choices,
        index=choices.index(initial) if initial in choices else 0,
        format_func=opts.get,key='v4_municipal_indicador')
    frame=mun[mun.uf.isin(ufs)].copy()
    # O read_csv padrão converte códigos municipais em int64; o GeoJSON usa str.
    frame['municipio']=frame['municipio'].astype('string').str.strip()
    sums=frame.groupby('municipio', observed=True, dropna=False)[metric].sum().to_dict()
    rows=[{'Código':str(f['properties']['codigo_sivep']),
           'Município':f['properties'].get('nome',str(f['properties']['codigo_sivep'])),
           'Registros':int(sums.get(str(f['properties']['codigo_sivep']),0))}
          for f in polys]
    df=pd.DataFrame(rows)
    available=sum(int(v) for k,v in sums.items() if str(k)!='Não informado')
    mapped=int(df['Registros'].sum())
    if available and mapped/available < .9:
        st.warning(f'Correspondência municipal incompleta: {num(mapped)} de {num(available)} '
                   f'registros com município estão representados. Confira os códigos.')
    st.caption(f'Municípios do IBGE: {len(polys)} · indicadores mapeados: {num(mapped)} · '
               'município de residência (CO_MUN_RES) · contornos estaduais reforçados no mapa estático')
    optcol1,optcol2=st.columns(2)
    with optcol1:
        method=st.selectbox('Escala das cores',
            ['Quantis','Raiz quadrada','Linear'],index=0,key='v7_cor_municipal',
            help='Quantis distribui os municípios em faixas com contagens próximas; '                 'raiz quadrada reduz a influência das cidades maiores; linear apresenta valores absolutos.')
    with optcol2:
        style=st.radio('Visualização do mapa',
            ['Mapa estático (compatível com Safari)','Mapa interativo'],
            horizontal=False,key='v4_municipal_tipo')
    st.caption('A escala de cores muda apenas a visualização. Os números de registros não são alterados.')
    geo={'type':'FeatureCollection','features':polys}
    outline_geo, selected_outline_geo = load_state_outlines(data_dir, tuple(ufs))
    titulo=f'{opts[metric]} · {" + ".join(ufs)}'
    if style.startswith('Mapa estático'):
        preview=mapa_png(geo,df,col_codigo='Código',col_valor='Registros',
                         id_prop='codigo_sivep',titulo=titulo,dpi=140,
                         outline_geo=outline_geo, selected_outline_geo=selected_outline_geo,
                         escala_cor=method)
        st.image(preview,caption='Malha municipal IBGE · intensidade visual por '+method.lower(),
                 use_container_width=True)
    else:
        frame_map=df.copy()
        transformed,ticks,labels=escala(frame_map['Registros'],method)
        frame_map['Intensidade']=transformed
        fig=choropleth_map(frame_map,geo,code_col='Código',id_prop='codigo_sivep',
              name_col='Município',value_col='Intensidade',
              extra_hover_cols={'Registros':':,'},legend_ticks=ticks,
              legend_labels=labels,legend_title='Registros',
              scope='MT+MS' if set(ufs)=={'MT','MS'} else ufs[0],
              auto_camera=True,style='carto-positron', line_color='#506471', line_width=1.05)
        fig.update_layout(height=height,margin=dict(l=0,r=8,t=10,b=10))
        st.plotly_chart(fig,use_container_width=True,
                 config={'displaylogo':False,'scrollZoom':False,'modeBarButtonsToRemove':['toImage']})
    signature=hashlib.sha256((titulo+method+df.to_csv(index=False)).encode()).hexdigest()[:16]
    key='v7_mapa_municipal_800'
    with st.expander('Exportar mapa municipal · PNG 800 dpi'):
        if st.button('Preparar mapa PNG 800 dpi',key='v7_prepare_municipal'):
            with st.spinner('Desenhando mapa em alta resolução...'):
                st.session_state[key]=(signature,mapa_png(geo,df,
                      col_codigo='Código',col_valor='Registros',id_prop='codigo_sivep',titulo=titulo,dpi=800,
                      outline_geo=outline_geo, selected_outline_geo=selected_outline_geo,escala_cor=method))
        stored=st.session_state.get(key)
        if stored and stored[0]==signature:
            st.download_button('Baixar mapa · 800 dpi',data=stored[1],
                   file_name='srag_municipios_'+"_".join(ufs)+'_800dpi.png',mime='image/png',
                   key='v7_download_municipal')
    ranking=df.sort_values('Registros',ascending=False).head(18).copy()
    if not ranking.empty:
        fig=px.bar(ranking.sort_values('Registros'),x='Registros',y='Município',
                   orientation='h',title='Municípios com maior número de registros',
                   color_discrete_sequence=[BLUE],text='Registros')
        fig.update_traces(textposition='outside',cliponaxis=False)
        fig.update_layout(xaxis_title='Notificações',yaxis_title='',margin=dict(l=8,r=46,t=40,b=25))
        chart(fig,460)
    unknown=count(frame[frame.municipio.eq('Não informado')],metric)
    st.caption(f'{num(unknown)} registros sem município válido não foram localizados. '
               'Este mapa municipal é anual (2023–2026); os filtros de semana, sexo e idade '
               'não são aplicados aos polígonos municipais.')
    with st.expander('Tabela de municípios'):
        table=df.sort_values('Registros',ascending=False)
        st.dataframe(table,hide_index=True,use_container_width=True,height=370)
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

    st.subheader('Circulação semanal por agente viral')
    st.caption('Compare marcadores positivos de diferentes vírus no recorte regional escolhido. Este detalhamento cobre 2023–2026.')
    target_names={
        'v_influenza':'Influenza (qualquer tipo)',
        'v_sars_cov_2':'SARS-CoV-2',
        'v_vsr':'VSR',
        'v_rinovirus':'Rinovírus',
        'v_parainfluenza':'Parainfluenza',
        'v_adenovirus':'Adenovírus',
        'v_metapneumovirus':'Metapneumovírus',
        'v_bocavirus':'Bocavírus',
        'v_outros_virus':'Outros vírus',
        'influenza_a':'Influenza A',
        'influenza_b':'Influenza B',
    }
    choices=st.multiselect('Alvos para comparar no Centro-Oeste',list(target_names),
        default=['influenza_a','influenza_b','v_vsr'],format_func=lambda k:target_names[k],
        key='regio_alvos')
    if choices:
        selected_week=temp[temp.semana.between(1,53)].groupby(['ano','semana'],observed=True)[choices].sum().reset_index().sort_values(['ano','semana'])
        if not selected_week.empty:
            selected_week['Ano – SE']=selected_week.ano.astype(str)+'-SE'+selected_week.semana.astype(str).str.zfill(2)
            long=selected_week.melt(id_vars=['ano','semana','Ano – SE'],value_vars=choices,
                                    var_name='Alvo',value_name='Detecções')
            long['Alvo']=long['Alvo'].map(target_names)
            chart_line=px.line(long,x='Ano – SE',y='Detecções',color='Alvo',
                title='Detecções semanais por agente viral')
            chart_line.update_layout(hovermode='x unified',
                xaxis=dict(type='category',nticks=16,tickangle=-35),
                legend=dict(orientation='h',y=1.15,x=0))
            chart(chart_line,465)
            st.download_button('Exportar série regional por alvo (CSV)',
                selected_week.to_csv(index=False).encode('utf-8-sig'),
                'srag_serie_regional_alvos.csv','text/csv')
    else:
        st.info('Selecione pelo menos um alvo.')

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
        fig.update_traces(textposition='outside',cliponaxis=False,texttemplate='%{x:,.0f}')
        fig.update_xaxes(range=[0,max(sub['Detecções'].max(),1)*1.22])
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
