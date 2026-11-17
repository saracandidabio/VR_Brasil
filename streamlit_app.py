"""Observatório SRAG Brasil: somente SIVEP-Gripe, dados offline preparados previamente."""
from __future__ import annotations
import io
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from paginas_centro_oeste import load_complement, apply_filters, municipal_map, regional_page
from mapas_geo import choropleth_map, geometry_valid

BASE=Path(__file__).resolve().parent
DATA=BASE/'data'
VIRUSES={
 'influenza':'Influenza','sars_cov_2':'SARS-CoV-2','vsr':'Vírus sincicial respiratório (VSR)',
 'parainfluenza':'Parainfluenza','adenovirus':'Adenovírus',
 'metapneumovirus':'Metapneumovírus','bocavirus':'Bocavírus',
 'rinovirus':'Rinovírus','outros_virus':'Outros vírus'
}
AGES=['< 2 anos','2 a 4 anos','5 a 9 anos','10 a 19 anos','20 a 29 anos',
      '30 a 39 anos','40 a 49 anos','50 a 59 anos','≥ 60 anos','Não informado']
CLASS={1:'Influenza',2:'Outro vírus respiratório',3:'Outro agente etiológico',
       4:'Não especificada',5:'COVID-19'}
RESOLVED_CLASS2={
 'class2_influenza':'Influenza',
 'class2_sars_cov_2':'SARS-CoV-2',
 'class2_vsr':'Vírus sincicial respiratório (VSR)',
 'class2_parainfluenza':'Parainfluenza',
 'class2_adenovirus':'Adenovírus',
 'class2_metapneumovirus':'Metapneumovírus',
 'class2_bocavirus':'Bocavírus',
 'class2_rinovirus':'Rinovírus',
 'class2_outros_virus_nao_especificados':'Outros vírus não especificados',
 'class2_codeteccao':'Codetecção / múltiplos vírus',
 'class2_sem_detalhe':'Sem detalhamento laboratorial'
}
PAGES=['Visão geral','Agentes virais','Séries temporais','Distribuição geográfica',
       'Centro-Oeste · MT e MS','Perfil epidemiológico','Explorador de dados','Métodos e auditoria']
CAPITALS={
'AC':(-9.97,-67.81),'AL':(-9.67,-35.74),'AP':(0.035,-51.07),
'AM':(-3.12,-60.02),'BA':(-12.97,-38.50),'CE':(-3.72,-38.54),
'DF':(-15.78,-47.93),'ES':(-20.32,-40.34),'GO':(-16.68,-49.25),
'MA':(-2.53,-44.30),'MT':(-15.60,-56.10),'MS':(-20.47,-54.62),
'MG':(-19.93,-43.94),'PA':(-1.46,-48.49),'PB':(-7.12,-34.86),
'PR':(-25.43,-49.27),'PE':(-8.05,-34.87),'PI':(-5.09,-42.81),
'RJ':(-22.90,-43.20),'RN':(-5.79,-35.21),'RS':(-30.03,-51.23),
'RO':(-8.76,-63.90),'RR':(2.82,-60.67),'SC':(-27.59,-48.55),
'SP':(-23.55,-46.63),'SE':(-10.91,-37.07),'TO':(-10.18,-48.33)}
C_PRIMARY='#23617D'; C_SECONDARY='#D68952'; C_GREEN='#287C73'

