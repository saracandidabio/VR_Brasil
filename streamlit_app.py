"""Observatório SRAG Brasil: somente SIVEP-Gripe, dados offline preparados previamente."""
from __future__ import annotations
import io
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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
PAGES=['Visão geral','Agentes virais','Séries temporais','Distribuição geográfica',
       'Perfil epidemiológico','Explorador de dados','Métodos e auditoria']
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

st.set_page_config(page_title='SRAG Brasil | Observatório de Vírus Respiratórios',page_icon='🫁',layout='wide')
st.markdown('''<style>
.block-container {padding-top:1.55rem;max-width:1460px}
[data-testid="stMetric"] {background:#f1f6f8;border:1px solid #dce9ee;border-radius:10px;padding:14px}
[data-testid="stMetricValue"] {color:#123d52}
[data-testid="stSidebar"] {border-right:1px solid #e5ebef}
.captioned {color:#587080;font-size:.9rem}
</style>''',unsafe_allow_html=True)

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
    with c1:st.metric('Notificações SRAG',number(n))
    with c2:st.metric('Agente selecionado' if focus!='todos' else 'Com ≥1 marcador viral',number(sel if focus!='todos' else metric(df,'com_deteccao')))
    with c3:st.metric('Óbitos por SRAG (evolução=2)',number(metric(df,'obitos_srag') if focus=='todos' else metric(df,f'obito_{focus}')))
    with c4:st.metric('UTI registrada',number(metric(df,'uti') if focus=='todos' else metric(df,f'uti_{focus}')))
    if no_rows(df):return
    a,b=st.columns([1.1,1],gap='large')
    with a:
        d=pd.DataFrame([{'Agente':name,'Registros':metric(df,'v_'+key)} for key,name in VIRUSES.items()])
        d=d.sort_values('Registros').tail(9)
        fig=px.bar(d,x='Registros',y='Agente',orientation='h',text='Registros',color_discrete_sequence=[C_PRIMARY])
        fig.update_traces(textposition='outside',cliponaxis=False)
        fig.update_layout(title='Marcadores positivos por agente viral')
        chart(fig,465)
    with b:
        summary=summarize(df,['ano','semana'])
        summary=summary[summary['semana'].between(1,53)].sort_values(['ano','semana'])
        summary['período']=summary['ano'].astype(str)+'-SE'+summary['semana'].astype(str).str.zfill(2)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=summary['período'],y=summary['notificacoes'],name='Todas as notificações',mode='lines',line_color=C_PRIMARY))
        fig.add_trace(go.Scatter(x=summary['período'],y=summary[agent_col(focus)] if focus!='todos' else summary['com_deteccao'],
                                 name=VIRUSES.get(focus,'Com detecção viral'),mode='lines',line_color=C_SECONDARY))
        fig.update_layout(title='Distribuição por semana epidemiológica',xaxis_title='Ano – SE',yaxis_title='Notificações',hovermode='x unified')
        chart(fig,465)
    st.caption('Marcadores não são categorias mutuamente exclusivas. Resultado ausente não significa teste negativo. Não equivale a prevalência, incidência ou positividade entre testados.')

