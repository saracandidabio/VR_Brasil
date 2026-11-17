"""Testes da nova cartografia, sem acesso a internet e sem iniciar Streamlit."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from mapas_geo import geometry_valid, camera_from_polygons, choropleth_map

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))


def test_malhas_e_enquadramento():
    for filename, code, n in [('malha_uf.geojson','sigla',27),
                              ('malha_municipios_MT.geojson','codigo_sivep',141),
                              ('malha_municipios_MS.geojson','codigo_sivep',79)]:
        geo=load(filename)
        assert len(geo['features'])==n
        assert geometry_valid(geo,code)
        camera=camera_from_polygons(geo)
        assert -75 < camera['center']['lon'] < -34
        assert -34 < camera['center']['lat'] < 6
        assert 1.8 <= camera['zoom'] <= 8.5


def test_grafico_nacional_27_ufs():
    geo=load('malha_uf.geojson')
    df=pd.DataFrame([{'uf':f['properties']['sigla'],'Nome':f['properties']['sigla'],
                      'Registros':100+i} for i,f in enumerate(geo['features'])])
    fig=choropleth_map(df,geo,code_col='uf',id_prop='sigla',
                       name_col='Nome',value_col='Registros',scope='BR',auto_camera=True)
    assert fig.data[0].type=='choroplethmap'
    assert len(fig.data[0].locations)==27
    assert fig.data[0].featureidkey=='properties.sigla'
    assert fig.layout.map.zoom > 2


def test_municipios_por_codigo():
    geo=load('malha_municipios_MS.geojson')
    df=pd.DataFrame([{'codigo':f['properties']['codigo_sivep'],
                      'nome':f['properties']['nome'],'registros':100}
                     for f in geo['features']])
    fig=choropleth_map(df,geo,code_col='codigo',id_prop='codigo_sivep',
                       name_col='nome',value_col='registros',scope='MS')
    assert len(fig.data[0].locations)==79
    assert fig.data[0].type=='choroplethmap'
    assert fig.layout.map.zoom>4
