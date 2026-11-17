"""Tipagem INFA/INFB onde há informação laboratorial no snapshot publicado.

O cubo nacional histórico de 2019–2022 tem Influenza agregado, sem A/B.
A extração complementar 2023–2026 distingue A/B no Brasil, Centro-Oeste,
MT e MS. Não extrapolar para outras UFs nem colocar zeros em anos sem dados.
"""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import streamlit as st
from figuras_ui import chart

FIELDMAP={'influenza_a':'Influenza A','influenza_b':'Influenza B',
          'influenza_sem_tipo':'Influenza sem tipagem',
          'a_h1n1':'A(H1N1)pdm09','a_h3n2':'A(H3N2)',
          'b_victoria':'B/Victoria','b_yamagata':'B/Yamagata'}
COLOR={'Influenza A':'#23617D','Influenza B':'#D68952',
       'Influenza sem tipagem':'#8e9aa3'}


def scope_for_uf(selected_ufs):
    if not selected_ufs:
        return ['Brasil'],'Brasil'
    sel=set(selected_ufs)
    if sel=={'MT'}:
        return ['MT'],'Mato Grosso'
    if sel=={'MS'}:
        return ['MS'],'Mato Grosso do Sul'
    if sel=={'MT','MS'}:
        return ['MT','MS'],'Mato Grosso + Mato Grosso do Sul'
    if sel=={'MT','MS','GO','DF'}:
        return ['Centro-Oeste'],'Centro-Oeste'
    return [],''


def select_influenza(timeline:pd.DataFrame, selected_ufs:list[str]):
    scopes,label=scope_for_uf(selected_ufs)
    if timeline.empty or not scopes:
        return pd.DataFrame(),label
    data=timeline[timeline.escopo.isin(scopes)].copy()
    # Os escopos Brasil/CO/MT/MS são hierárquicos. Nunca somar Brasil a MT.
    return data,label


def counts(data:pd.DataFrame):
    if data.empty:return None
    return {key:int(data[key].sum()) for key in FIELDMAP if key in data}


def detail(timeline:pd.DataFrame, selected_ufs:list[str], *,
           expand:bool=False, include_chart:bool=True, include_age:bool=False,
           heading:str='Influenza A e B · tipagem laboratorial'):
    st.subheader(heading)
    data,region=select_influenza(timeline,selected_ufs)
    if data.empty:
        st.info('A distinção laboratorial entre Influenza A e B está disponível no complemento '
                '2023–2026 para Brasil, Centro-Oeste, MT e MS. Não há dados desagregados '
                'por outras UFs ou para 2019–2022 nos arquivos atualmente publicados.')
        return
    years=sorted(data.ano.unique().tolist())
    years_txt=', '.join(str(y) for y in years)
    st.caption(f'Escopo: **{region}** · anos com tipagem: **{years_txt}**. '
               'Os totais não representam todos os anos selecionados quando 2019–2022 estão ativos.')
    c=counts(data)
    a,b,c3=st.columns(3)
    with a: st.metric('Influenza A (INFA)',f'{c.get("influenza_a",0):,}'.replace(',','.'))
    with b: st.metric('Influenza B (INFB)',f'{c.get("influenza_b",0):,}'.replace(',','.'))
    with c3:st.metric('Influenza sem tipo',f'{c.get("influenza_sem_tipo",0):,}'.replace(',','.'))
    if include_chart:
        with st.expander('Comparar circulação de A e B',expanded=expand):
            sub=data[data.semana.between(1,53)]
            if sub.empty:
                st.info('Sem semanas válidas no recorte.')
            else:
                y=sub.groupby(['ano','semana'],observed=True)[['influenza_a','influenza_b']].sum().reset_index()
                y['Ano – SE']=y.ano.astype(str)+'-SE'+y.semana.astype(str).str.zfill(2)
                chartdata=y.melt(['ano','semana','Ano – SE'],value_vars=['influenza_a','influenza_b'],
                                 var_name='Agente',value_name='Detecções')
                chartdata['Agente']=chartdata['Agente'].map(FIELDMAP)
                fig=px.line(chartdata,x='Ano – SE',y='Detecções',color='Agente',
                            color_discrete_map=COLOR,
                            title=f'Influenza A e B por semana · {region}')
                fig.update_xaxes(type='category',nticks=13,tickangle=-30)
                chart(fig,390)
                st.download_button('Baixar série A/B em CSV',
                      data=y.to_csv(index=False).encode('utf-8-sig'),
                      file_name='influenza_A_B_semanal.csv',mime='text/csv')
    if include_age:
        by_age=data.groupby('faixa_etaria',observed=True)[['influenza_a','influenza_b']].sum().reset_index()
        long=by_age.melt('faixa_etaria',var_name='Agente',value_name='Detecções')
        long['Agente']=long['Agente'].map(FIELDMAP)
        fig=px.bar(long,x='faixa_etaria',y='Detecções',color='Agente',barmode='group',
                   title=f'Influenza A e B por faixa etária · {region}',color_discrete_map=COLOR)
        fig.update_xaxes(tickangle=-35)
        chart(fig,425)


def temporal_columns(agg:pd.DataFrame, timeline:pd.DataFrame,selected_ufs:list[str]):
    """Junta A/B por ano/semana sem fabricar zeros nos anos sem tipagem.

    Se a UF não estiver coberta pelo complemento, retorna NaN para A/B.
    """
    data, region=select_influenza(timeline,selected_ufs)
    agg=agg.copy()
    if data.empty:
        agg['influenza_a']=float('nan')
        agg['influenza_b']=float('nan')
        return agg, region
    y=data.groupby(['ano','semana'],observed=True)[['influenza_a','influenza_b']].sum().reset_index()
    agg=agg.merge(y,on=['ano','semana'],how='left',validate='one_to_one')
    return agg,region
