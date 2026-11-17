"""Mapas coropléticos responsivos do observatório SRAG.

As malhas GeoJSON são publicadas em data/ e possuem coordenadas WGS84.
O mapa usa MapLibre (choropleth_map), não `geo` (choropleth), para evitar
comportamentos de fitbounds em alguns navegadores.
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.express as px

SCALE = ['#e7f2f8','#b5d7e5','#7bacbf','#4088a6','#195a79','#103c53']
# Centro e zoom iniciais para janela de aproximadamente 800px.
CAMERAS = {
    'BR': {'center': {'lat': -14.7, 'lon': -52.7}, 'zoom': 2.75},
    'MT': {'center': {'lat': -12.8, 'lon': -55.9}, 'zoom': 5.1},
    'MS': {'center': {'lat': -20.7, 'lon': -54.6}, 'zoom': 5.0},
    'MT+MS': {'center': {'lat': -16.8, 'lon': -55.3}, 'zoom': 4.25},
}


def geometry_valid(geo: dict, id_prop: str) -> bool:
    """Verifica a integridade estrutural mínima e IDs não duplicados."""
    if geo.get('type') != 'FeatureCollection' or not geo.get('features'):
        return False
    ids = []
    for feature in geo['features']:
        props = feature.get('properties') or {}
        geometry = feature.get('geometry') or {}
        if not props.get(id_prop) or geometry.get('type') not in ('Polygon', 'MultiPolygon') or not geometry.get('coordinates'):
            return False
        ids.append(str(props[id_prop]))
    return len(ids) == len(set(ids))


def _walk_lonlat(part):
    """Pares WGS84 em polígonos e multipolígonos sem depender de GeoPandas."""
    if isinstance(part, (tuple, list)) and len(part)>=2 and all(isinstance(x,(int,float)) for x in part[:2]):
        yield float(part[0]), float(part[1])
    elif isinstance(part,(tuple,list)):
        for item in part:
            yield from _walk_lonlat(item)


def camera_from_polygons(geo: dict, *, viewport=(800,590)) -> dict:
    """Centraliza e enquadra a região sem depender do fitbounds do navegador."""
    xy = [pair for feature in geo['features'] for pair in _walk_lonlat(feature['geometry']['coordinates'])]
    if not xy:
        return CAMERAS['BR']
    lons,lats=zip(*xy)
    left,right=min(lons),max(lons)
    south,north=min(lats),max(lats)
    center={'lat':(south+north)/2,'lon':(left+right)/2}
    longitude_span=max(right-left,0.2)
    # Extensão vertical correta na projeção Web Mercator.
    def merc(lat):
        lat=math.radians(max(-85,min(85,lat)))
        return math.log(math.tan(math.pi/4 + lat/2))
    span_merc=max(abs(merc(north)-merc(south)),0.005)
    w,h=viewport
    zx=math.log2((360*w)/(512*longitude_span*1.22))
    zy=math.log2((h*2*math.pi)/(512*span_merc*1.22))
    return {'center':center,'zoom':max(1.8,min(8.5,min(zx,zy)-0.18))}


def choropleth_map(
    df: pd.DataFrame,
    geo: dict,
    *,
    code_col: str,
    id_prop: str,
    name_col: str,
    value_col: str,
    scope: str = 'BR',
    style: str = 'carto-positron',
    auto_camera: bool = False,
    camera_geo: dict | None = None,
    line_color: str = '#637b8a',
    line_width: float = 0.65,
    title: str = '',
):
    """Retorna uma figura maplibre, usando ligações explícitas com GeoJSON.

    O conjunto de dados precisa ter um registro por polígono. Valores ausentes
    são zeros SOMENTE quando o polígono representa localidade sem registros no
    subconjunto; períodos incompletos não são preenchidos como 0.
    """
    if not geometry_valid(geo, id_prop):
        raise ValueError(f'Malha sem IDs únicos/projeção válida para {id_prop}')
    a = df.copy()
    a[code_col] = a[code_col].astype(str)
    a[value_col] = pd.to_numeric(a[value_col], errors='coerce').fillna(0)
    locations = set(a[code_col])
    geo_ids = {str(f['properties'][id_prop]) for f in geo['features']}
    missing = locations - geo_ids
    if missing:
        raise ValueError(f'{len(missing)} localidades não correspondem à malha: {sorted(missing)[:5]}')
    cam_source = camera_geo if camera_geo is not None else geo
    params = camera_from_polygons(cam_source) if auto_camera else CAMERAS[scope]
    fig = px.choropleth_map(
        a, geojson=geo,
        locations=code_col,
        featureidkey=f'properties.{id_prop}',
        color=value_col,
        hover_name=name_col,
        hover_data={code_col:False, value_col:':,'},
        color_continuous_scale=SCALE,
        labels={value_col:'Registros'},
        map_style=style,
        center=params['center'], zoom=params['zoom'],
        opacity=0.89,
        title=title or None,
    )
    fig.update_traces(marker_line_color=line_color, marker_line_width=line_width, selector=dict(type='choroplethmap'))
    fig.update_layout(
        coloraxis_colorbar=dict(title='Registros', thickness=12, len=0.72),
        font_family='Arial', font_size=12,
        margin=dict(l=0, r=0, t=36 if title else 0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        uirevision=None,
    )
    return fig