def virus_page(df,focus):
    title('Agentes virais','Detecções registradas no mesmo sistema de vigilância; não inferir espécie viral exclusivamente pela classificação final.')
    if no_rows(df):return
    counts=pd.DataFrame([{'agente':key,'Agente':label,'Registros':metric(df,'v_'+key)} for key,label in VIRUSES.items()]).sort_values('Registros',ascending=False)
    st.metric('Notificações com ≥2 grupos virais detectados',number(metric(df,'codeteccoes')))
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
    title('Séries temporais','Anos epidemiológicos dos arquivos oficiais e semana de início dos sintomas (SEM_PRI).')
    if no_rows(df):return
    agg=summarize(df,['ano','semana'])
    agg=agg[agg.semana.between(1,53)].sort_values(['ano','semana'])
    agg['Ano (categoria)']=agg['ano'].astype(str)
    tab1,tab2=st.tabs(['Sobreposição das temporadas','Série cronológica'])
    with tab1:
        graph=px.line(agg,x='semana',y=agent_col(focus),color='Ano (categoria)',markers=False,
               labels={'semana':'Semana epidemiológica','ano':'Ano','notificacoes':'Notificações',f'v_{focus}':'Detecções'},
               title='Comparação das semanas entre anos')
        chart(graph,470)
        st.caption('Comparações entre temporadas são influenciadas por mudanças de vigilância, testagem e preenchimento, especialmente a partir de 2020.')
    with tab2:
        agg['Ano – SE']=agg['ano'].astype(str)+'-SE'+agg['semana'].astype(str).str.zfill(2)
        fig=px.bar(agg,x='Ano – SE',y=agent_col(focus),color_discrete_sequence=[C_PRIMARY],title='Notificações por período')
        chart(fig,450)
    yr=summarize(df,['ano'])[['ano','notificacoes','com_deteccao','obitos_srag']]
    st.dataframe(yr.sort_values('ano'),hide_index=True,use_container_width=True)