st.set_page_config(
    page_title='SRAG Brasil | Observatório de Vírus Respiratórios',
    page_icon='🫁', layout='wide', initial_sidebar_state='expanded'
)
st.markdown('''<style>
/* Identidade editorial: legível no tema claro ou escuro. */
.block-container {padding-top:1.25rem;max-width:1510px;padding-bottom:2.5rem}
[data-testid="stSidebar"] {border-right:1px solid rgba(122,149,164,.25)}
h1,h2,h3 {letter-spacing:-.025em}
.srag-hero {padding:1.35rem 1.6rem 1.2rem;border-radius:16px;
 background:linear-gradient(115deg,#123b50 0%,#155a72 68%,#18737d 100%);
 border:1px solid #396d80;color:#f7fbff;
 box-shadow:0 6px 25px rgba(18,48,65,.10);margin:.15rem 0 .7rem}
.srag-eyebrow {font-size:.71rem;letter-spacing:.13em;text-transform:uppercase;
 font-weight:750;color:#bde0e9;margin-bottom:.4rem}
.srag-title {font-size:clamp(1.5rem,2.4vw,2.15rem);font-weight:750;
 letter-spacing:-.035em;line-height:1.2;margin:0 0 .35rem}
.srag-subtitle {color:#e2eef2;font-size:.95rem;line-height:1.6;max-width:1000px}
.srag-meta {display:flex;flex-wrap:wrap;gap:.45rem;margin-top:1rem}
.srag-meta span {border:1px solid rgba(212,238,243,.38);border-radius:20px;
 padding:.22rem .65rem;color:#e7f4f6;font-size:.75rem}
.srag-credits {border-left:3px solid #24869c;padding:.65rem 1rem;
 background:rgba(116,166,186,.08);border-radius:0 10px 10px 0;
 margin:.35rem 0 .55rem;line-height:1.52;font-size:.87rem}
.srag-credits strong {font-weight:750}
.srag-credits a {color:inherit;text-decoration:underline;text-decoration-color:#48a2bb;text-underline-offset:3px}
.srag-source {font-size:.83rem;opacity:.86;line-height:1.58;padding:0 0 .2rem}
.srag-source a {color:inherit;text-decoration:underline;text-underline-offset:3px}
.srag-kpi {min-height:114px;padding:1rem 1.05rem;border-radius:13px;
 color:#f9fcff!important;border:1px solid #2a556d;
 background:linear-gradient(155deg,#143448,#1b5269);box-shadow:0 3px 10px rgba(9,33,49,.09)}
.srag-kpi .kpi-label {color:#c6e1e9!important;font-size:.83rem;line-height:1.3;
 font-weight:650;min-height:2.1em}
.srag-kpi .kpi-value {color:#fff!important;font-size:clamp(1.4rem,2vw,2rem);
 font-weight:750;letter-spacing:-.035em;font-variant-numeric:tabular-nums;
 line-height:1.28;margin-top:.15rem}
.srag-kpi .kpi-detail {color:#d1e5eb!important;font-size:.72rem;margin-top:.25rem}
[data-testid="stMetric"] {background:#143448!important;border:1px solid #2a556d;
 border-radius:13px!important;padding:15px!important}
[data-testid="stMetric"] [data-testid="stMetricLabel"] * {color:#c6e1e9!important;font-weight:650!important}
[data-testid="stMetric"] [data-testid="stMetricValue"] * {color:#fff!important}
[data-testid="stMetric"] [data-testid="stMetricDelta"] * {color:#d1e5eb!important}
[data-testid="stPlotlyChart"] {border:1px solid rgba(130,154,167,.14);border-radius:12px;padding:.3rem}
@media(max-width:800px) {.srag-hero {padding:1.05rem}.srag-title{font-size:1.55rem}}
</style>''', unsafe_allow_html=True)


def kpi(label: str, value: str, detail: str = '') -> None:
    """Cartão com contraste fixo, inclusive no tema escuro do navegador."""
    from html import escape
    extra = f'<div class="kpi-detail">{escape(detail)}</div>' if detail else ''
    st.markdown(
        '<div class="srag-kpi">'
        f'<div class="kpi-label">{escape(label)}</div>'
        f'<div class="kpi-value">{escape(str(value))}</div>{extra}</div>',
        unsafe_allow_html=True,
    )


def header(meta: dict, available_years: list[int]) -> None:
    """Créditos mantidos conforme o dashboard Orthoherpes da autora."""
    from html import escape
    start = min(available_years)
    end = max(available_years)
    snapshot = str(meta.get('gerado_em_utc', 'não informada'))[:10]
    status = 'Série 2019–2026 disponível' if meta.get('completo_2019_2026') else 'Base parcial'
    st.markdown(f'''
<div class="srag-hero">
  <div class="srag-eyebrow">Vigilância epidemiológica · Brasil</div>
  <div class="srag-title">Observatório de Vírus Respiratórios</div>
  <div class="srag-subtitle">Síndrome Respiratória Aguda Grave (SRAG) ·
  Análise de notificações, agentes virais, distribuição espacial, perfil epidemiológico
  e evolução temporal no território brasileiro.</div>
  <div class="srag-meta"><span>Fonte: SIVEP-Gripe / Ministério da Saúde</span>
  <span>Arquivos: {start}–{end}</span><span>{status}</span>
  <span>Preparação: {escape(snapshot)}</span></div>
</div>''', unsafe_allow_html=True)
    st.markdown('''
<div class="srag-credits"><strong>Idealizado por Sara Cândida Ferreira dos Santos</strong>
  · Mestranda em Bioinformática – UFMG<br>
  Bióloga – Universidade Federal de Minas Gerais · Técnica em Biotecnologia – COLTEC/UFMG<br>
  <a href="http://lattes.cnpq.br/5384262726323885" target="_blank">Currículo Lattes</a>
  &nbsp;·&nbsp; <a href="https://www.linkedin.com/in/sara-cândida-santos/" target="_blank">LinkedIn</a>
  &nbsp;·&nbsp; <a href="mailto:saracandida@ufmg.br">Contato</a>
</div>''', unsafe_allow_html=True)
    st.markdown('''
<div class="srag-source"><strong>Sobre a base de dados.</strong>
O <strong>SIVEP-Gripe</strong> (Sistema de Informação da Vigilância Epidemiológica da Gripe)
reúne registros da vigilância de <strong>SRAG hospitalizada e de óbitos por SRAG, independentemente de hospitalização</strong>.
Os dados oficiais divulgados pelo Ministério da Saúde permitem explorar informações demográficas,
clínicas, laboratoriais e de desfecho. Este painel utiliza exclusivamente arquivos públicos de SRAG
já tratados e agregados para consulta; não representa todos os casos de infecção respiratória no país.
<a href="https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026" target="_blank">Fonte: Portal de Dados Abertos do SUS</a>.
</div>''', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def manifest():
    return json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))

