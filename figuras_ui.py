"""Gráficos sem legendas sobrepostas e botão de exportação PNG científica."""
from __future__ import annotations
import hashlib
import re
import unicodedata

import streamlit as st
from exportacao import figura_png


def _slug(value: str):
    normalized = unicodedata.normalize('NFKD',value)
    normalized = normalized.encode('ascii','ignore').decode('ascii').lower()
    return re.sub('[^a-z0-9]+','_',normalized).strip('_')[:42] or 'grafico'


def chart(fig, height: int = 400):
    """Exibe figura e disponibiliza PNG 800 dpi reais por exportação sob demanda.

    O exportador faz redesenho científico estático com os mesmos dados do gráfico;
    não captura a tela e não exige Chrome ou Kaleido no servidor.
    """
    raw_title=fig.layout.title.text if fig.layout.title is not None else None
    title=re.sub('<[^>]*>','',raw_title or '').strip()
    if title:
        st.markdown(f'**{title}**')
    legend=any(getattr(tr,'showlegend',True) is not False and tr.name for tr in fig.data)
    map_fig=any(tr.type=='choroplethmap' for tr in fig.data)
    fig.update_layout(
        title=None,height=height,font_family='Arial',font_size=12,
        paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=22,r=28,t=112 if legend else 18,b=78 if not map_fig else 24),
        legend=dict(orientation='h',x=0,y=1.12,xanchor='left',yanchor='bottom',
                    font=dict(size=10.5),title_text=''),
    )
    st.plotly_chart(fig,use_container_width=True,
        config={'displaylogo':False,'scrollZoom':False,
                'modeBarButtonsToRemove':['toImage']})
    ix=st.session_state.get('_v4_chart_ix',0)+1
    st.session_state['_v4_chart_ix']=ix
    prefix=f'v4_export_{ix}'
    figure_hash=hashlib.sha256((fig.to_json()+title).encode('utf-8')).hexdigest()[:16]
    storage=f'{prefix}_png'
    with st.expander('Exportar figura · PNG 800 dpi'):
        st.caption('Imagem estática redesenhada a partir dos dados do gráfico, com resolução física de 800 dpi (apropriada para impressão).')
        if st.button('Preparar PNG em 800 dpi',key=f'{prefix}_preparar'):
            with st.spinner('Gerando arquivo de alta resolução...'):
                try:
                    st.session_state[storage]=(figure_hash,figura_png(fig,title=title,dpi=800))
                except Exception as exc:
                    st.warning(f'Não foi possível preparar este gráfico: {exc}')
        cached=st.session_state.get(storage)
        if cached and cached[0]==figure_hash:
            st.download_button('Baixar PNG · 800 dpi',data=cached[1],
                  file_name=f'srag_{ix:02}_{_slug(title)}_800dpi.png',
                  mime='image/png',key=f'{prefix}_download')