def geography(df,focus):
    title('Distribuição geográfica','UF de residência (SG_UF); contagens absolutas, sem ajuste para população.')
    if no_rows(df):return
    a=summarize(df,['uf'])
    a=a[a.uf.isin(CAPITALS)].copy().sort_values(agent_col(focus),ascending=False)
    a['Indicador']=a[agent_col(focus)]
    a['UF']=a['uf']
    a['lat']=a.uf.map({k:v[0] for k,v in CAPITALS.items()})
    a['lon']=a.uf.map({k:v[1] for k,v in CAPITALS.items()})
    c1,c2=st.columns([1.4,0.9],gap='large')
    with c1:
        # Polígonos UF (opcional) vêm dos dados preparados; caso contrário exibimos marcadores nas capitais.
        features=geojson()
        used=False
        if features:
            sample=features.get('features',[])
            if sample:
                prop=sample[0].get('properties',{})
                # Malha IBGE pode vir com sigla, SIGLA, UF ou nome da UF.
                key=next((x for x in ('sigla','SIGLA','uf','UF') if x in prop),None)
                if key:
                    fig=px.choropleth(a,geojson=features,locations='uf',featureidkey=f'properties.{key}',
                                      color='Indicador',hover_name='UF',hover_data={'notificacoes':True},color_continuous_scale='Blues')
                    fig.update_geos(fitbounds='locations',visible=False)
                    chart(fig,500);used=True
        if not used:
            fig=px.scatter_geo(a,lat='lat',lon='lon',size='Indicador',color='Indicador',
                               hover_name='UF',hover_data={'notificacoes':True,'lat':False,'lon':False},
                               projection='natural earth',size_max=45,color_continuous_scale='Blues')
            fig.update_geos(lataxis_range=[-35,6],lonaxis_range=[-76,-31],showland=True,landcolor='#eff3f4',
                            showcountries=True,countrycolor='#afbdc5',showcoastlines=False)
            chart(fig,500)
            st.caption('Marcadores estão posicionados nas capitais apenas para indicar as UFs; não são locais reais de casos. Para mapa por polígonos, a preparação pode incorporar malha UF.')
    with c2:
        fig=px.bar(a.sort_values('Indicador').tail(18),x='Indicador',y='UF',orientation='h',text='Indicador',color_discrete_sequence=[C_PRIMARY])
        chart(fig,500)
    st.dataframe(a[['UF','notificacoes','Indicador','obitos_srag']].sort_values('Indicador',ascending=False),hide_index=True,use_container_width=True)

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
    c1,c2,c3=st.columns(3)
    with c1:st.metric('Hospitalização (campo=1)',number(metric(df,'hospitalizados')))
    with c2:st.metric('UTI (campo=1)',number(metric(df,'uti') if focus=='todos' else metric(df,f'uti_{focus}')))
    with c3:st.metric('Óbito por SRAG (EVOLUCAO=2)',number(metric(df,'obitos_srag') if focus=='todos' else metric(df,f'obito_{focus}')))
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
    st.write('**Fonte exclusiva:** SIVEP-Gripe — SRAG. Dados oficiais nacionais publicados no Portal de Dados Abertos do SUS.')
    st.link_button('Abrir coleção oficial',meta.get('colecao_oficial','https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026'))
    st.markdown('''
**Interpretação dos indicadores**

- Uma notificação não equivale a uma pessoa única, e o processamento **não remove automaticamente duplicações internas** do SIVEP-Gripe.
- Os anos de referência são os **anos dos arquivos oficiais**; a semana é `SEM_PRI` (início dos sintomas). Semana zero indica campo ausente/inválido.
- Um vírus é contado se pelo menos um campo laboratorial correspondente está codificado como `1`. Não se infere positividade de `CLASSI_FIN`.
- A ausência de marcador positivo **não** significa teste negativo ou resultado não detectável.
- Óbito por SRAG usa `EVOLUCAO=2`. Óbito por outras causas não entra no numerador; campos não preenchidos permanecem desconhecidos.
- Codetecção corresponde a mais de um grupo viral marcado como positivo na mesma notificação.
- Bases de 2019 a 2024 têm cobertura diferente da vigilância após a pandemia. Comparações precisam considerar alterações de definição, testagem e vigilância.
- Dados de 2025 e 2026 são sujeitos a revisão; o dashboard **não se atualiza sozinho**. Reprocessar e publicar novos agregados para mudar o snapshot.
- Arquivos de publicação são **agregados**, sem nomes, datas diárias, números de notificação ou municípios. Agregação não é garantia formal de anonimização.
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
    st.caption('SIVEP-Gripe | fonte única')
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
    st.caption('Snapshot offline: dados previamente tratados e versionados no GitHub.')
    st.caption('Última preparação: '+str(META.get('gerado_em_utc','não informada'))[:10])

filtered=BASE_DATA[BASE_DATA.ano.isin(years)] if years else BASE_DATA.iloc[0:0].copy()
filtered=filtered[filtered.semana.between(*week)]
if ufs_sel:filtered=filtered[filtered.uf.isin(ufs_sel)]
if sex_sel:filtered=filtered[filtered.sexo.isin(sex_sel)]
if age_sel:filtered=filtered[filtered.faixa_etaria.isin(age_sel)]

st.title('Vigilância de vírus respiratórios no Brasil')
st.markdown('**Síndrome Respiratória Aguda Grave (SRAG)** · SIVEP-Gripe · painel epidemiológico exploratório')
if page=='Visão geral':
    st.caption('Painel de pesquisa construído a partir de dados públicos nacionais do Ministério da Saúde.')
if not META.get('completo_2019_2026'):
    st.warning(f"**BASE PARCIAL:** anos disponíveis {', '.join(map(str,available))}. Para completar 2019–2026, execute `python construir_base.py --todos` e publique a pasta `data/` no GitHub.")
st.caption(f'**{number(metric(filtered,"notificacoes"))}** notificações após os filtros · arquivos disponíveis: {min(available)}–{max(available)} · atualização não automática')
st.divider()
if page==PAGES[0]:overall(filtered,focus)
elif page==PAGES[1]:virus_page(filtered,focus)
elif page==PAGES[2]:trend_page(filtered,focus)
elif page==PAGES[3]:geography(filtered,focus)
elif page==PAGES[4]:epidemiology(filtered,focus)
elif page==PAGES[5]:explorer(filtered,focus)
else:methods(META)
st.divider()
st.caption('Fonte: Ministério da Saúde, SIVEP-Gripe/SRAG | Notificações e detecções laboratoriais não equivalem à incidência populacional. Consulte a metodologia.')