@st.cache_data(show_spinner='Abrindo tabelas agregadas...')
def load_all(years:tuple[int,...])->pd.DataFrame:
    df=[]
    for year in years:
        p=DATA/f'cubo_srag_{year}.csv.gz'
        if not p.exists():continue
        d=pd.read_csv(p,compression='gzip',low_memory=False,
                      dtype={'uf':'string','sexo':'string','faixa_etaria':'string'})
        df.append(d)
    return pd.concat(df,ignore_index=True) if df else pd.DataFrame()

@st.cache_data(show_spinner=False)
def geojson():
    p=DATA/'malha_uf.geojson'
    if not p.exists():return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return None

def number(x):return f'{int(x):,}'.replace(',','.')
def percent(n,d):return f'{100*float(n)/float(d):.1f}%'.replace('.',',') if d else '—'
def chart(fig, height=400):
    fig.update_layout(font_family='Arial',font_size=12,height=height,
         paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
         margin=dict(l=4,r=4,t=40,b=15),legend_title_text='')
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False,'scrollZoom':False})

def summarize(df,groupby):
    if df.empty:return pd.DataFrame()
    fields=[c for c in df.columns if c not in ['ano','semana','uf','sexo','faixa_etaria']]
    return df.groupby(groupby,observed=True,dropna=False,sort=False)[fields].sum().reset_index()

def metric(df,col):return int(df[col].sum()) if col in df else 0

def agent_col(agent):return 'notificacoes' if agent=='todos' else f'v_{agent}'

def scoping(df,agent):return metric(df,agent_col(agent))

def title(t,subtitle):
    st.header(t)
    st.caption(subtitle)

def no_rows(df):
    if df.empty:
        st.info('Não existem dados neste recorte. Altere os filtros na barra lateral.')
        return True
    return False

def overall(df,focus):
    title('Visão geral','Indicadores exploratórios de notificações de SRAG; um arquivo oficial por ano epidemiológico.')
    n=metric(df,'notificacoes'); sel=scoping(df,focus)
    c1,c2,c3,c4=st.columns(4)
    with c1:kpi('Notificações SRAG',number(n),'Registros no recorte')
    with c2:kpi('Agente selecionado' if focus!='todos' else 'Com ≥1 marcador viral',number(sel if focus!='todos' else metric(df,'com_deteccao')),'Detecção registrada')
    with c3:kpi('Óbitos por SRAG',number(metric(df,'obitos_srag') if focus=='todos' else metric(df,f'obito_{focus}')),'Evolução = 2')
    with c4:kpi('UTI registrada',number(metric(df,'uti') if focus=='todos' else metric(df,f'uti_{focus}')),'UTI = 1')
    if no_rows(df):return
    a,b=st.columns([1.1,1],gap='large')
    with a:
        d=pd.DataFrame([{'Agente':name,'Registros':metric(df,'v_'+key)} for key,name in VIRUSES.items()])
        d=d.sort_values('Registros').tail(9)
        fig=px.bar(d,x='Registros',y='Agente',orientation='h',text='Registros',color_discrete_sequence=[C_PRIMARY])
        fig.update_traces(textposition='outside',cliponaxis=False,texttemplate='%{x:,.0f}')
        fig.update_layout(title='Marcadores positivos por agente viral',margin=dict(l=8,r=110,t=40,b=15))
        fig.update_xaxes(range=[0,max(d['Registros'].max(),1)*1.23])
        chart(fig,465)
    with b:
        summary=summarize(df,['ano','semana'])
        summary=summary[summary['semana'].between(1,53)].sort_values(['ano','semana'])
        summary['período']=summary['ano'].astype(str)+'-SE'+summary['semana'].astype(str).str.zfill(2)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=summary['período'],y=summary['notificacoes'],name='Todas as notificações',mode='lines',line_color=C_PRIMARY))
        fig.add_trace(go.Scatter(x=summary['período'],y=summary[agent_col(focus)] if focus!='todos' else summary['com_deteccao'],
                                 name=VIRUSES.get(focus,'Com detecção viral'),mode='lines',line_color=C_SECONDARY))
        fig.update_layout(title='Distribuição por semana epidemiológica',xaxis_title='Ano – SE',yaxis_title='Notificações',hovermode='x unified',xaxis=dict(type='category',nticks=13,tickangle=-35),legend=dict(orientation='h',y=1.16,x=0))
        chart(fig,465)
    st.caption('Marcadores não são categorias mutuamente exclusivas. Resultado ausente não significa teste negativo. Não equivale a prevalência, incidência ou positividade entre testados.')

