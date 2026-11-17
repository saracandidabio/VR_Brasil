from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from preparar_centro_oeste import metrics_for_chunk, onset_month, combine_groups, METRICS_CO, DIMS_MUN


def test_tipos_subtipos_e_municipios():
    data=pd.DataFrame([
        {'SG_UF':'MT','CO_MUN_RES':'510340','DT_SIN_PRI':'2026-03-17T00:00:00.000Z',
         'SEM_PRI':'11','CS_SEXO':'F','NU_IDADE_N':'30','TP_IDADE':'3',
         'POS_PCRFLU':'1','TP_FLU_PCR':'1','PCR_FLUASU':'2'},
        {'SG_UF':'MS','CO_MUN_RES':'500270','DT_SIN_PRI':'2026-03-18T00:00:00.000Z',
         'SEM_PRI':'11','CS_SEXO':'M','POS_PCRFLU':'1','TP_FLU_PCR':'2','PCR_FLUBLI':'1'},
        {'SG_UF':'MT','CO_MUN_RES':'510340','DT_SIN_PRI':'2026-04-01T00:00:00.000Z',
         'SEM_PRI':'14','POS_AN_FLU':'1','TP_FLU_AN':'1'},
        {'SG_UF':'MT','CO_MUN_RES':'ABC','DT_SIN_PRI':'2026-03-13T00:00:00.000Z',
         'SEM_PRI':'10','POS_PCRFLU':'1','TP_FLU_PCR':'','PCR_FLUASU':'2'},
        {'SG_UF':'SP','CO_MUN_RES':'355030','DT_SIN_PRI':'2026-03-17T00:00:00.000Z',
         'SEM_PRI':'11','POS_PCRFLU':'1','TP_FLU_PCR':'1','PCR_FLUASU':'1'},
    ])
    res=metrics_for_chunk(data,2026)
    assert res.influenza_a.sum()==3
    assert res.influenza_b.sum()==1
    assert res.a_h3n2.sum()==1
    assert res.b_victoria.sum()==1
    assert res.influenza_sem_tipo.sum()==1
    assert res.iloc[3].a_h3n2 == 0  # subtipo isolado não prova tipo
    assert res.iloc[3].municipio == 'Não informado'
    assert res.loc[0,'mes']==3
    assert res.loc[2,'mes']==4
    assert res.loc[1,'uf']=='MS'
    co=res.loc[res.uf.isin(['MT','MS','GO','DF'])].groupby(DIMS_MUN,observed=True)[METRICS_CO].sum().reset_index()
    assert co.notificacoes.sum()==4


def test_mes_fora_do_ano_nao_classificado():
    a=pd.DataFrame({'DT_SIN_PRI':['2025-12-01T00:00:00.000Z','2026-03-22T00:00:00.000Z',None,'15/03/2026']})
    assert onset_month(a,2026).tolist()==[0,3,0,3]
