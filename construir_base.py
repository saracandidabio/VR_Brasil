"""Constrói um snapshot offline e agregado do SIVEP-Gripe/SRAG 2019–2026.

Use `python construir_base.py --todos` UMA VEZ com acesso à internet.
A publicação Streamlit utiliza somente `data/cubo_srag_*.csv.gz` e manifest.json.

NÃO identifica pessoas únicas; garante uma única fonte/arquivo por ano, mas não
promete deduplicação epidemiológica de registros no SIVEP-Gripe.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
from html import unescape
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from urllib.parse import urlparse
from zipfile import ZipFile

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
CACHE = ROOT / 'downloads_srag'
PORTAL = 'https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026'
S3 = 'https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG'
RESOURCE_PAGES = {
    2025: PORTAL + '/resource/20c49de3-ddc3-4b76-a942-1518eaae9c91',
    2026: PORTAL + '/resource/74091efc-3f75-42e8-a6fa-6b79a8d30582',
}
FALLBACK_2026 = {2025: '16-11-2026', 2026: '16-11-2026'}
YEARS = tuple(range(2019,2027))
AGE_ORDER = ['< 2 anos','2 a 4 anos','5 a 9 anos','10 a 19 anos','20 a 29 anos',
             '30 a 39 anos','40 a 49 anos','50 a 59 anos','≥ 60 anos','Não informado']
SEX_ORDER = ['Feminino','Masculino','Não informado']
UFS = set('AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO'.split())
VIRUSES = ['influenza','sars_cov_2','vsr','parainfluenza','adenovirus',
           'metapneumovirus','bocavirus','rinovirus','outros_virus']
TESTS = {
    'influenza':['POS_PCRFLU','POS_AN_FLU'],
    'sars_cov_2':['PCR_SARS2','AN_SARS2'],
    'vsr':['PCR_VSR','AN_VSR'],
    'parainfluenza':['PCR_PARA1','PCR_PARA2','PCR_PARA3','PCR_PARA4','AN_PARA1','AN_PARA2','AN_PARA3'],
    'adenovirus':['PCR_ADENO','AN_ADENO'],
    'metapneumovirus':['PCR_METAP'],
    'bocavirus':['PCR_BOCA'],
    'rinovirus':['PCR_RINO'],
    'outros_virus':['PCR_OUTRO','AN_OUTRO'],
}
CLASSIFICATIONS = {'1':'SRAG por influenza','2':'SRAG por outro vírus respiratório',
                   '3':'SRAG por outro agente etiológico','4':'SRAG não especificada',
                   '5':'SRAG por COVID-19'}
DIM = ['ano','semana','uf','sexo','faixa_etaria']
RESOLVED_CLASS2 = ['class2_sem_detalhe','class2_codeteccao','class2_outros_virus_nao_especificados'] + [f'class2_{v}' for v in VIRUSES if v!='outros_virus']
CLASS_ONLY = ['classe_influenza_sem_resultado_laboratorial', 'classe_covid_sem_resultado_laboratorial', 'classe_outro_virus_sem_resultado_laboratorial']
METRICS = CLASS_ONLY + ['notificacoes','com_deteccao','codeteccoes','hospitalizados','uti','obitos_srag','desfecho_conhecido'] + [f'v_{v}' for v in VIRUSES] + [f'obito_{v}' for v in VIRUSES] + [f'uti_{v}' for v in VIRUSES] + [f'classe_{i}' for i in range(1,6)] + RESOLVED_CLASS2


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=1.4,
                  status_forcelist=(429,500,502,503,504),allowed_methods=('GET','HEAD'))
    s.mount('https://',HTTPAdapter(max_retries=retry))
    s.headers.update({'User-Agent':'SRAG-Observatorio-Academico/1.0 (+dados publicos)'})
    return s


def official_url(year:int, s:requests.Session) -> str:
    if year not in YEARS:
        raise ValueError(f'Ano não contemplado: {year}')
    if year<=2024:
        return f'{S3}/{year}/INFLUD{str(year)[-2:]}-23-03-2026.csv'
    try:
        r=s.get(RESOURCE_PAGES[year],timeout=(20,50));r.raise_for_status()
        html=unescape(r.text).replace('\\/','/')
        found=re.findall(r'https://s3\.sa-east-1\.amazonaws\.com/ckan\.saude\.gov\.br/SRAG/\d{4}/INFLUD\d{2}-\d{2}-\d{2}-\d{4}\.csv',html)
        correct=[u for u in found if f'/SRAG/{year}/INFLUD{str(year)[-2:]}-' in u]
        if correct:return correct[0]
    except requests.RequestException as e:
        print(f'[AVISO] Falha consultando página de {year}: {e}',flush=True)
    print(f'[AVISO] Usando URL confirmada em 17/11/2026 para {year}; pode ficar desatualizada.',flush=True)
    return f'{S3}/{year}/INFLUD{str(year)[-2:]}-{FALLBACK_2026[year]}.csv'


def sha256(path:Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
    return h.hexdigest()


def download(url:str,dest:Path,s:requests.Session) -> None:
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.is_file() and dest.stat().st_size>100_000:
        print(f'  Já existe {dest.name} ({dest.stat().st_size/1e6:,.1f} MB)',flush=True)
        return
    partial=dest.with_suffix(dest.suffix+'.part')
    offset=partial.stat().st_size if partial.exists() else 0
    h={'Range':f'bytes={offset}-'} if offset else {}
    with s.get(url,stream=True,timeout=(25,180),headers=h) as r:
        r.raise_for_status()
        accept_resume=(r.status_code==206 and offset>0)
        mode='ab' if accept_resume else 'wb'
        total=int(r.headers.get('Content-Length') or 0) + (offset if accept_resume else 0)
        with partial.open(mode) as f:
            size=offset if accept_resume else 0
            last_report=size
            for buf in r.iter_content(chunk_size=2**20):
                if not buf:continue
                f.write(buf)
                size+=len(buf)
                if size-last_report>=50*2**20:
                    print(f'  {size/1e6:,.0f} MB'+(f' / {total/1e6:,.0f} MB' if total else ''),flush=True)
                    last_report=size
    if partial.stat().st_size<1000:
        raise RuntimeError('Download minúsculo/inválido; confira URL')
    partial.replace(dest)


def age_group(raw:pd.DataFrame)->pd.Series:
    v=pd.to_numeric(raw.get('NU_IDADE_N',pd.Series(index=raw.index,dtype='string')),errors='coerce')
    u=raw.get('TP_IDADE',pd.Series(index=raw.index,dtype='string')).astype('string')
    years=v.where(u.eq('3'),0.0).where(u.isin(['1','2','3']))
    years=years.where(years.between(0,120) & v.notna())
    bins=[-0.01,1.999,4.999,9.999,19.999,29.999,39.999,49.999,59.999,120]
    return pd.cut(years,bins=bins,labels=AGE_ORDER[:-1]).astype('string').fillna('Não informado')


def col(raw:pd.DataFrame,name:str)->pd.Series:
    if name in raw.columns:return raw[name].astype('string').str.strip()
    return pd.Series(pd.NA,index=raw.index,dtype='string')


def make_metrics(raw:pd.DataFrame,year:int)->pd.DataFrame:
    out=pd.DataFrame(index=raw.index)
    out['ano']=year # ano do arquivo epidemiológico, evita sobreposição de anos por data de sintomas
    weeks=pd.to_numeric(col(raw,'SEM_PRI'),errors='coerce')
    # preservar semana desconhecida separadamente, sem inventar semana 1
    out['semana']=weeks.where(weeks.between(1,53)).fillna(0).astype('int16')
    uf=col(raw,'SG_UF').str.upper()
    out['uf']=uf.where(uf.isin(UFS),'Não informado').fillna('Não informado')
    sex=col(raw,'CS_SEXO').str.upper().map({'F':'Feminino','M':'Masculino'})
    out['sexo']=sex.fillna('Não informado')
    out['faixa_etaria']=age_group(raw)
    evol=col(raw,'EVOLUCAO')
    obito=evol.eq('2').fillna(False)
    uti=col(raw,'UTI').eq('1').fillna(False)
    hospital=col(raw,'HOSPITAL').eq('1').fillna(False)
    flags={}
    for virus,fields in TESTS.items():
        cols=[col(raw,c).eq('1').fillna(False) for c in fields if c in raw.columns]
        flag=pd.concat(cols,axis=1).any(axis=1) if cols else pd.Series(False,index=raw.index)
        flags[virus]=flag
    count=sum(f.astype('int8') for f in flags.values())
    out['notificacoes']=1
    out['com_deteccao']=(count>=1).astype('int8')
    out['codeteccoes']=(count>=2).astype('int8')
    out['hospitalizados']=hospital.astype('int8')
    out['uti']=uti.astype('int8')
    out['obitos_srag']=obito.astype('int8')
    out['desfecho_conhecido']=evol.isin(['1','2','3']).astype('int8')
    for virus,flag in flags.items():
        out[f'v_{virus}']=flag.astype('int8')
        out[f'obito_{virus}']=(flag&obito).astype('int8')
        out[f'uti_{virus}']=(flag&uti).astype('int8')
    classifications=col(raw,'CLASSI_FIN')
    for cls in range(1,6):out[f'classe_{cls}']=classifications.eq(str(cls)).fillna(False).astype('int8')

    # CLASSI_FIN não identifica o tipo A/B e não substitui teste positivo.
    # 'Sem resultado laboratorial registrado' é diferente de teste negativo:
    # 1 positivo, 2 negativo e 3 inconclusivo são resultados, portanto excluídos.
    # 'Aguardando', 'não realizado' e vazio não constituem resultado disponível.
    # Registrar somente se NENHUM marcador viral estiver positivo.
    has_result = (col(raw, 'PCR_RESUL').isin(['1','2','3']) |
                  col(raw, 'RES_AN').isin(['1','2','3'])).fillna(False)
    class_only = (~has_result) & count.eq(0)
    for cl, name in [('1','classe_influenza_sem_resultado_laboratorial'),
                     ('5','classe_covid_sem_resultado_laboratorial'),
                     ('2','classe_outro_virus_sem_resultado_laboratorial')]:
        out[name]=(class_only & classifications.eq(cl).fillna(False)).astype('int8')


    # Resolve parte das notificações classificadas genericamente como
    # 'outro vírus respiratório' (CLASSI_FIN=2) usando os marcadores laboratoriais.
    is_class2 = classifications.eq('2').fillna(False)
    viral_count = sum(flags[v].astype('int8') for v in VIRUSES)
    out['class2_sem_detalhe'] = (is_class2 & viral_count.eq(0)).astype('int8')
    out['class2_codeteccao'] = (is_class2 & viral_count.ge(2)).astype('int8')
    out['class2_outros_virus_nao_especificados'] = (is_class2 & viral_count.eq(1) & flags['outros_virus']).astype('int8')
    for virus in VIRUSES:
        if virus == 'outros_virus':
            continue
        out[f'class2_{virus}'] = (is_class2 & viral_count.eq(1) & flags[virus]).astype('int8')
    return out


def read_chunks(fp, chunksize:int=60000):
    # Fonte oficial usa ; e codificação latin1 nas versões verificadas.
    yield from pd.read_csv(fp,sep=';',encoding='latin1',dtype='string',chunksize=chunksize,
                           on_bad_lines='error',keep_default_na=True,low_memory=False)


def process(fp,year:int,outfile:Path,chunksize:int=60000) -> dict:
    partial=[];raw_n=0; source_fields=set();missing_fields=set()
    for i,chunk in enumerate(read_chunks(fp,chunksize)):
        if i==0:
            source_fields=set(chunk.columns)
            for group in [['SG_UF','CS_SEXO','NU_IDADE_N','TP_IDADE','SEM_PRI','EVOLUCAO','HOSPITAL','UTI','CLASSI_FIN']]:
                missing_fields.update(set(group)-source_fields)
            if len(missing_fields)>3:raise ValueError(f'{year}: colunas essenciais ausentes: {sorted(missing_fields)}')
        raw_n+=len(chunk)
        metrics=make_metrics(chunk,year)
        grouped=metrics.groupby(DIM,dropna=False,sort=False,observed=True)[METRICS].sum().reset_index()
        partial.append(grouped)
        if i%10==0:print(f'    {year}: {raw_n:,} notificações lidas',flush=True)
    if not partial:raise ValueError(f'{year}: arquivo vazio')
    cube=pd.concat(partial,ignore_index=True).groupby(DIM,sort=False,dropna=False,observed=True)[METRICS].sum().reset_index()
    if int(cube['notificacoes'].sum())!=raw_n:raise AssertionError('Contagem da agregação não confere')
    for field in METRICS:
        if field!='notificacoes' and (cube[field]>cube['notificacoes']).any():
            raise AssertionError(f'Indicador {field} excede notificações')
    outfile.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(outfile,'wt',encoding='utf-8',compresslevel=8) as f:
        cube.to_csv(f,index=False)
    return dict(ano=year,notificacoes=raw_n,grupos=len(cube),
                casos_com_marcador=int(cube['com_deteccao'].sum()),
                casos_obito_srag=int(cube['obitos_srag'].sum()),
                semanas_nao_informadas=int(cube.loc[cube.semana.eq(0),'notificacoes'].sum()),
                campos_essenciais_ausentes=sorted(missing_fields),
                tamanho_arquivo_mb=round(outfile.stat().st_size/1e6,3))


def file_info(out_file:Path,url:str,src_file:Path,stats:dict,origin:str)->dict:
    return {'origem':origin,'url_recurso':url,'nome_arquivo_original':src_file.name,
            'sha256_original':sha256(src_file),'tamanho_original_bytes':src_file.stat().st_size,
            'arquivo_agregado':out_file.name,'sha256_agregado':sha256(out_file),**stats}


def build_one(year, source_file, origin_url, origin='portal_oficial'):
    out=DATA/f'cubo_srag_{year}.csv.gz'
    print(f'[PROCESSAMENTO] {year}',flush=True)
    with source_file.open('rb') as f:stats=process(f,year,out)
    return file_info(out,origin_url,source_file,stats,origin)


def consolidate(metadata:dict)->None:
    available=[]
    for year in YEARS:
        path=DATA/f'cubo_srag_{year}.csv.gz'
        if path.exists() and str(year) in metadata.get('anos',{}):available.append(year)
    metadata['anos_disponiveis']=available
    metadata['notificacoes_total']=sum(metadata['anos'][str(y)]['notificacoes'] for y in available)
    metadata['completo_2019_2026']=available==list(YEARS)
    metadata['gerado_em_utc']=datetime.now(timezone.utc).isoformat(timespec='seconds')
    tmp=DATA/'manifest.json.tmp'
    tmp.write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(DATA/'manifest.json')



IBGE_API='https://servicodados.ibge.gov.br/api/v3/malhas/estados'

def download_uf_geojson(s:requests.Session)->None:
    """Prepara malhas estaduais via IBGE; nenhum acesso externo é feito no Streamlit."""
    dst=DATA/'malha_uf.geojson'
    if dst.exists():
        print('[MALHA] Já disponível localmente',flush=True)
        return
    features=[]
    for uf in sorted(UFS):
        r=s.get(f'{IBGE_API}/{uf}',params={'formato':'application/vnd.geo+json',
                'qualidade':'minima'},timeout=(20,90))
        r.raise_for_status()
        obj=r.json()
        if obj.get('type')=='FeatureCollection':
            sub=obj.get('features',[])
        elif obj.get('type')=='Feature':
            sub=[obj]
        elif obj.get('type') in ('Polygon','MultiPolygon'):
            sub=[{'type':'Feature','geometry':obj,'properties':{}}]
        else:
            raise ValueError(f'API malha IBGE: tipo não reconhecido para {uf}: {obj.get("type")}')
        if len(sub)!=1 or not sub[0].get('geometry'):
            raise ValueError(f'Malha com {len(sub)} elementos em {uf}, esperado 1')
        feature=sub[0]
        feature['id']=uf
        feature.setdefault('properties',{})['sigla']=uf
        features.append(feature)
    if len(features)!=27:raise ValueError('IBGE retornou menos de 27 UFs')
    temp=dst.with_suffix('.geojson.tmp')
    temp.write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False),encoding='utf-8')
    temp.replace(dst)
    print(f'[MALHA] 27 UFs do IBGE incluídas no snapshot ({dst.stat().st_size/1e3:.1f} KB)',flush=True)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--todos',action='store_true',help='Baixar e processar os 8 anos de 2019 a 2026')
    ap.add_argument('--anos',type=int,nargs='+',help='Baixar e processar apenas anos selecionados')
    ap.add_argument('--arquivo-local',type=Path,help='CSV já baixado (usado em conjunto com --ano-local)')
    ap.add_argument('--ano-local',type=int,help='Ano de arquivo local CSV')
    ap.add_argument('--zip-demo',type=Path,help='Importar somente o CSV de 2026 existente no ZIP da pesquisa')
    ap.add_argument('--preservar-brutos',action='store_true',help='Manter CSVs originais fora do GitHub')
    ap.add_argument('--reprocessar',action='store_true',help='Reprocessar anos mesmo se já estiverem preparados')
    ap.add_argument('--sem-malha',action='store_true',help='Não consultar a API do IBGE para os polígonos estaduais')
    ap.add_argument('--apenas-malha',action='store_true',help='Baixar somente a malha do IBGE; sem reconstruir os anos de SRAG')
    args=ap.parse_args(argv)
    DATA.mkdir(exist_ok=True,parents=True)
    if args.apenas_malha:
        download_uf_geojson(session())
        print('Malha pronta. Inclua data/malha_uf.geojson no repositório GitHub.',flush=True)
        return
    meta_path=DATA/'manifest.json'
    metadata=json.loads(meta_path.read_text()) if meta_path.exists() else {
        'versao':'1.0','sistema':'SIVEP-Gripe — SRAG',
        'colecao_oficial':PORTAL,'unidade':'notificações; não pessoas únicas',
        'definicoes':{'ano':'ano epidemiológico do arquivo de origem',
            'semana':'SEM_PRI (0 = ausente/inválida)',
            'uf':'SG_UF (residência)',
            'deteccao':'campo laboratorial de agente igual a 1; negativo/ausente NÃO equivale a não testado',
            'codeteccao':'dois ou mais grupos de vírus positivos na mesma notificação',
            'obito':'EVOLUCAO = 2 (óbito por SRAG), sem ajustes de atraso',
            'desfecho_conhecido':'EVOLUCAO em {1,2,3}',
            'duplicidade':'um arquivo oficial por ano. Não há eliminação automática de notificações duplicadas dentro do SIVEP; não representa pessoas únicas.'},
        'anos':{}}
    if args.zip_demo:
        year=2026
        with ZipFile(args.zip_demo) as z:
            matches=[n for n in z.namelist() if re.search(r'/SRAG/2026/INFLUD26.*\.csv$',n)]
            if len(matches)!=1:raise ValueError('ZIP não contém CSV SRAG 2026 único')
            print('Usando versão histórica de 2026 enviada pelo usuário; NÃO é atualização do portal.')
            with tempfile.TemporaryDirectory() as td:
                p=Path(td)/Path(matches[0]).name
                with z.open(matches[0]) as src,p.open('wb') as dst:shutil.copyfileobj(src,dst)
                metadata['anos'][str(year)]=build_one(year,p,'arquivo fornecido pelo usuário',origin='arquivo_local_demo')
                consolidate(metadata)
        return
    if args.arquivo_local:
        if args.ano_local not in YEARS:ap.error('--ano-local deve estar entre 2019 e 2026')
        y=args.ano_local
        metadata['anos'][str(y)]=build_one(y,args.arquivo_local,'arquivo fornecido pelo usuário',origin='arquivo_local')
        consolidate(metadata)
        return
    years=list(YEARS) if args.todos else args.anos
    if not years:ap.error('Informe --todos, --anos, --arquivo-local ou --zip-demo')
    s=session()
    for y in years:
        if y not in YEARS:raise ValueError(f'Ano inválido: {y}')
        out=DATA/f'cubo_srag_{y}.csv.gz'
        if (out.exists() and str(y) in metadata['anos'] and
            metadata['anos'][str(y)].get('origem')=='portal_oficial' and not args.reprocessar):
            print(f'[PULAR] {y} já preparado (use --reprocessar se desejar substituir)',flush=True)
            continue
        url=official_url(y,s)
        dest=CACHE/Path(urlparse(url).path).name
        print(f'[DOWNLOAD] {y}: {url}',flush=True)
        download(url,dest,s)
        # Resumo: downloads de 2020 e 2021 podem ocupar GB em disco durante preparação.
        metadata['anos'][str(y)]=build_one(y,dest,url)
        consolidate(metadata)
        if not args.preservar_brutos:
            dest.unlink(missing_ok=True)
    if not args.sem_malha:
        try: download_uf_geojson(s)
        except (requests.RequestException, ValueError, OSError) as exc:
            print(f'[AVISO] Não foi possível baixar a malha UF do IBGE: {exc}. O mapa usará marcadores.',flush=True)
    consolidate(metadata)
    print(f'\nConcluído: {len(metadata["anos_disponiveis"])}/8 anos; completo={metadata["completo_2019_2026"]}',flush=True)


if __name__=='__main__':main()