def virus_page(df,focus):
    title('Agentes virais','Detecções registradas no mesmo sistema de vigilância; não inferir espécie viral exclusivamente pela classificação final.')
    if no_rows(df):return
    counts=pd.DataFrame([{'agente':key,'Agente':label,'Registros':metric(df,'v_'+key)} for key,label in VIRUSES.items()]).sort_values('Registros',ascending=False)
    kpi('Notificações com ≥2 grupos virais detectados',number(metric(df,'codeteccoes')),'Marcadores não exclusivos')
    a,b=st.columns([1.25,1])
    with a:
        fig=px.bar(counts,x='Agente',y='Registros',text='Registros',color_discrete_sequence=[C_PRIMARY]);fig.update_xaxes(tickangle=-27)
        chart(fig,460)
    with b:
        st.dataframe(counts[['Agente','Registros']],use_container_width=True,hide_index=True,height=430)
    choice=st.selectbox('Detalhar por faixa etária',list(VIRUSES),index=list(VIRUSES).index(focus) if focus!='todos' else 0,format_func=lambda v:VIRUSES[v])
    a=summarize(df,['faixa_etaria'])
    a['faixa_etaria']=pd.Categorical(a.faixa_etaria,categories=AGES,ordered=True)
    a=a.sort_values('faixa_etaria')
    fig=px.bar(a,x='faixa_etaria',y='v_'+choice,
               labels={'faixa_etaria':'Faixa etária','v_'+choice:'Notificações com detecção'},color_discrete_sequence=[C_GREEN],text='v_'+choice)
    chart(fig,380)
    st.caption('Codetecção: coexistência de marcadores em uma notificação; não necessariamente coinfecção ativa.')

def trend_page(df,focus):
    title('Séries temporais','Notificações por semana epidemiológica (SEM_PRI) e marcadores laboratoriais; 2019–2026.')
    if no_rows(df):return
    agg=summarize(df,['ano','semana'])
    agg=agg[agg.semana.between(1,53)].sort_values(['ano','semana']).copy()
    if agg.empty:
        st.info('Nenhuma semana válida no período selecionado.')
        return
    agg['Ano (categoria)']=agg['ano'].astype(str)
    agg['Ano – SE']=agg['ano'].astype(str)+'-SE'+agg['semana'].astype(str).str.zfill(2)
    tab1,tab2,tab3=st.tabs(['Temporadas sobrepostas','Série cronológica','Série temporal por agente'])
    with tab1:
        graph=px.line(agg,x='semana',y=agent_col(focus),color='Ano (categoria)',markers=False,
            labels={'semana':'Semana epidemiológica','ano':'Ano','notificacoes':'Notificações',f'v_{focus}':'Detecções'},
            title='Comparação das semanas entre anos')
        graph.update_layout(hovermode='x unified',xaxis=dict(dtick=4))
        chart(graph,465)
        st.caption('Comparações entre temporadas são influenciadas por mudanças de vigilância, testagem e preenchimento, especialmente após 2020.')
    with tab2:
        fig=px.line(agg,x='Ano – SE',y=agent_col(focus),color_discrete_sequence=[C_PRIMARY],
                    title='Notificações ou detecções por período')
        fig.update_layout(xaxis=dict(type='category',nticks=15,tickangle=-40),hovermode='x unified',
                          xaxis_title='Ano e semana epidemiológica',yaxis_title='Registros')
        chart(fig,465)
    with tab3:
        st.markdown('**Compare a evolução temporal de diferentes agentes virais.**')
        defaults=[focus] if focus!='todos' else ['influenza','vsr','sars_cov_2']
        selected=st.multiselect('Alvos virais',list(VIRUSES),default=defaults,
                                format_func=lambda k:VIRUSES[k],key='series_agentes')
        chartmode=st.radio('Forma de comparação',['Linha do tempo contínua','Temporadas sobrepostas'],
                           horizontal=True,key='series_modo')
        if not selected:
            st.info('Selecione pelo menos um alvo viral.')
        else:
            labelmap={f'v_{k}':v for k,v in VIRUSES.items()}
            melted=agg.melt(id_vars=['ano','semana','Ano – SE'],value_vars=[f'v_{k}' for k in selected],
                            var_name='Alvo',value_name='Detecções')
            melted['Alvo']=melted['Alvo'].map(labelmap)
            if chartmode=='Linha do tempo contínua':
                plot=px.line(melted,x='Ano – SE',y='Detecções',color='Alvo',
                             title='Detecções por vírus e semana epidemiológica')
                plot.update_layout(xaxis=dict(type='category',nticks=17,tickangle=-40),
                                   hovermode='x unified',legend=dict(orientation='h',y=1.13,x=0))
                chart(plot,525)
            else:
                single=st.selectbox('Alvo para comparar os anos',selected,
                                    format_func=lambda x:VIRUSES[x],key='series_foco_ano')
                one=agg[['ano','semana',f'v_{single}']].rename(columns={f'v_{single}':'Detecções'}).copy()
                one['Ano']=one.ano.astype(str)
                plot=px.line(one,x='semana',y='Detecções',color='Ano',
                             title=VIRUSES[single]+' — temporadas por ano')
                plot.update_layout(xaxis=dict(dtick=4),hovermode='x unified')
                chart(plot,470)
            st.caption('Uma notificação pode ter mais de um marcador positivo. As linhas não representam incidência populacional nem positividade entre testados.')
            selected_col=[f'v_{k}' for k in selected]
            yearly=agg.groupby('ano',observed=True)[selected_col].sum().reset_index().rename(columns=labelmap)
            st.dataframe(yearly,hide_index=True,use_container_width=True)
            st.download_button('Exportar série semanal por agente (CSV)',
                agg[['ano','semana',*selected_col]].to_csv(index=False).encode('utf-8-sig'),
                'srag_serie_por_agente.csv','text/csv')
    yr=summarize(df,['ano'])[['ano','notificacoes','com_deteccao','obitos_srag']]
    with st.expander('Resumo anual dos registros'):
        st.dataframe(yr.sort_values('ano'),hide_index=True,use_container_width=True)

