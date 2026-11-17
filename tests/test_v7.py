"""Regressões das correções V7: navegação, escala e mapa municipal."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from escala_municipal import escala
from mapas_geo import choropleth_map
from exportacao import mapa_png

ROOT = Path(__file__).resolve().parents[1]


def test_navegacao_sem_codeteccoes_e_sem_quadros_repetidos():
    code=(ROOT/'streamlit_app.py').read_text(encoding='utf-8')
    nav=code.split('PAGES=',1)[1].split('CAPITALS=',1)[0]
    assert 'Co-detecções' not in nav
    assert 'Influenza A e B' in nav
    assert 'influenza_detail(' not in code
    assert 'format_func=lambda x:extended[x]' in code


def test_escala_cores_tem_zero_e_preserva_empates():
    valores=np.array([0,0,1,1,2,4,15,304],dtype=float)
    v,t,labels=escala(valores,'Quantis')
    assert v[0] == 0 and v[1]==0
    assert v[2]==v[3]  # valores iguais não recebem cores diferentes
    assert all(a<=b for a,b in zip(v[2:],v[3:]))
    assert labels[0]=='0'
    assert len(t)==len(labels)
    for metodo in ('Raiz quadrada','Linear'):
        k,tk,lk=escala(valores,metodo)
        assert len(tk)==len(lk)
        assert k[0]==0 and k[-1]>k[4]


def test_mapa_municipal_cor_vs_valores_reais():
    geo=json.loads((ROOT/'data/malha_municipios_MT.geojson').read_text(encoding='utf-8'))
    tab=pd.read_csv(ROOT/'data/municipios_co_2026.csv.gz',dtype={'uf':'string','municipio':'string'})
    counts=tab[tab.uf.eq('MT')].groupby('municipio')['influenza_a'].sum().to_dict()
    df=pd.DataFrame([{'Código':str(ft['properties']['codigo_sivep']),
                      'Município':ft['properties']['nome'],
                      'Registros':int(counts.get(str(ft['properties']['codigo_sivep']),0))}
                     for ft in geo['features']])
    assert len(df)==141
    assert int(df.Registros.sum())==972
    df['Intensidade'],ticks,labels=escala(df['Registros'],'Quantis')
    fig=choropleth_map(df,geo,code_col='Código',id_prop='codigo_sivep',
         name_col='Município',value_col='Intensidade',
         extra_hover_cols={'Registros':':,'},legend_ticks=ticks,legend_labels=labels,
         auto_camera=True,scope='MT')
    assert len(fig.data[0].locations)==141
    assert 'Registros' in fig.data[0].hovertemplate
    assert len(fig.layout.coloraxis.colorbar.tickvals)>1
    img=mapa_png(geo,df,col_codigo='Código',id_prop='codigo_sivep',
                 escala_cor='Quantis',dpi=80)
    assert img[:8]==b'\x89PNG\r\n\x1a\n'
