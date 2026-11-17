"""Exportação científica do observatório: PNG com 800 dpi reais.

A imagem é redesenhada em Matplotlib com os mesmos dados mostrados no Plotly.
Isso evita dependência do Google Chrome/Kaleido no Streamlit Community Cloud.
O arquivo PNG incorpora metadados físicos de resolução (pHYs: 800 dpi).
"""
from __future__ import annotations

from io import BytesIO
import math
import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Polygon as MPLPolygon
from matplotlib.collections import PatchCollection
from matplotlib.ticker import MaxNLocator
from escala_municipal import escala

COLORS = ['#23617D','#D68952','#287C73','#C75D67','#8F8FD0','#8B6B48','#648EA1','#c2a35f']
MAP_COLORS = ['#e7f2f8','#b5d7e5','#7bacbf','#4088a6','#195a79','#103c53']


def _parts(geometry):
    if geometry['type'] == 'Polygon':
        polys = [geometry['coordinates']]
    elif geometry['type'] == 'MultiPolygon':
        polys = geometry['coordinates']
    else:
        return
    for poly in polys:
        if poly and len(poly[0]) >= 3:
            yield np.asarray(poly[0], dtype=float)


def _render_outline(ax, geo, *, edgecolor="#7d8790", linewidth=.65, alpha=.9):
    patches=[]
    for feature in geo.get("features", []):
        for coords in _parts(feature["geometry"]):
            patches.append(MPLPolygon(coords, closed=True, fill=False))
    if not patches:
        return
    collection = PatchCollection(patches, facecolor="none", edgecolor=edgecolor,
                                 linewidth=linewidth, alpha=alpha, antialiased=True)
    ax.add_collection(collection)


def _render_map(ax, geo, data_by_code, id_prop, label='Registros', *,
                outline_geo=None, selected_outline_geo=None, escala_cor='Linear'):
    patches, values = [], []
    for feature in geo.get('features', []):
        code = str(feature['properties'][id_prop])
        value = float(data_by_code.get(code, 0))
        for coords in _parts(feature['geometry']):
            patches.append(MPLPolygon(coords, closed=True))
            values.append(value)
    if not patches:
        ax.text(.5,.5,'Nenhum polígono disponível',ha='center',transform=ax.transAxes)
        return
    transformed, tickvals, ticklabels = escala(values, escala_cor)
    v_max = max(transformed) if len(transformed) else 1
    norm = Normalize(vmin=0, vmax=max(v_max,1))
    # Branco para ausência de notificação; azul contrastante para municípios com valores.
    cmap = LinearSegmentedColormap.from_list('srag', ['#ffffff','#a8d4e1','#649fb9','#246b91','#083a56'])
    collection = PatchCollection(patches, cmap=cmap, norm=norm,
                                  linewidth=.68 if len(patches)>50 else .9,
                                  edgecolor='#536b79', antialiased=True)
    collection.set_array(np.asarray(transformed))
    ax.add_collection(collection)
    if outline_geo is not None:
        _render_outline(ax, outline_geo, edgecolor='#8a96a0', linewidth=.9, alpha=.92)
    if selected_outline_geo is not None:
        _render_outline(ax, selected_outline_geo, edgecolor='#4b5c68', linewidth=1.35, alpha=.96)
    ax.autoscale_view()
    x0,y0,x1,y1=collection.get_datalim(ax.transData).extents
    dx=max(x1-x0, .05);dy=max(y1-y0,.05)
    ax.set_xlim(x0-dx*.04,x1+dx*.04)
    ax.set_ylim(y0-dy*.05,y1+dy*.05)
    latitude=(y0+y1)/2
    ax.set_aspect(1/max(math.cos(math.radians(latitude)),.3))
    ax.set_xlabel('Longitude (°)',fontsize=9)
    ax.set_ylabel('Latitude (°)',fontsize=9)
    ax.grid(alpha=.13,linestyle='--',linewidth=.4)
    cbar=ax.figure.colorbar(ScalarMappable(norm=norm,cmap=cmap),ax=ax,fraction=.035,pad=.015,shrink=.83)
    cbar.set_label(label+' · '+escala_cor.lower(),fontsize=9)
    cbar.set_ticks(tickvals)
    cbar.set_ticklabels(ticklabels)
    cbar.ax.tick_params(labelsize=7)


