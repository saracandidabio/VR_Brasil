"""Complemento offline do SIVEP-Gripe para influenza A/B e mapas municipais.

Um arquivo de origem por ano. Gera tabelas agregadas (não registros individuais),
separadas do cubo SRAG principal; não altera `data/cubo_srag_*.csv.gz`.

Exemplos:
  python preparar_centro_oeste.py --todos --malhas
  python preparar_centro_oeste.py --ano-local 2026 --arquivo-local /caminho/INFLUD26.csv
  python preparar_centro_oeste.py --apenas-malhas
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import re
from urllib.parse import urlparse

import pandas as pd
import requests

from construir_base import (ROOT, DATA, CACHE, col, age_group, download,
                            download_uf_geojson, official_url, session, sha256, TESTS)

YEARS_CO = (2023, 2024, 2025, 2026)
STATES_CO = ('MT', 'MS', 'GO', 'DF')
MUNICIPAL_MAP_STATES = ('MT', 'MS')
DIMS_MUN = ['ano', 'uf', 'municipio']
DIMS_TIME = ['ano', 'semana', 'mes', 'escopo', 'sexo', 'faixa_etaria']
VIRAL_COLS = [f'v_{k}' for k in TESTS]
CLASS_ONLY = ['classe_influenza_sem_resultado_laboratorial', 'classe_covid_sem_resultado_laboratorial', 'classe_outro_virus_sem_resultado_laboratorial']
METRICS_CO = CLASS_ONLY + ['notificacoes', 'influenza_a', 'influenza_b', 'influenza_sem_tipo',
              'influenza_a_b', 'a_h1n1', 'a_h3n2', 'a_nao_subtipada',
              'a_nao_subtipavel', 'a_outro_subtipo', 'b_victoria', 'b_yamagata',
              'b_sem_linhagem', 'b_outra_linhagem'] + VIRAL_COLS


def onset_month(raw: pd.DataFrame, year: int) -> pd.Series:
    """Mês do início dos sintomas; 0 = desconhecido ou ano discordante do arquivo."""
    v = col(raw, 'DT_SIN_PRI')
    dates = pd.to_datetime(v.str.slice(0, 10), format='%Y-%m-%d', errors='coerce')
    # Algumas versões históricas podem trazer datas dd/mm/aaaa.
    need = dates.isna() & v.str.match(r'^\d{2}/\d{2}/\d{4}', na=False)
    if need.any():
        dates.loc[need] = pd.to_datetime(v.loc[need].str.slice(0, 10), format='%d/%m/%Y', errors='coerce')
    return dates.dt.month.where(dates.dt.year.eq(year), 0).fillna(0).astype('int8')


def metrics_for_chunk(raw: pd.DataFrame, year: int) -> pd.DataFrame:
    out = pd.DataFrame(index=raw.index)
    out['ano'] = year
    weeks = pd.to_numeric(col(raw, 'SEM_PRI'), errors='coerce')
    out['semana'] = weeks.where(weeks.between(1, 53), 0).fillna(0).astype('int8')
    out['mes'] = onset_month(raw, year)
    out['uf'] = col(raw, 'SG_UF').str.upper().fillna('Não informado')

    # Código municipal de residência no SIVEP = 6 primeiros dígitos do código IBGE.
    # Não utilizar ID_MUNICIP/CO_MUN_NOT, que são municípios de notificação.
    muni = col(raw, 'CO_MUN_RES').str.extract(r'^(\d{6})', expand=False)
    same_state = ((out['uf'].eq('MT') & muni.str.startswith('51', na=False)) |
                  (out['uf'].eq('MS') & muni.str.startswith('50', na=False)) |
                  (out['uf'].eq('GO') & muni.str.startswith('52', na=False)) |
                  (out['uf'].eq('DF') & muni.str.startswith('53', na=False)))
    out['municipio'] = muni.where(same_state, 'Não informado').fillna('Não informado')
    out['sexo'] = col(raw, 'CS_SEXO').str.upper().map({'F': 'Feminino', 'M': 'Masculino'}).fillna('Não informado')
    out['faixa_etaria'] = age_group(raw)
    out['notificacoes'] = 1

    pcr_ok = col(raw, 'POS_PCRFLU').eq('1').fillna(False)
    an_ok = col(raw, 'POS_AN_FLU').eq('1').fillna(False)
    pcr_type = col(raw, 'TP_FLU_PCR')
    an_type = col(raw, 'TP_FLU_AN')
    a = (pcr_ok & pcr_type.eq('1').fillna(False)) | (an_ok & an_type.eq('1').fillna(False))
    b = (pcr_ok & pcr_type.eq('2').fillna(False)) | (an_ok & an_type.eq('2').fillna(False))
    anyflu = pcr_ok | an_ok
    out['influenza_a'] = a.astype('int8')
    out['influenza_b'] = b.astype('int8')
    out['influenza_sem_tipo'] = (anyflu & ~a & ~b).astype('int8')
    out['influenza_a_b'] = (a & b).astype('int8')

    suba = col(raw, 'PCR_FLUASU')
    subb = col(raw, 'PCR_FLUBLI')
    # Só contabilizar subtipo/linhagem se houver tipo confirmado pelo PCR.
    pcr_a = pcr_ok & pcr_type.eq('1').fillna(False)
    pcr_b = pcr_ok & pcr_type.eq('2').fillna(False)
    for name, value in [('a_h1n1', '1'), ('a_h3n2', '2'), ('a_nao_subtipada', '3'),
                        ('a_nao_subtipavel', '4'), ('a_outro_subtipo', '6')]:
        out[name] = (pcr_a & suba.eq(value).fillna(False)).astype('int8')
    for name, value in [('b_victoria', '1'), ('b_yamagata', '2'), ('b_outra_linhagem', '5')]:
        out[name] = (pcr_b & subb.eq(value).fillna(False)).astype('int8')
    out['b_sem_linhagem'] = (pcr_b & ~subb.isin(['1', '2', '5'])).astype('int8')

    for virus, fields in TESTS.items():
        found = [col(raw, c).eq('1').fillna(False) for c in fields if c in raw.columns]
        out[f'v_{virus}'] = (pd.concat(found, axis=1).any(axis=1) if found
                             else pd.Series(False, index=raw.index)).astype('int8')
    # Uma classificação epidemiológica sem exame registrado é apresentada à parte.
    # Teste negativo/inconclusivo NÃO é rotulado como 'sem resultado'.
    valid_result=(col(raw,'PCR_RESUL').isin(['1','2','3']) |
                  col(raw,'RES_AN').isin(['1','2','3'])).fillna(False)
    any_marker=out[VIRAL_COLS].sum(axis=1).gt(0)
    eligible=(~valid_result) & (~any_marker)
    classification=col(raw,'CLASSI_FIN')
    for val, name in [('1','classe_influenza_sem_resultado_laboratorial'),
                      ('5','classe_covid_sem_resultado_laboratorial'),
                      ('2','classe_outro_virus_sem_resultado_laboratorial')]:
        out[name]=(eligible & classification.eq(val).fillna(False)).astype('int8')
    return out


def combine_groups(parts, dims):
    if not parts:
        return pd.DataFrame(columns=dims+METRICS_CO)
    return (pd.concat(parts, ignore_index=True)
            .groupby(dims, observed=True, dropna=False, sort=False)[METRICS_CO]
            .sum().reset_index())


def process_source(path: Path, year: int, chunk_size: int = 60000) -> dict:
    """Agrega Brasil + Centro-Oeste temporalmente, e MT/MS/GO/DF por município."""
    municipalities = []
    timelines = []
    rows = 0
    with path.open('rb') as f:
        reader = pd.read_csv(f, sep=';', encoding='latin1', dtype='string',
                             chunksize=chunk_size, on_bad_lines='error', low_memory=False)
        for batch, raw in enumerate(reader, 1):
            if batch == 1:
                missing = {'SG_UF','CO_MUN_RES','SEM_PRI','DT_SIN_PRI','POS_PCRFLU',
                           'TP_FLU_PCR','PCR_FLUASU','PCR_FLUBLI','POS_AN_FLU','TP_FLU_AN'} - set(raw.columns)
                if missing:
                    raise ValueError(f'{year}: ausentes campos essenciais: {sorted(missing)}')
            rows += len(raw)
            m = metrics_for_chunk(raw, year)
            # Cada linha fonte é computada uma vez em cada escopo hierárquico.
            for scope, condition in [
                ('Brasil', pd.Series(True, index=m.index)),
                ('Centro-Oeste', m['uf'].isin(STATES_CO)),
                ('MT', m['uf'].eq('MT')), ('MS', m['uf'].eq('MS')),
            ]:
                selection = m.loc[condition, ['ano','semana','mes','sexo','faixa_etaria',*METRICS_CO]]
                if selection.empty:
                    continue
                temp = selection.groupby(['ano','semana','mes','sexo','faixa_etaria'], observed=True, sort=False)[METRICS_CO].sum().reset_index()
                temp['escopo'] = scope
                timelines.append(temp[DIMS_TIME+METRICS_CO])
            co = m.loc[m.uf.isin(STATES_CO), DIMS_MUN+METRICS_CO]
            if not co.empty:
                municipalities.append(co.groupby(DIMS_MUN, observed=True, sort=False, dropna=False)[METRICS_CO].sum().reset_index())
            if batch % 12 == 1:
                print(f'  {year}: {rows:,} notificações processadas...', flush=True)
    mun = combine_groups(municipalities, DIMS_MUN)
    tim = combine_groups(timelines, DIMS_TIME)
    assert int(tim.loc[tim.escopo.eq('Brasil'), 'notificacoes'].sum()) == rows, 'Brasil != total fonte'
    assert int(tim.loc[tim.escopo.eq('Centro-Oeste'), 'notificacoes'].sum()) == int(mun.notificacoes.sum()), 'CO != municípios'
    for key in METRICS_CO:
        if (tim[key] > tim['notificacoes']).any() or (mun[key] > mun['notificacoes']).any():
            raise AssertionError(f'Contagem inválida para {key}')
    DATA.mkdir(exist_ok=True, parents=True)
    names = {'municipios': f'municipios_co_{year}.csv.gz',
             'temporal': f'temporal_influenza_{year}.csv.gz'}
    for label, table in [('municipios', mun), ('temporal', tim)]:
        dest = DATA / names[label]
        tmp = dest.with_name(dest.name+'.tmp')
        with gzip.open(tmp, 'wt', encoding='utf-8', compresslevel=8) as fp:
            table.to_csv(fp, index=False)
        tmp.replace(dest)
    return {'ano': year, 'notificacoes_brasil': rows,
            'notificacoes_co': int(mun.notificacoes.sum()),
            'linhas_municipios_agregadas': len(mun),
            'origem_arquivo': path.name, 'sha256_origem': sha256(path),
            'municipios': names['municipios'], 'temporal': names['temporal'],
            'sha256_municipios': sha256(DATA/names['municipios']),
            'sha256_temporal': sha256(DATA/names['temporal'])}


def fetch_municipal_geojson(uf: str, s: requests.Session, force: bool = False) -> None:
    """Obtém polígonos municipais da API de malhas do IBGE (v3), sem usar mapas não oficiais."""
    if uf not in MUNICIPAL_MAP_STATES:
        raise ValueError('Apenas MT e MS são contemplados na malha municipal atual')
    dst = DATA / f'malha_municipios_{uf}.geojson'
    if dst.is_file() and not force:
        print(f'[MALHA MUNICIPAL] {uf} já disponível', flush=True)
        return
    base = 'https://servicodados.ibge.gov.br/api/v3/malhas/estados/' + uf
    r = s.get(base, params={'intrarregiao':'municipio',
                            'formato':'application/vnd.geo+json', 'qualidade':'minima'},
              timeout=(25, 180))
    r.raise_for_status()
    geo = r.json()
    if geo.get('type') != 'FeatureCollection':
        raise ValueError(f'IBGE {uf}: retorno inesperado {geo.get("type")}')
    features = geo.get('features', [])
    if not features:
        raise ValueError(f'IBGE {uf}: malha municipal vazia')
    for f in features:
        props = f.setdefault('properties', {})
        candidates = [f.get('id'), *(props.get(k) for k in
                       ('codarea', 'codmun', 'CD_MUN', 'codigo', 'id', 'cod', 'geocodigo'))]
        codes = [str(c) for c in candidates if c is not None]
        ibge = next((c for c in codes if re.fullmatch(r'\d{7}', c)), None)
        if ibge is None:
            raise ValueError(f'IBGE {uf}: não foi possível identificar o código municipal: {codes}')
        props['codigo_sivep'] = ibge[:6]
    if len({f['properties']['codigo_sivep'] for f in features}) != len(features):
        raise ValueError(f'IBGE {uf}: códigos municipais duplicados')

    # Acrescenta nomenclatura oficial via API de localidades, sem depender de campos da malha.
    u = f'https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios'
    r = s.get(u, timeout=(25, 90))
    r.raise_for_status()
    names = {str(m['id'])[:6]: m['nome'] for m in r.json()}
    for f in features:
        code = f['properties']['codigo_sivep']
        f['properties']['nome'] = names.get(code, code)
    if len(features) != len(names):
        print(f'[AVISO] Malha IBGE {uf}: {len(features)} polígonos, {len(names)} municípios no cadastro.', flush=True)
    dst.parent.mkdir(exist_ok=True, parents=True)
    tmp = dst.with_suffix('.geojson.tmp')
    tmp.write_text(json.dumps(geo, ensure_ascii=False, separators=(',',':')), encoding='utf-8')
    tmp.replace(dst)
    print(f'[MALHA MUNICIPAL] {uf}: {len(features)} polígonos, {dst.stat().st_size/1024:.1f} KiB', flush=True)


def update_metadata(info: dict) -> None:
    # Duas extrações em datas diferentes podem ter contagens diferentes.
    national_manifest = DATA/'manifest.json'
    if national_manifest.exists():
        try:
            national = json.loads(national_manifest.read_text(encoding='utf-8'))
            original = national.get('anos', {}).get(str(info['ano']), {})
            expected = original.get('notificacoes')
            if expected is not None:
                info['notificacoes_cubo_nacional'] = int(expected)
                info['compativel_com_cubo_nacional'] = (int(expected) == int(info['notificacoes_brasil']))
                if not info['compativel_com_cubo_nacional']:
                    print(f'[ATENÇÃO] {info["ano"]}: fonte do complemento tem {info["notificacoes_brasil"]:,} '
                          f'notificações, mas cubo nacional possui {expected:,}. '
                          'As extrações são de snapshots diferentes. Não compare diretamente valores absolutos sem harmonizar a versão.',
                          flush=True)
        except (ValueError, OSError, TypeError) as exc:
            print(f'[AVISO] Não foi possível conferir manifesto nacional: {exc}', flush=True)
    dest = DATA/'centro_oeste_manifest.json'
    meta = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else {
        'versao': '2.0',
        'descricao': 'Dados SIVEP-Gripe, complemento geográfico e tipagem de influenza',
        'fonte': 'https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026',
        'unidade': 'notificações; sem deduplicação interna do SIVEP',
        'inicio_sintomas': 'DT_SIN_PRI para mês, SEM_PRI para semana; mês zero indica inválido/incompatível',
        'residencia': 'CO_MUN_RES e SG_UF, não município de notificação',
        'tipagem': 'somente marcadores positivos de PCR e teste antigênico com tipo 1=A, 2=B',
        'subtipagem': 'PCR_FLUASU: 1=H1N1pdm09, 2=H3N2; PCR_FLUBLI: 1=Victoria, 2=Yamagata',
        'anos': {}, 'escopos_temporais': ['Brasil','Centro-Oeste','MT','MS'],
        'ufs_municipios': list(STATES_CO),
        'granularidade_municipal': 'município + UF + ano; sem idade, sexo, semana ou mês por minimização dos dados',
    }
    meta['anos'][str(info['ano'])] = info
    meta['anos_disponiveis'] = sorted(int(k) for k in meta['anos'] if (DATA / f'temporal_influenza_{k}.csv.gz').exists()
                                      and (DATA / f'municipios_co_{k}.csv.gz').exists())
    meta['gerado_em_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    temp = dest.with_suffix('.json.tmp')
    temp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(dest)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--todos', action='store_true', help='2023 a 2026, sem alterar cubos SRAG')
    ap.add_argument('--anos', type=int, nargs='+', help='Anos a complementar (2023–2026)')
    ap.add_argument('--ano-local', type=int)
    ap.add_argument('--arquivo-local', type=Path)
    ap.add_argument('--malhas', action='store_true', help='Baixar malha UF (se ausente) e municipais MT/MS')
    ap.add_argument('--apenas-malhas', action='store_true')
    ap.add_argument('--reprocessar', action='store_true')
    ap.add_argument('--preservar-brutos', action='store_true')
    args = ap.parse_args(argv)
    if args.ano_local and not args.arquivo_local:
        ap.error('--ano-local requer --arquivo-local')
    if args.arquivo_local and not args.ano_local:
        ap.error('--arquivo-local requer --ano-local')
    s = session()
    if args.malhas or args.apenas_malhas:
        try:
            download_uf_geojson(s)
        except Exception as exc:
            print(f'[AVISO] Não foi possível obter malha nacional UF: {exc}', flush=True)
        for uf in MUNICIPAL_MAP_STATES:
            try:
                fetch_municipal_geojson(uf, s)
            except (requests.RequestException, ValueError, OSError) as exc:
                if args.apenas_malhas:
                    raise
                print(f'[AVISO] Malha municipal {uf} indisponível: {exc}. Dados serão preparados; reexecute depois --apenas-malhas.', flush=True)
    if args.apenas_malhas:
        return
    if args.arquivo_local:
        if args.ano_local not in YEARS_CO:
            ap.error('Ano local deve ser 2023–2026')
        item = process_source(args.arquivo_local, args.ano_local)
        item['origem'] = 'arquivo_local'
        update_metadata(item)
        print(f'[CONCLUÍDO] {args.ano_local}', flush=True)
        return
    years = list(YEARS_CO) if args.todos else args.anos
    if not years:
        ap.error('Informe --todos, --anos ou --arquivo-local, ou --apenas-malhas')
    for year in years:
        if year not in YEARS_CO:
            ap.error(f'Ano fora do intervalo de 2023 a 2026: {year}')
        meta_path = DATA/'centro_oeste_manifest.json'
        prev = json.loads(meta_path.read_text(encoding='utf-8')).get('anos',{}).get(str(year),{}) if meta_path.exists() else {}
        valid = (prev.get('origem','').startswith('https://') and all(
            (DATA/f'{prefix}_{year}.csv.gz').exists()
            for prefix in ('municipios_co','temporal_influenza')))
        if valid and not args.reprocessar:
            print(f'[PULAR] {year} já preparado de fonte oficial', flush=True)
            continue
        url = official_url(year, s)
        src = CACHE/Path(urlparse(url).path).name
        print(f'[DOWNLOAD] {year}: {url}', flush=True)
        download(url, src, s)
        print(f'[AGREGAÇÃO] {year}', flush=True)
        item = process_source(src, year)
        item['origem'] = url
        update_metadata(item)
        print(f'[OK] {year}: {item["notificacoes_co"]:,} notificações na região', flush=True)
        if not args.preservar_brutos:
            src.unlink(missing_ok=True)
    print('[CONCLUÍDO] Complemento offline preparado. Inclua os novos arquivos da pasta data/ no GitHub.', flush=True)

if __name__ == '__main__':
    main()
