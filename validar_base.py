"""Valida a coerência e os arquivos preparados, sem consultar a internet."""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import sys
import pandas as pd

BASE=Path(__file__).resolve().parent
DATA=BASE/'data'
EXPECTED=set(range(2019,2027))

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def validate(required_all=True):
    m=json.loads((DATA/'manifest.json').read_text(encoding='utf-8'))
    years=set(map(int,m.get('anos_disponiveis',[])))
    if required_all and years!=EXPECTED:
        raise AssertionError('Base INCOMPLETA. Anos ausentes: '+str(sorted(EXPECTED-years)))
    total=0
    for year in sorted(years):
        p=DATA/f'cubo_srag_{year}.csv.gz'
        if not p.exists():raise AssertionError(f'Falta {p}')
        if p.stat().st_size>=95_000_000:
            raise AssertionError(f'Arquivo acima do limite seguro para GitHub: {p}')
        entry=m['anos'][str(year)]
        assert sha256(p)==entry['sha256_agregado'],f'SHA256 alterado: {year}'
        d=pd.read_csv(p)
        assert set(['ano','semana','uf','sexo','faixa_etaria','notificacoes']).issubset(d.columns)
        assert (d.ano==year).all()
        assert (d.semana.between(0,53)).all()
        assert (d.notificacoes>=1).all()
        assert not d.duplicated(['ano','semana','uf','sexo','faixa_etaria']).any()
        assert int(d.notificacoes.sum())==entry['notificacoes']
        for field in [col for col in d if col.startswith(('v_','obito_','uti_','classe_')) or col in ('com_deteccao','codeteccoes','hospitalizados','uti','obitos_srag','desfecho_conhecido')]:
            assert (d[field]<=d.notificacoes).all(),f'{field} excede n {year}'
        total+=int(d.notificacoes.sum())
        print(f'OK {year}: {len(d):,} grupos; {entry["notificacoes"]:,} notificações; {p.stat().st_size/1e6:.2f} MB')
    assert m['notificacoes_total']==total
    assert m['completo_2019_2026']==(years==EXPECTED)
    print('VERIFICAÇÃO CONCLUÍDA | anos=',len(years),'| notificações=',f'{total:,}')
    return True

if __name__=='__main__':validate('--permitir-parcial' not in sys.argv)