def mapa_png(geo, valores:pd.DataFrame, *, col_codigo='Código',col_valor='Registros',
             id_prop='codigo_sivep',titulo='SRAG · Distribuição municipal', dpi=800,
             outline_geo=None, selected_outline_geo=None, escala_cor='Linear'):
    """Mapa sem dependência de navegador/cartografia externa; PNG com dpi embutido."""
    table=valores.copy()
    table[col_codigo]=table[col_codigo].astype('string').str.strip()
    table[col_valor]=pd.to_numeric(table[col_valor],errors='coerce').fillna(0)
    lookup=dict(zip(table[col_codigo],table[col_valor]))
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':9,
                         'axes.spines.top':False,'axes.spines.right':False}):
        fig,ax=plt.subplots(figsize=(8.2,6.3),facecolor='white')
        _render_map(ax,geo,lookup,id_prop, outline_geo=outline_geo,
                    selected_outline_geo=selected_outline_geo, escala_cor=escala_cor)
        fig.suptitle(titulo,fontsize=13,fontweight='semibold',y=.985)
        fig.subplots_adjust(left=.09,right=.91,top=.93,bottom=.10)
        bio=BytesIO()
        fig.savefig(bio,dpi=dpi,format='png',facecolor='white',metadata={'Software':'Observatório SRAG Brasil'})
        plt.close(fig)
    return bio.getvalue()


