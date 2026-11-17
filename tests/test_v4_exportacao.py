"""Valida resolução PNG e a correspondência exata das notificações municipais."""
import io
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from exportacao import mapa_png, figura_png

DATA=Path(__file__).resolve().parents[1]/'data'


def test_influenza_municipal_codigo_texto():
    data=pd.read_csv(DATA/'municipios_co_2026.csv.gz',compression='gzip',dtype={'municipio':'string'})
    mt=data[data.uf.eq('MT')]
    geo=json.loads((DATA/'malha_municipios_MT.geojson').read_text())
    codes={f['properties']['codigo_sivep'] for f in geo['features']}
    grouped=mt.groupby('municipio',observed=True)[['influenza_a','influenza_b']].sum()
    for col in ('influenza_a','influenza_b'):
        mapped=sum(int(grouped.loc[code,col]) for code in codes if code in grouped.index)
        known=sum(int(v) for key,v in grouped[col].items() if key!='Não informado')
        assert mapped==known
    assert sum(grouped['influenza_a'])==972  # fotografia 2026 do pacote


def test_dpi_real_png():
    data=pd.DataFrame({'Semana':[1,2,3],'A':[1,3,5]})
    fig=px.line(data,x='Semana',y='A')
    png=figura_png(fig,title='Teste de exportação',dpi=800)
    opened=Image.open(io.BytesIO(png))
    assert opened.width>=6000
    assert abs(opened.info['dpi'][0]-800)<.1


def test_mapa_imagem_valida():
    geo=json.loads((DATA/'malha_municipios_MS.geojson').read_text())
    codes=[f['properties']['codigo_sivep'] for f in geo['features']]
    vals=pd.DataFrame({'Código':codes,'Registros':range(len(codes))})
    png=mapa_png(geo,vals,titulo='Mato Grosso do Sul',dpi=120)
    opened=Image.open(io.BytesIO(png))
    assert opened.width>800
    assert abs(opened.info['dpi'][0]-120)<.1
