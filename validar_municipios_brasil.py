"""Auditoria dos cubos municipais, malhas e compatibilidade da extração anual."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from construir_base import DATA,YEARS,sha256
from preparar_municipios_brasil import IBGE_PREFIX,FIELDS


def validate(require_all=False, data_dir:Path=DATA):
    path=data_dir/'municipios_brasil_manifest.json'
    if not path.exists():
        if require_all:raise ValueError('Manifesto municipal nacional ainda não gerado. Execute preparar_municipios_brasil.py --todos')
        print('[AVISO] Municípios nacionais não preparados. Válido usar apenas dados MT/MS existentes.')
        return False
    meta=json.loads(path.read_text(encoding='utf-8'))
    base=json.loads((data_dir/'manifest.json').read_text(encoding='utf-8'))
    valid=[]
    for year in YEARS:
        item=meta.get('anos',{}).get(str(year))
        if not item:
            if require_all:raise ValueError(f'Falta município nacional para {year}')
            continue
        src=base.get('anos',{}).get(str(year),{})
        path=data_dir/item['arquivo']
        if not path.exists():raise ValueError(f'{year}: arquivo municipal ausente {path}')
        if sha256(path)!=item.get('sha256_agregado'):
            raise ValueError(f'{year}: SHA256 agregado incorreto')
        if src.get('sha256_original')!=item.get('sha256_original'):
            raise ValueError(f'{year}: cubo nacional e municípios são de fontes diferentes')
        mun=pd.read_csv(path,compression='gzip',dtype={'uf':'string','municipio':'string'})
        nat=pd.read_csv(data_dir/f'cubo_srag_{year}.csv.gz',compression='gzip',dtype={'uf':'string'})
        if int(mun.notificacoes.sum())!=int(nat.notificacoes.sum()):
            raise ValueError(f'{year}: total municipal != nacional')
        a=mun.groupby('uf')['notificacoes'].sum().sort_index()
        b=nat.groupby('uf')['notificacoes'].sum().sort_index()
        if not a.equals(b):
            diff=a.sub(b,fill_value=0)
            raise ValueError(f'{year}: contagens por UF divergentes {diff[diff!=0].to_dict()}')
        if any(c not in mun.columns for c in FIELDS):
            raise ValueError(f'{year}: faltam métricas municipais')
        if mun.duplicated(['ano','uf','municipio']).any():
            raise ValueError(f'{year}: município/ano duplicado')
        valid.append(year)
        print(f'[OK] {year}: {len(mun):,} grupos, {int(mun.notificacoes.sum()):,} notificações (totais iguais por UF)')
    geo_done=[]
    for uf,prefix in IBGE_PREFIX.items():
        p=data_dir/f'malha_municipios_{uf}.geojson'
        if not p.exists():
            if require_all:raise ValueError(f'Malha municipal faltando: {uf}')
            continue
        geo=json.loads(p.read_text(encoding='utf-8'))
        ids=[str(f.get('properties',{}).get('codigo_sivep','')) for f in geo.get('features',[])]
        if not ids or any(len(x)!=6 or not x.startswith(prefix) for x in ids) or len(ids)!=len(set(ids)):
            raise ValueError(f'Malha {uf}: IDs municipais inconsistentes')
        geo_done.append(uf)
    if require_all and set(valid)!=set(YEARS):
        raise ValueError(f'Anos municipais incompletos: {valid}')
    print(f'[RESULTADO] {len(valid)}/8 anos sincronizados; {len(geo_done)}/27 UFs com polígonos.')
    return len(valid)==len(YEARS) and len(geo_done)==27

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--exigir-completo',action='store_true')
    args=ap.parse_args()
    validate(args.exigir_completo)
