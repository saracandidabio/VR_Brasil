"""Validação offline do pacote completo para publicação no GitHub.

Valida integridade dos oito cubos, séries complementares 2023-2026 e GeoJSON.
Não baixa dados nem altera os arquivos.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pandas as pd

from validar_base import validate as validate_national

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate_all() -> bool:
    assert validate_national(required_all=True), 'Cubo nacional inválido'
    national = json.loads((DATA / 'manifest.json').read_text(encoding='utf-8'))
    meta = json.loads((DATA / 'centro_oeste_manifest.json').read_text(encoding='utf-8'))
    regional_years = {2023, 2024, 2025, 2026}
    actual = set(map(int, meta.get('anos_disponiveis', [])))
    assert actual == regional_years, f'Anos faltantes no Centro-Oeste: {regional_years - actual}'
    scopes = {'Brasil','Centro-Oeste','MT','MS'}
    for year in sorted(regional_years):
        info = meta['anos'][str(year)]
        temporal = DATA / f'temporal_influenza_{year}.csv.gz'
        municipios = DATA / f'municipios_co_{year}.csv.gz'
        for path, field in ((temporal, 'sha256_temporal'),(municipios, 'sha256_municipios')):
            assert path.is_file(), f'Arquivo ausente: {path}'
            assert checksum(path) == info[field], f'SHA256 divergente: {path.name}'
            assert path.stat().st_size < 95_000_000, f'Arquivo muito grande: {path.name}'
        assert national['anos'][str(year)]['sha256_original'] == info['sha256_origem'], f'Snapshots diferentes em {year}'
        t = pd.read_csv(temporal)
        m = pd.read_csv(municipios, dtype={'municipio':'string','uf':'string'})
        assert set(t['escopo']) == scopes, f'Escopos incompletos: {year}'
        assert (t['ano'] == year).all() and (m['ano'] == year).all(), f'Ano inválido: {year}'
        grouped = t.groupby('escopo',observed=True)['notificacoes'].sum()
        assert int(grouped['Brasil']) == national['anos'][str(year)]['notificacoes'], f'Brasil inconsistente: {year}'
        assert int(grouped['Centro-Oeste']) == int(m['notificacoes'].sum()) == info['notificacoes_co'], f'CO inconsistente: {year}'
        assert int(grouped['MT']) == int(m.loc[m.uf.eq('MT'),'notificacoes'].sum()), f'MT inconsistente: {year}'
        assert int(grouped['MS']) == int(m.loc[m.uf.eq('MS'),'notificacoes'].sum()), f'MS inconsistente: {year}'
        print(f'OK complemento {year}: {int(grouped["Centro-Oeste"]):,} notificações CO')
    for filename, expected in [('malha_uf.geojson',27),
                               ('malha_municipios_MT.geojson',141),
                               ('malha_municipios_MS.geojson',79)]:
        path = DATA / filename
        assert path.is_file(), f'GeoJSON ausente: {filename}'
        features = json.loads(path.read_text(encoding='utf-8'))['features']
        assert len(features) == expected, f'Malha incompleta em {filename}: {len(features)} geometrias'
        assert all(feature.get('geometry') for feature in features), f'Geometria ausente em {filename}'
        print(f'OK malha {filename}: {len(features)} polígonos')
    assert 'https://vrbrasil.streamlit.app/' in (ROOT / 'README.md').read_text(encoding='utf-8')
    print('PACOTE VALIDADO: 2019–2026 + Centro-Oeste 2023–2026 + GeoJSON + README')
    return True


if __name__ == '__main__':
    validate_all()
