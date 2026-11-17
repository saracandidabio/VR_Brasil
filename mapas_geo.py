"""Mapas coropléticos responsivos do observatório SRAG.

As malhas GeoJSON são publicadas em data/ e possuem coordenadas WGS84.
O mapa usa MapLibre (choropleth_map), não `geo` (choropleth), para evitar
comportamentos de fitbounds em alguns navegadores.
"""
from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
    extra_hover_cols: dict | None = None,
    legend_ticks: list | None = None,
    legend_labels: list | None = None,
    legend_title: str = 'Registros',
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
        hover_data={code_col:False, value_col:False, **(extra_hover_cols or {})},
        color_continuous_scale=SCALE,
        range_color=(0,max(float(a[value_col].max()),1)),
        labels={value_col:'Registros'},
        map_style=style,
        center=params['center'], zoom=params['zoom'],
        opacity=0.89,
        title=title or None,
    )
    fig.update_traces(marker_line_color=line_color, marker_line_width=line_width, selector=dict(type='choroplethmap'))
    # Em versões recentes do Plotly, hover_data do choropleth_map pode deixar
    # o template sem valores: construir tooltip explicitamente a partir da UF/município.
    hover_field = next(iter(extra_hover_cols)) if extra_hover_cols else value_col
    lookup = a.set_index(code_col)[hover_field].to_dict()
    for tr in fig.data:
        if tr.type == 'choroplethmap':
            tr.customdata = [[float(lookup.get(str(loc), 0))] for loc in tr.locations]
            tr.hovertemplate = ('<b>%{hovertext}</b><br>' +
                                ('Registros' if extra_hover_cols else legend_title) +
                                ': %{customdata[0]:,.0f}<extra></extra>')
    fig.update_layout(
        coloraxis_colorbar=dict(title=legend_title, thickness=13, len=0.68,
                                tickvals=legend_ticks, ticktext=legend_labels),
        font_family='Arial', font_size=12,
        margin=dict(l=0, r=0, t=36 if title else 0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        uirevision=None,
    )
    return fig


def state_boundary_overlay(fig, state_geo:dict | None, selected_ufs: list[str] | None=None):
    """Mostra limites estaduais por cima das malhas municipais (sem recolorir)."""
    if not state_geo:
        return fig
    feats=state_geo.get('features',[])
    if not feats:return fig
    key=next((x for x in ('sigla','SIGLA','uf','UF') if x in feats[0].get('properties',{})),None)
    if not key:return fig
    selected=set(selected_ufs or [])
    def lines(parts):
        lons=[];lats=[]
        for ft in parts:
            g=ft.get('geometry') or {}
            if g.get('type')=='Polygon':polys=[g.get('coordinates',[])]
            elif g.get('type')=='MultiPolygon':polys=g.get('coordinates',[])
            else:continue
            for polygon in polys:
                if polygon:
                    for xy in polygon[0]:
                        if len(xy)>1:
                            lons.append(xy[0]);lats.append(xy[1])
                    lons.append(None);lats.append(None)
        return lons,lats
    if selected:
        others=[x for x in feats if str(x['properties'].get(key)) not in selected]
        if others:
            lon,lat=lines(others)
            fig.add_trace(go.Scattermap(lon=lon,lat=lat,mode='lines',
                            line=dict(color='#586774',width=1.4),
                            hoverinfo='skip',showlegend=False,name='Limites das UFs'))
    main=[x for x in feats if not selected or str(x['properties'].get(key)) in selected]
    lon,lat=lines(main)
    if lon:
        fig.add_trace(go.Scattermap(lon=lon,lat=lat,mode='lines',
                        line=dict(color='#394e5a',width=2.2 if selected else 1.5),
                        hoverinfo='skip',showlegend=False,name='Limites estaduais'))
    return fig
