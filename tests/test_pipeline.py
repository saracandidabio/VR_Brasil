from pathlib import Path
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from construir_base import make_metrics,official_url, YEARS, PORTAL, session
from validar_base import validate


def test_prepare_one_row():
    raw=pd.DataFrame([{'SEM_PRI':'11','SG_UF':'MG','CS_SEXO':'F','NU_IDADE_N':'1','TP_IDADE':'3',
                      'POS_PCRFLU':'1','PCR_VSR':'1','EVOLUCAO':'2','UTI':'1','HOSPITAL':'1',
                      'CLASSI_FIN':'1'},
                      {'SEM_PRI':'','SG_UF':'XX','CS_SEXO':'M','NU_IDADE_N':'','TP_IDADE':'2',
                       'EVOLUCAO':'3','CLASSI_FIN':'4'}])
    d=make_metrics(raw,2026)
    assert len(d)==2
    assert d.iloc[0]['com_deteccao']==1
    assert d.iloc[0]['codeteccoes']==1
    assert d.iloc[0]['obitos_srag']==1
    assert d.iloc[0]['faixa_etaria']=='< 2 anos'
    assert d.iloc[1]['semana']==0
    assert d.iloc[1]['uf']=='Não informado'
    assert d.iloc[1]['faixa_etaria']=='Não informado'
    assert d.iloc[1]['obitos_srag']==0


def test_link_frozen_year_without_network():
    u=official_url(2020,session())
    assert u.endswith('/2020/INFLUD20-23-03-2026.csv')


def test_example_data_integrity():
    if not (Path(__file__).resolve().parents[1]/'data'/'manifest.json').exists():
        pytest.skip('Pacote de atualização sem dados originais')
    assert validate(required_all=False)


def test_class2_detalhamento_exclusivo():
    raw=pd.DataFrame([
        {'CLASSI_FIN':'2','PCR_VSR':'1'},
        {'CLASSI_FIN':'2','PCR_RINO':'1'},
        {'CLASSI_FIN':'2','PCR_VSR':'1','PCR_RINO':'1'},
        {'CLASSI_FIN':'2','PCR_OUTRO':'1'},
        {'CLASSI_FIN':'2'},
        {'CLASSI_FIN':'1','PCR_VSR':'1'},
    ])
    d=make_metrics(raw,2026)
    keys=[c for c in d if c.startswith('class2_')]
    assert d['class2_vsr'].sum()==1
    assert d['class2_rinovirus'].sum()==1
    assert d['class2_codeteccao'].sum()==1
    assert d['class2_outros_virus_nao_especificados'].sum()==1
    assert d['class2_sem_detalhe'].sum()==1
    assert int(d[keys].sum().sum())==int(d.classe_2.sum())==5