def geography(df,focus, selected_ufs, municipal_data, year_scope):
    title('Distribuição geográfica',
          'Distribuição de notificações por residência. Brasil: UFs (2019–2026); MT/MS: municípios (2023–2026). Valores absolutos.')
    # Mudança de escala: somente MT e/ou MS selecionados => mapa municipal.
    # Os cubos nacionais não possuem município nem conservam cruzamentos
    # por semana, idade ou sexo na escala municipal. Nunca reaproveitar os
    # totais filtrados nacionais como se fossem totais municipais.
    municipio_ufs = {'MT','MS'}
    municipio_years = {2023,2024,2025,2026}
    if selected_ufs and set(selected_ufs).issubset(municipio_ufs):
        mapa_anos = sorted(set(year_scope).intersection(municipio_years))
        if mapa_anos and not municipal_data.empty:
            mapa = municipal_data[municipal_data.ano.isin(mapa_anos)]
            st.caption('**Visualização municipal ampliada:** '+', '.join(selected_ufs)
                       +' · anos '+', '.join(map(str,mapa_anos))
                       +'. As contagens por município são anuais; os filtros de sexo, idade'
                       +' e semana NÃO se aplicam a este mapa.')
            if len(mapa_anos)<len(set(year_scope)):
                st.info('O detalhamento municipal cobre apenas 2023–2026. '
                        'Os anos 2019–2022 permanecem disponíveis no mapa estadual, '
                        'quando selecionados sem restringir a MT/MS.')
            if municipal_map(mapa, list(selected_ufs), focus, str(DATA), height=690):
                return
        else:
            st.info('O mapa municipal está disponível para 2023–2026. '
                    'Selecione ao menos um desses anos ou consulte o mapa estadual abaixo.')
    if no_rows(df):return
    a=summarize(df,['uf'])
    a=a[a.uf.isin(CAPITALS)].copy().sort_values(agent_col(focus),ascending=False)
    if a.empty:
        st.info('Nenhuma UF identificada para o recorte.');return
    a['Indicador']=a[agent_col(focus)]
    a['UF']=a['uf']
    a['lat']=a.uf.map({k:v[0] for k,v in CAPITALS.items()})
    a['lon']=a.uf.map({k:v[1] for k,v in CAPITALS.items()})
    st.caption('Indicador no mapa: '+(VIRUSES[focus] if focus!='todos' else 'Todas as notificações de SRAG'))
    map_base=st.radio('Base cartográfica',['Com fundo cartográfico','Sem fundo externo'],horizontal=True,key='mapa_estilo_geografia')
    c1,c2=st.columns([1.7,0.85],gap='large')
    with c1:
        features=geojson()
        used_polygons=False
        if features and len(features.get('features',[]))==27:
            prop=features['features'][0].get('properties',{})
            key=next((x for x in ('sigla','SIGLA','uf','UF') if x in prop),None)
            if key:
                if geometry_valid(features,key):
                    # MapLibre: todas as 27 UFs visíveis, sem fitbounds instável.
                    # Filtra os polígonos e centraliza automaticamente em UFs selecionadas.
                    selected_codes=set(a['uf'].astype(str))
                    selected_geo={'type':'FeatureCollection','features':[
                        ft for ft in features['features'] if str(ft['properties'][key]) in selected_codes]}
                    fig=choropleth_map(
                        a,selected_geo,code_col='uf',id_prop=key,
                        name_col='UF',value_col='Indicador',scope='BR',
                        auto_camera=True,style='carto-positron' if map_base=='Com fundo cartográfico' else 'white-bg')
                    chart(fig,635)
                    used_polygons=True
        if not used_polygons:
            # MapLibre com mosaicos de mapa é mais legível do que scatter_geo sem malha.
            # São pontos representativos da UF, NÃO coordenadas de pacientes.
            fig=px.scatter_map(
                a,lat='lat',lon='lon',size='Indicador',color='Indicador',
                hover_name='UF',hover_data={'notificacoes':':,','Indicador':':,','lat':False,'lon':False},
                map_style='open-street-map',center={'lat':-15.3,'lon':-53.1},zoom=2.9,
                size_max=40,color_continuous_scale=['#7cb5c9','#155a72','#0c394f']
            )
            fig.update_traces(marker={'opacity':.82})
            fig.update_layout(coloraxis_colorbar=dict(title='Registros',len=.72))
            chart(fig,620)
            st.caption('Mapa de apoio: cada círculo foi posicionado na capital para representar a UF; as coordenadas não correspondem aos locais dos casos. A visualização com polígonos depende de `data/malha_uf.geojson`. O mapa base utiliza mosaicos cartográficos online.')
    with c2:
        shown=a.sort_values('Indicador').tail(15)
        fig=px.bar(shown,x='Indicador',y='UF',orientation='h',text='Indicador',
                   color_discrete_sequence=[C_PRIMARY],title='15 UFs com mais registros')
        fig.update_traces(textposition='outside',cliponaxis=False)
        fig.update_layout(xaxis_title='Notificações',yaxis_title='',margin=dict(l=2,r=32,t=50,b=15))
        chart(fig,620)
    st.subheader('Tabela por unidade da federação')
    st.dataframe(a[['UF','notificacoes','Indicador','obitos_srag']].sort_values('Indicador',ascending=False),
                 hide_index=True,use_container_width=True)
    st.caption('A maior quantidade de notificações não significa necessariamente maior risco: as comparações dependem de população, intensidade de testagem e acesso aos serviços de saúde.')

