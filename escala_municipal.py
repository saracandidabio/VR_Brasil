"""Contrastes para coropléticos municipais sem alterar as contagens reais."""
from __future__ import annotations
import numpy as np


def escala(valores, metodo='Quantis'):
    """Retorna valores visuais, posições da legenda e rótulos em notificações reais."""
    x = np.maximum(np.nan_to_num(np.asarray(valores, dtype=float), nan=0.0), 0)
    positives = x[x > 0]
    if not len(positives):
        return np.zeros_like(x), [0], ['0']
    if metodo == 'Quantis':
        # Os mesmos valores nunca recebem cores diferentes; zeros têm uma cor exclusiva.
        cuts = np.unique(np.quantile(positives, [.2, .4, .6, .8]))
        cuts = cuts[cuts < positives.max()]
        visual = np.where(x > 0, np.searchsorted(cuts, x, side='left') + 1, 0).astype(float)
        ticks = [0] + list(range(1, int(visual.max()) + 1))
        labels = ['0']
        for band in ticks[1:]:
            observed = x[visual == band]
            lo, hi = int(observed.min()), int(observed.max())
            labels.append(f'{lo:,}–{hi:,}' if lo != hi else f'{lo:,}')
        return visual, ticks, labels
    sample = sorted(set([0.0, *np.quantile(positives, [.25,.5,.75,1]).tolist()]))
    if metodo == 'Raiz quadrada':
        return np.sqrt(x), list(np.sqrt(sample)), [f'{int(v):,}' for v in sample]
    return x.copy(), sample, [f'{int(v):,}' for v in sample]
