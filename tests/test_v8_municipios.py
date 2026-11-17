from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from preparar_municipios_brasil import municipal_flags,IBGE_PREFIX
from mapas_geo import choropleth_map,state_boundary_overlay
import json


def test_municipio_residencia_6digitos_e_sem_soma_dupla():
    raw=pd.DataFrame({
      'SG_UF':['GO','GO','MT','MS'],
      'CO_MUN_RES':['520870','5208701','510340','500270'],
      'POS_PCRFLU':['1','2','1','1'],
      'TP_FLU_PCR':['1','', '2','1'],
      'POS_AN_FLU':['2','2','2','2'],
      'EVOLUCAO':['1','2','1','1'],
      'UTI':['2','1','2','2'],
    },dtype='string')
    m=municipal_flags(raw,2026)
    assert m.loc[0,'municipio']=='520870'
    assert m.loc[1,'municipio']=='520870'
    assert m.loc[0,'influenza_a']==1
    assert m.loc[2,'influenza_b']==1
    assert m.loc[1,'obitos_srag']==1
    assert int(m.notificacoes.sum())==4


def test_municipio_uf_incompatível_nao_mapeia():
    raw=pd.DataFrame({'SG_UF':['GO'],'CO_MUN_RES':['510340'],'POS_PCRFLU':['1'], 'TP_FLU_PCR':['1']},dtype='string')
    assert municipal_flags(raw,2026).iloc[0]['municipio']=='Não informado'


def test_mapa_usa_escala_linear_e_uf_sobreposta():
    base=Path(__file__).resolve().parents[1]
    geo=json.loads((base/'data/malha_municipios_MT.geojson').read_text())
    states=json.loads((base/'data/malha_uf.geojson').read_text())
    rows=[{'Código':ft['properties']['codigo_sivep'],
        'Município':ft['properties']['nome'],'Registros':i} for i,ft in enumerate(geo['features'])]
    fig=choropleth_map(pd.DataFrame(rows),geo,code_col='Código',id_prop='codigo_sivep',
        name_col='Município',value_col='Registros',auto_camera=True)
    state_boundary_overlay(fig,states,['MT'])
    assert fig.layout.coloraxis.cmin==0
    assert fig.layout.coloraxis.cmax==len(rows)-1
    assert [x.type for x in fig.data]==['choroplethmap','scattermap','scattermap']