def epidemiology(df,focus):
    title('Perfil epidemiológico','Distribuição das notificações por sexo, idade, classificação final e desfechos registrados.')
    if no_rows(df):return
    field=agent_col(focus)
    a,b=st.columns(2)
    with a:
        g=summarize(df,['faixa_etaria']);g['faixa_etaria']=pd.Categorical(g.faixa_etaria,categories=AGES,ordered=True)
        g=g.sort_values('faixa_etaria')
        fig=px.bar(g,x='faixa_etaria',y=field,labels={'faixa_etaria':'Idade',field:'Notificações'},color_discrete_sequence=[C_PRIMARY],title='Faixa etária');fig.update_xaxes(tickangle=-25)
        chart(fig,400)
    with b:
        s=summarize(df,['sexo']);fig=px.pie(s,names='sexo',values=field,hole=.48,color_discrete_sequence=[C_PRIMARY,C_SECONDARY,C_GREEN],title='Sexo')
        chart(fig,400)
    st.subheader('Classificação final da SRAG')
    count=pd.DataFrame([{'Classificação':label,'Registros':metric(df,f'classe_{k}')} for k,label in CLASS.items()])
    fig=px.bar(count,x='Classificação',y='Registros',text='Registros',color_discrete_sequence=[C_PRIMARY]);chart(fig,355)

    if all(col in df.columns for col in RESOLVED_CLASS2):
        st.subheader('Detalhamento dos registros classificados como “Outro vírus respiratório”')
        resolved = pd.DataFrame([{'Categoria resolvida':label,'Registros':metric(df,key)} for key,label in RESOLVED_CLASS2.items()])
        resolved = resolved[resolved['Registros']>0].sort_values('Registros',ascending=False)
        if not resolved.empty:
            fig=px.bar(resolved,x='Categoria resolvida',y='Registros',text='Registros',color_discrete_sequence=[C_SECONDARY])
            fig.update_xaxes(tickangle=-25)
            chart(fig,365)
            st.caption('Esse detalhamento só redistribui os casos já classificados como “Outro vírus respiratório” com base nos marcadores laboratoriais positivos registrados na mesma notificação.')
    else:
        st.info('Para detalhar a categoria “Outro vírus respiratório”, reprocese a base com a versão atualizada de `construir_base.py`.')

    c1,c2,c3=st.columns(3)
    with c1:kpi('Hospitalização registrada',number(metric(df,'hospitalizados')),'Campo HOSPITAL = 1')
    with c2:kpi('UTI registrada',number(metric(df,'uti') if focus=='todos' else metric(df,f'uti_{focus}')),'Campo UTI = 1')
    with c3:kpi('Óbito por SRAG',number(metric(df,'obitos_srag') if focus=='todos' else metric(df,f'obito_{focus}')),'Evolução = 2')
    st.caption('Indicadores de desfecho não foram ajustados por atraso de encerramento; estimativas de letalidade exigem análise específica e denominadores apropriados. Classificação final é distinta dos marcadores laboratoriais.')

