"""Prepara UMA VEZ a distribuição municipal de SRAG de 2019 a 2026.

Baixa uma única fonte SIVEP por ano, sincroniza o cubo nacional, o complemento
CO/Influenza (2023-2026) e a tabela por município e ano; adiciona as malhas
municipais oficiais do IBGE, usando a mesma extração. Nada é baixado online.

Executar: python preparar_municipios_brasil.py --todos
Alternativa com CSV já baixado: python preparar_municipios_brasil.py --ano-local 2026 --arquivo-local INFLUD26.csv
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from typing import Any

import pandas as pd
import requests

from construir_base import (ROOT, DATA, CACHE, YEARS, UFS, TESTS, col,
                            make_metrics, official_url, session, download,
                            download_uf_geojson, build_one, consolidate, sha256)
from preparar_centro_oeste import (process_source, update_metadata,
                                    fetch_municipal_geojson as fetch_co_geo)

IBGE_PREFIX = {
    'RO':'11','AC':'12','AM':'13','RR':'14','PA':'15','AP':'16','TO':'17',
    'MA':'21','PI':'22','CE':'23','RN':'24','PB':'25','PE':'26','AL':'27','SE':'28','BA':'29',
    'MG':'31','ES':'32','RJ':'33','SP':'35','PR':'41','SC':'42','RS':'43',
    'MS':'50','MT':'51','GO':'52','DF':'53',
}
MUN_DIR = DATA
FIELDS = ['notificacoes','com_deteccao','codeteccoes','uti','obitos_srag'] + [f'v_{x}' for x in TESTS] + [
    'influenza_a','influenza_b','influenza_sem_tipo','influenza_a_b',
    'a_h1n1','a_h3n2','b_victoria','b_yamagata']
DIMS = ['ano','uf','municipio']
REQUIRED_SOURCE = set(('SG_UF','CO_MUN_RES','SEM_PRI','EVOLUCAO','UTI','CLASSI_FIN',
                       'POS_PCRFLU','POS_AN_FLU','TP_FLU_PCR','TP_FLU_AN',
                       'PCR_FLUASU','PCR_FLUBLI'))
REQUIRED_SOURCE |= {field for fields in TESTS.values() for field in fields}


def municipal_flags(raw: pd.DataFrame, year: int) -> pd.DataFrame:
    base = make_metrics(raw,year)
    out=base[['ano','uf','notificacoes','com_deteccao','codeteccoes','uti','obitos_srag',
              *[f'v_{x}' for x in TESTS]]].copy()
    original = col(raw,'CO_MUN_RES').str.extract(r'^\s*(\d{6})',expand=False)
    # CO_MUN_RES usa seis primeiros algarismos do geocódigo IBGE.
    expected_prefix = out.uf.map(IBGE_PREFIX)
    valid = original.str[:2].eq(expected_prefix).fillna(False)
    out['municipio'] = original.where(valid,'Não informado').fillna('Não informado')
    pcr = col(raw,'POS_PCRFLU').eq('1').fillna(False)
    ant = col(raw,'POS_AN_FLU').eq('1').fillna(False)
    pt=col(raw,'TP_FLU_PCR'); at=col(raw,'TP_FLU_AN')
    a=(pcr & pt.eq('1').fillna(False)) | (ant & at.eq('1').fillna(False))
    b=(pcr & pt.eq('2').fillna(False)) | (ant & at.eq('2').fillna(False))
    out['influenza_a']=a.astype('int8')
    out['influenza_b']=b.astype('int8')
    out['influenza_sem_tipo']=((pcr|ant)&~a&~b).astype('int8')
    out['influenza_a_b']=(a&b).astype('int8')
    sub_a=col(raw,'PCR_FLUASU'); sub_b=col(raw,'PCR_FLUBLI')
    out['a_h1n1']=(pcr & pt.eq('1').fillna(False) & sub_a.eq('1').fillna(False)).astype('int8')
    out['a_h3n2']=(pcr & pt.eq('1').fillna(False) & sub_a.eq('2').fillna(False)).astype('int8')
    out['b_victoria']=(pcr & pt.eq('2').fillna(False) & sub_b.eq('1').fillna(False)).astype('int8')
    out['b_yamagata']=(pcr & pt.eq('2').fillna(False) & sub_b.eq('2').fillna(False)).astype('int8')
    return out[DIMS+FIELDS]


def process_municipal(source: Path, year: int, chunk_size: int=55000) -> dict:
    parts=[]; raw_count=0; missing_names=set(); original_columns=set()
    with source.open('rb') as fp:
        chunks=pd.read_csv(fp, sep=';',encoding='latin1', dtype='string',
                           usecols=lambda c:c in REQUIRED_SOURCE,
                           chunksize=chunk_size,on_bad_lines='error',low_memory=False)
        for i,raw in enumerate(chunks):
            if i==0:
                original_columns=set(raw.columns)
                essential={'CO_MUN_RES','SG_UF'}
                if essential-original_columns:
                    raise ValueError(f'{year}: campos geográficos obrigatórios não encontrados: {essential-original_columns}')
                missing_names=REQUIRED_SOURCE-original_columns
            raw_count+=len(raw)
            m=municipal_flags(raw,year)
            parts.append(m.groupby(DIMS,observed=True,dropna=False,sort=False)[FIELDS].sum().reset_index())
            if i%12==0:
                print(f'  {year}: {raw_count:,} notificações agregadas por município',flush=True)
    if not parts:raise ValueError(f'{year}: fonte CSV vazia')
    all_groups=pd.concat(parts,ignore_index=True).groupby(DIMS,observed=True,dropna=False,sort=False)[FIELDS].sum().reset_index()
    if int(all_groups.notificacoes.sum())!=raw_count:
        raise AssertionError(f'{year}: total municipal diferente da fonte')
    if (all_groups[FIELDS].gt(all_groups.notificacoes,axis=0)).any().any():
        raise AssertionError(f'{year}: indicador excede registros')
    # Ordenação determinística para hashes estáveis e GitHub.
    all_groups=all_groups.sort_values(DIMS).reset_index(drop=True)
    filename=f'municipios_brasil_{year}.csv.gz'
    outfile=DATA/filename
    outfile.parent.mkdir(parents=True,exist_ok=True)
    tmp=outfile.with_suffix('.gz.tmp')
    with gzip.open(tmp,'wt',encoding='utf-8',compresslevel=8) as f:
        all_groups.to_csv(f,index=False)
    tmp.replace(outfile)
    return {
       'ano':year,'notificacoes_fonte':raw_count,'linhas_agrupadas':len(all_groups),
       'municipios_com_registros':int(all_groups.loc[all_groups.municipio.ne('Não informado'),'municipio'].nunique()),
       'notificacoes_sem_municipio_valido':int(all_groups.loc[all_groups.municipio.eq('Não informado'),'notificacoes'].sum()),
       'arquivo':filename,'sha256_agregado':sha256(outfile),
       'campos_originais_ausentes':sorted(missing_names),
       'campos_tipagem_disponiveis':all(k in original_columns for k in ('TP_FLU_PCR','TP_FLU_AN')),
    }


def fetch_geo(uf: str, s:requests.Session, force:bool=False):
    if uf not in UFS:raise ValueError(f'UF inválida: {uf}')
    dest=DATA/f'malha_municipios_{uf}.geojson'
    if dest.is_file() and not force:
        obj=json.loads(dest.read_text(encoding='utf-8'))
        codes=[str(f.get('properties',{}).get('codigo_sivep','')) for f in obj.get('features',[])]
        if codes and all(re.fullmatch(r'\d{6}',c) for c in codes) and len(codes)==len(set(codes)):
            print(f'[MALHA] {uf} já validada ({len(codes)} municípios)',flush=True)
            return
    # Mantém total compatibilidade com as malhas MT/MS já processadas e IBGE.
    if uf in ('MT','MS'):
        fetch_co_geo(uf,s,force=force)
        return
    r=s.get(f'https://servicodados.ibge.gov.br/api/v3/malhas/estados/{uf}',
            params={'intrarregiao':'municipio','formato':'application/vnd.geo+json','qualidade':'minima'},
            timeout=(25,180))
    r.raise_for_status()
    geo=r.json()
    if geo.get('type')!='FeatureCollection' or not geo.get('features'):
        raise ValueError(f'IBGE {uf}: malha municipal inválida: {geo.get("type")}')
    feats=geo['features']
    # O Distrito Federal não possui divisão em municípios como as demais UFs;
    # caso a API não forneça o geocódigo 5300108, usamos a geometria estadual
    # com o código IBGE de Brasília, sem inventar subdivisões administrativas.
    if uf=='DF':
        first=feats[0]
        props=first.get('properties',{})
        candidates=[first.get('id'),*(props.get(k) for k in
                   ('codarea','codmun','CD_MUN','codigo','id','cod','geocodigo'))]
        if not any(re.fullmatch(r'\d{7}',str(v)) for v in candidates if v is not None):
            geo_uf=json.loads((DATA/'malha_uf.geojson').read_text(encoding='utf-8'))
            matched=[f for f in geo_uf.get('features',[]) if f.get('properties',{}).get('sigla')=='DF']
            if len(matched)!=1:raise ValueError('Não foi possível obter o contorno oficial de DF')
            feats=[{'type':'Feature','id':'5300108',
                    'properties':{'codigo_sivep':'530010','nome':'Brasília'},
                    'geometry':matched[0]['geometry']}]
            geo={'type':'FeatureCollection','features':feats}
    unique=set()
    for feature in feats:
        props=feature.setdefault('properties',{})
        candidates=[feature.get('id'), *(props.get(k) for k in
               ('codarea','codmun','CD_MUN','codigo','id','cod','geocodigo'))]
        seven=next((str(c) for c in candidates if c is not None and re.fullmatch(r'\d{7}',str(c))),None)
        if not seven:
            raise ValueError(f'IBGE {uf}: código de 7 dígitos ausente para: {candidates}')
        six=seven[:6]
        if not six.startswith(IBGE_PREFIX[uf]) or six in unique:
            raise ValueError(f'IBGE {uf}: código inválido/duplicado: {six}')
        unique.add(six)
        props['codigo_sivep']=six
        if not feature.get('geometry'):
            raise ValueError(f'IBGE {uf}: geometria ausente para {seven}')
    rr=s.get(f'https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios',timeout=(25,100))
    rr.raise_for_status()
    names={str(m['id'])[:6]:m['nome'] for m in rr.json()}
    for feature in feats:
        code=feature['properties']['codigo_sivep']
        feature['properties']['nome']=names.get(code,code)
    tmp=dest.with_suffix('.geojson.tmp')
    tmp.write_text(json.dumps(geo,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    tmp.replace(dest)
    print(f'[MALHA] {uf}: {len(feats)} polígonos ({dest.stat().st_size/1024:.0f} KiB)',flush=True)


def manifest_path():return DATA/'municipios_brasil_manifest.json'


def read_manifest():
    p=manifest_path()
    if p.exists():return json.loads(p.read_text(encoding='utf-8'))
    return {'versao':'8.0','fonte':'SIVEP-Gripe / Ministério da Saúde',
            'referencia':'https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026',
            'municipio':'CO_MUN_RES (residência), seis dígitos IBGE',
            'geometria':'API de malhas municipais IBGE, qualidade mínima',
            'granularidade':'município, UF e ano; sem dados individuais, idade ou semana',
            'escala_cores':'linear (valores absolutos); sem quantis/raiz quadrada',
            'anos':{}}


def persist_manifest(meta):
    meta['gerado_em_utc']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    meta['anos_disponiveis']=sorted(int(y) for y,d in meta['anos'].items() if (DATA/d.get('arquivo','não existe')).exists())
    meta['completo_2019_2026']=meta['anos_disponiveis']==list(YEARS)
    geo_done=[]
    for uf in IBGE_PREFIX:
        p=DATA/f'malha_municipios_{uf}.geojson'
        if p.exists():geo_done.append(uf)
    meta['ufs_malhas_disponiveis']=sorted(geo_done)
    meta['malhas_completas']=len(geo_done)==27
    tmp=manifest_path().with_suffix('.json.tmp')
    tmp.write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(manifest_path())


def prepare_one(year:int, source:Path, url:str, *, sync:bool=True):
    meta=read_manifest()
    original_sha=sha256(source)
    if sync:
        national_path=DATA/'manifest.json'
        national=json.loads(national_path.read_text(encoding='utf-8')) if national_path.exists() else {
            'versao':'1.0','sistema':'SIVEP-Gripe — SRAG',
            'colecao_oficial':'https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026',
            'unidade':'notificações; não pessoas únicas','anos':{}}
        national['anos'][str(year)]=build_one(year,source,url,origin='portal_oficial' if url.startswith('https://') else 'arquivo_local')
        consolidate(national)
    info=process_municipal(source,year)
    info['sha256_original']=original_sha
    info['fonte_csv']=source.name
    info['url_origem']=url
    national=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    ref=national.get('anos',{}).get(str(year),{})
    info['compatibilidade_cubo_nacional']=(ref.get('sha256_original')==original_sha and
                                            int(ref.get('notificacoes',-1))==info['notificacoes_fonte'])
    if not info['compatibilidade_cubo_nacional']:
        print(f'[ALERTA] {year}: município e cubo nacional usam extrações diferentes; o painel não exibirá esses municípios até sincronizar.',flush=True)
    # Complemento de influenza é atualizado a partir da mesma extração.
    if year>=2023 and sync:
        print(f'[COMPLEMENTO CENTRO-OESTE] {year}',flush=True)
        update_metadata(process_source(source,year))
    meta['anos'][str(year)]=info
    persist_manifest(meta)
    return info


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--todos',action='store_true',help='Baixar e preparar os oito anos')
    ap.add_argument('--anos',type=int,nargs='+',help='Somente estes anos')
    ap.add_argument('--arquivo-local',type=Path)
    ap.add_argument('--ano-local',type=int)
    ap.add_argument('--apenas-malhas',action='store_true')
    ap.add_argument('--sem-malhas',action='store_true')
    ap.add_argument('--preservar-brutos',action='store_true')
    ap.add_argument('--reprocessar',action='store_true')
    args=ap.parse_args(argv)
    if args.arquivo_local and args.ano_local not in YEARS:
        ap.error('--arquivo-local requer --ano-local entre 2019 e 2026')
    if args.ano_local and not args.arquivo_local:
        ap.error('--ano-local requer --arquivo-local')
    if args.apenas_malhas and args.sem_malhas:ap.error('Não combine --apenas-malhas e --sem-malhas')
    years=[args.ano_local] if args.arquivo_local else list(YEARS) if args.todos else args.anos
    if not years and not args.apenas_malhas:
        ap.error('Informe --todos, --anos, --apenas-malhas ou --arquivo-local + --ano-local')
    for y in years or []:
        if y not in YEARS:ap.error(f'Ano não suportado: {y}')
    DATA.mkdir(parents=True,exist_ok=True)
    s=session()
    if not args.sem_malhas:
        download_uf_geojson(s)
        for uf in sorted(IBGE_PREFIX):
            fetch_geo(uf,s,force=False)
        persist_manifest(read_manifest())
    if args.apenas_malhas:
        print('[OK] Malhas baixadas. Gere as tabelas executando --todos.',flush=True)
        return
    for year in years:
        prev=read_manifest()['anos'].get(str(year),{})
        nation=json.loads((DATA/'manifest.json').read_text(encoding='utf-8')) if (DATA/'manifest.json').exists() else {}
        info_national=nation.get('anos',{}).get(str(year),{})
        if (not args.reprocessar and prev.get('compatibilidade_cubo_nacional') and
            prev.get('sha256_original')==info_national.get('sha256_original') and
            (DATA/prev.get('arquivo','ausente')).exists()):
            print(f'[PULAR] {year}: município e cubo nacional já sincronizados',flush=True)
            continue
        if args.arquivo_local:
            source=args.arquivo_local
            origin='arquivo local disponibilizado pelo usuário'
        else:
            origin=official_url(year,s)
            source=CACHE/Path(urlparse(origin).path).name
            print(f'[DOWNLOAD] {year}: {origin}',flush=True)
            download(origin,source,s)
        print(f'[PROCESSAMENTO] {year}: sincronizando cubo, municípios e complemento',flush=True)
        prepare_one(year,source,origin)
        if not args.preservar_brutos and not args.arquivo_local:
            source.unlink(missing_ok=True)
    meta=read_manifest()
    persist_manifest(meta)
    print(f'[CONCLUÍDO] {len(meta["anos_disponiveis"])}/8 anos municipais; malhas {len(meta["ufs_malhas_disponiveis"])}/27 UFs',flush=True)
    print('Envie o conteúdo de data/ e os arquivos Python para GitHub. Não envie downloads_srag/.',flush=True)


if __name__=='__main__':main()