def figura_png(fig_plotly, *, title='', dpi=800):
    """Exporta os gráficos Plotly usados no painel como PNG científico de 800 dpi.

    Suporta linhas, barras verticais/horizontais, setores e mapas coropléticos.
    Usa as matrizes da figura em vez de fotografar a tela. A formatação estática
    prioriza legendas legíveis e exportação sem sobreposição.
    """
    traces=list(fig_plotly.data)
    if not traces:
        raise ValueError('Figura sem dados')
    t=traces[0].type
    if t == 'choroplethmap':
        trace=traces[0]
        locs=[str(x) for x in trace.locations]
        vals=np.asarray(trace.z,dtype=float)
        key=trace.featureidkey.split('.')[-1]
        lookup=dict(zip(locs,vals))
        with plt.rc_context({'font.family':'DejaVu Sans','font.size':9}):
            fig,ax=plt.subplots(figsize=(8.2,6.2),facecolor='white')
            _render_map(ax,trace.geojson,lookup,key)
            fig.suptitle(title or 'Distribuição espacial da SRAG',fontsize=13,fontweight='semibold',y=.985)
            fig.subplots_adjust(left=.1,right=.92,top=.94,bottom=.1)
            bio=BytesIO();fig.savefig(bio,dpi=dpi,format='png',facecolor='white')
            plt.close(fig)
        return bio.getvalue()
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':9,
                         'axes.spines.top':False,'axes.spines.right':False}):
        fig,ax=plt.subplots(figsize=(8.4,5.3),facecolor='white')
        if t == 'pie':
            tr=traces[0]
            vals=[float(v) for v in tr.values]
            labels=[str(v) for v in tr.labels]
            ax.pie(vals,labels=None,autopct=lambda v: f'{v:.1f}%' if v>=2 else '',
                   startangle=90,colors=COLORS[:len(vals)],pctdistance=.83,
                   wedgeprops={'linewidth':.7,'edgecolor':'white','width':.65 if tr.hole else 1})
            ax.legend(labels,bbox_to_anchor=(1.02,1),loc='upper left',frameon=False,fontsize=8)
            ax.set_aspect('equal')
            fig.subplots_adjust(right=.75,top=.88,bottom=.12)
        elif t == 'bar':
            orientation=getattr(traces[0],'orientation',None)
            horizontal=orientation=='h'
            if horizontal:
                # Barras horizontais usam categorias na ordenação original.
                if len(traces)!=1:
                    raise ValueError('Barras horizontais múltiplas não disponíveis')
                tr=traces[0]
                y=[str(v) for v in tr.y]
                values=np.asarray(tr.x,dtype=float)
                colors=[COLORS[0]]*len(values)
                ax.barh(np.arange(len(y)),values,color=colors,height=.75)
                ax.set_yticks(range(len(y)),y,fontsize=8)
                ax.invert_yaxis()
                ax.set_xlim(0,max(1,float(np.nanmax(values)))*1.18)
                for i,value in enumerate(values):
                    ax.text(value+max(values)*.012,i,f'{value:,.0f}',va='center',fontsize=8)
                ax.set_xlabel('Registros')
                fig.subplots_adjust(left=.35,right=.93,top=.87,bottom=.13)
            else:
                cats=[]
                for tr in traces:
                    for cat in tr.x:
                        if str(cat) not in cats:cats.append(str(cat))
                x=np.arange(len(cats))
                m=len(traces)
                width=.78/max(m,1)
                for j,tr in enumerate(traces):
                    v=dict(zip((str(c) for c in tr.x),[float(y) for y in tr.y]))
                    vals=[v.get(c,0) for c in cats]
                    ax.bar(x+(j-(m-1)/2)*width,vals,width=width,
                           label=str(tr.name) if tr.name else None,color=COLORS[j%len(COLORS)])
                stride=max(1,math.ceil(len(cats)/15))
                positions=list(range(0,len(cats),stride))
                ax.set_xticks(positions,[cats[i] for i in positions],rotation=40,ha='right',fontsize=8)
                ax.set_xlim(-.6,len(cats)-.4)
                if m>1:ax.legend(frameon=False,loc='upper left',bbox_to_anchor=(0,1.02),ncol=min(m,3))
                ax.set_ylabel('Registros')
                fig.subplots_adjust(left=.1,right=.95,top=.85,bottom=.24)
        else:
            # Unir categorias para alinhar séries que possuem coberturas diferentes
            # (p. ex., VSR 2019–2026 e INFA/INFB apenas 2023–2026).
            all_x=[v for tr in traces for v in (list(tr.x) if tr.x is not None else [])]
            numeric=bool(all_x) and all(isinstance(v,(int,float,np.number)) for v in all_x)
            cats=[] if numeric else sorted({str(v) for v in all_x})
            indices={cat:i for i,cat in enumerate(cats)}
            for i,tr in enumerate(traces):
                xx=list(tr.x) if tr.x is not None else list(range(len(tr.y)))
                yy=[float(y) if y is not None else np.nan for y in tr.y]
                if not numeric:
                    x=[indices[str(v)] for v in xx]
                else:
                    x=np.asarray(xx,dtype=float)
                name=str(tr.name) if tr.name else f'Série {i+1}'
                color=getattr(getattr(tr,'line',None),'color',None)
                if not isinstance(color,str):color=COLORS[i%len(COLORS)]
                ax.plot(x,yy,color=color,linewidth=1.55,label=name)
            if not numeric and cats:
                stride=max(1,math.ceil(len(cats)/13))
                inds=list(range(0,len(cats),stride))
                ax.set_xticks(inds,[cats[k] for k in inds],rotation=38,ha='right',fontsize=8)
            if len(traces)>1:
                ncol=min(3,len(traces))
                ax.legend(loc='upper center',bbox_to_anchor=(.5,1.18),frameon=False,
                          fontsize=8,ncol=ncol)
            ax.set_ylabel('Detecções / notificações')
            fig.subplots_adjust(left=.10,right=.96,top=.81,bottom=.23)
        ax.grid(axis='y',alpha=.19,linewidth=.7)
        if title:
            fig.suptitle(re.sub(r'<[^>]+>','',title),fontsize=12.5,fontweight='semibold',y=.98)
        bio=BytesIO()
        fig.savefig(bio,dpi=dpi,format='png',facecolor='white',metadata={'Software':'Observatório SRAG Brasil'})
        plt.close(fig)
    return bio.getvalue()