def explorer(df,focus):
    title('Explorador de dados','Tabela agregada exportável; nenhuma linha representa um paciente individual.')
    group_map={'Ano':'ano','Semana epidemiológica':'semana','UF':'uf','Sexo':'sexo','Faixa etária':'faixa_etaria'}
    cols=st.multiselect('Agrupar resultados por',list(group_map),default=['Ano','UF'])
    if not cols:
        st.info('Selecione pelo menos um agrupamento.');return
    if no_rows(df):return
    out=summarize(df,[group_map[c] for c in cols]);out=out.sort_values([group_map[c] for c in cols])
    st.caption(f'{number(len(out))} combinações agregadas | {number(metric(df,"notificacoes"))} notificações nos filtros')
    st.dataframe(out,use_container_width=True,hide_index=True,height=470)
    st.download_button('Exportar tabela CSV',data=out.to_csv(index=False).encode('utf-8-sig'),
                       file_name='srag_brasil_agregado.csv',mime='text/csv')

def methods(meta):
    title('Métodos e auditoria','Origem, recortes temporais e limitações de interpretação do snapshot publicado.')
    st.write('**Fonte exclusiva:** SIVEP-Gripe — Sistema de Informação da Vigilância Epidemiológica da Gripe, do Ministério da Saúde. Os dados públicos de SRAG registram casos hospitalizados e óbitos por SRAG independentemente de internação. O painel não utiliza e-SUS Notifica nem SG Sentinela.')
    st.link_button('Abrir coleção oficial',meta.get('colecao_oficial','https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026'))
    st.markdown('''
**Interpretação dos indicadores**

- Uma notificação não equivale a uma pessoa única, e o processamento **não remove automaticamente duplicações internas** do SIVEP-Gripe.
- Os anos de referência são os **anos dos arquivos oficiais**; a semana é `SEM_PRI` (início dos sintomas). Semana zero indica campo ausente/inválido.
- Um vírus é contado se pelo menos um campo laboratorial correspondente está codificado como `1`. Não se infere positividade de `CLASSI_FIN`.
- A ausência de marcador positivo **não** significa teste negativo ou resultado não detectável.
- Óbito por SRAG usa `EVOLUCAO=2`. Óbito por outras causas não entra no numerador; campos não preenchidos permanecem desconhecidos.
- Codetecção corresponde a mais de um grupo viral marcado como positivo na mesma notificação.
- O detalhamento de `CLASSI_FIN=2` utiliza os marcadores laboratoriais correspondentes; esse agrupamento adicional não modifica a classificação final original nem identifica necessariamente a etiologia com certeza.
- Bases de 2019 a 2024 têm cobertura diferente da vigilância após a pandemia. Comparações precisam considerar alterações de definição, testagem e vigilância.
- Dados de 2025 e 2026 são sujeitos a revisão; o dashboard **não se atualiza sozinho**. Reprocessar e publicar novos agregados para mudar o snapshot.
- Arquivos de publicação são **agregados**, sem nomes, datas diárias ou números de notificação. O complemento municipal inclui município e ano, sem sexo, idade ou semana; os gráficos temporais de maior escala retêm estratos epidemiológicos. Agregação **não é garantia formal de anonimização**; avaliar ocultação de células pequenas antes de publicar.
- O complemento 2023–2026 foi construído separadamente a partir dos CSVs oficiais, sem alterar ou somar novamente os cubos nacionais.
- Município por `CO_MUN_RES` (residência); malhas municipais do IBGE. Não é município da coleta, atendimento ou notificação.
- Influenza A e B são distinguidas por tipagem laboratorial positiva, não exclusivamente por `CLASSI_FIN`. Subtipos H1N1/H3N2 e linhagens Victoria/Yamagata são contados apenas com PCR positivo e subtipo/linhagem informados.
- Na comparação mensal, mês derivado de `DT_SIN_PRI`; mês 0 indica campo inválido/ano incompatível. Na análise semanal, utilizar `SEM_PRI`.
''')
    a=[]
    for year,item in sorted(meta.get('anos',{}).items()):
        a.append({'Ano':int(year),'Notificações':item.get('notificacoes',0),
                  'Arquivo original':item.get('nome_arquivo_original',''),
                  'Origem':item.get('origem',''),
                  'Grupos agregados':item.get('grupos',0),
                  'SHA256 arquivo agregado':item.get('sha256_agregado','')})
    st.dataframe(pd.DataFrame(a),use_container_width=True,hide_index=True)
    with st.expander('Metadados completos, SHA256 e arquivos originais'):
        st.json(meta,expanded=False)

if not (DATA/'manifest.json').exists():
    st.error('Dados preparados não encontrados. Execute localmente `python construir_base.py --todos`, inclua a pasta data/ no GitHub e publique.')
    st.stop()
META=manifest()
available=[int(y) for y in META.get('anos_disponiveis',[]) if (DATA/f'cubo_srag_{y}.csv.gz').exists()]
if not available:
    st.error('Nenhum arquivo de dados foi encontrado. Rode `python construir_base.py --todos`.');st.stop()

with st.sidebar:
    st.markdown('### Observatório SRAG · Brasil')
    st.caption('Ministério da Saúde · SIVEP-Gripe')
    page=st.radio('Navegação',PAGES)
    st.divider()
    st.markdown('#### Filtros globais')
    if st.button('Limpar filtros',use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith('f_'):del st.session_state[k]
        st.rerun()

BASE_DATA=load_all(tuple(available))
if BASE_DATA.empty:
    st.error('Arquivos agregados vazios');st.stop()
with st.sidebar:
    years=st.multiselect('Anos epidemiológicos',available,default=available,key='f_years')
    ufs=sorted(x for x in BASE_DATA.uf.dropna().unique() if x!='Não informado')
    ufs_sel=st.multiselect('UF de residência',ufs,key='f_ufs')
    sex_sel=st.multiselect('Sexo',sorted(BASE_DATA.sexo.dropna().unique()),key='f_sexo')
    age_sel=st.multiselect('Faixa etária',AGES,key='f_ages')
    week=st.slider('Semanas epidemiológicas (0 = não informada)',0,53,(0,53),key='f_weeks')
    focus=st.selectbox('Agente em foco',['todos',*VIRUSES],index=0,
                        format_func=lambda x:'Todos os registros' if x=='todos' else VIRUSES[x],key='f_focus')
    st.divider()
    st.caption('Selecione MT ou MS em UF de residência para exibir municípios na página Geografia.')
    st.caption('Snapshot offline: dados previamente tratados e versionados no GitHub.')
    st.caption('Última preparação: '+str(META.get('gerado_em_utc','não informada'))[:10])

filtered=BASE_DATA[BASE_DATA.ano.isin(years)] if years else BASE_DATA.iloc[0:0].copy()
filtered=filtered[filtered.semana.between(*week)]
if ufs_sel:filtered=filtered[filtered.uf.isin(ufs_sel)]
if sex_sel:filtered=filtered[filtered.sexo.isin(sex_sel)]
if age_sel:filtered=filtered[filtered.faixa_etaria.isin(age_sel)]

# Complementos independentes não sobrescrevem os cubos nacionais.
CO_MUN = load_complement(str(DATA),tuple(available),'municipios')
if not CO_MUN.empty:
    CO_MUN = CO_MUN[CO_MUN.ano.isin(years)]
CO_TIME = apply_filters(load_complement(str(DATA),tuple(available),'temporal'),
                        years,week,sex_sel,age_sel)
header(META,available)
if not META.get('completo_2019_2026'):
    st.warning(f"**BASE PARCIAL:** anos disponíveis {', '.join(map(str,available))}. Para completar 2019–2026, execute `python construir_base.py --todos` e publique a pasta `data/` no GitHub.")
st.caption(f'**{number(metric(filtered,"notificacoes"))}** notificações após os filtros · arquivos disponíveis: {min(available)}–{max(available)} · atualização não automática')
st.divider()
if page==PAGES[0]:overall(filtered,focus)
elif page==PAGES[1]:virus_page(filtered,focus)
elif page==PAGES[2]:trend_page(filtered,focus)
elif page==PAGES[3]:geography(filtered,focus,ufs_sel,CO_MUN,years)
elif page==PAGES[4]:regional_page(filtered,CO_MUN,CO_TIME,years,ufs_sel,focus,str(DATA))
elif page==PAGES[5]:epidemiology(filtered,focus)
elif page==PAGES[6]:explorer(filtered,focus)
else:methods(META)
st.divider()
st.caption('Observatório SRAG Brasil · Fonte primária: Ministério da Saúde / SIVEP-Gripe · Indicadores baseados em notificações oficiais, não em incidência populacional · Idealização: Sara Cândida Ferreira dos Santos.')
