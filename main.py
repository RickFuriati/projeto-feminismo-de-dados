import pandas as pd 
import numpy as np

from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit.components.v1 import html
import branca

from branca.element import Template, MacroElement
from folium import Element
from streamlit import components
import plotly.express as px

def find_coordinates(institutos):
    geolocator = Nominatim(user_agent="unicamp_geocoder")

    # Rate limiter para evitar bloqueio da API (máx 1 req/s recomendado)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    # Criar listas para armazenar resultados
    nomes = []
    latitudes = []
    longitudes = []

    for inst in institutos:
        location = geocode(str(inst).strip() + ", Campinas, São Paulo, Brazil")  # melhora a precisão
        if location:
            nomes.append(inst)
            latitudes.append(location.latitude)
            longitudes.append(location.longitude)
        else:
            nomes.append(inst)
            latitudes.append(None)
            longitudes.append(None)

    # Criar DataFrame
    df_coords = pd.DataFrame({
        "instituto": nomes,
        "latitude": latitudes,
        "longitude": longitudes
    })

    df_coords.loc[df_coords['instituto'] == 'FECFAU', ['latitude', 'longitude']] = [-22.8184, -47.0604]
    df_coords.loc[df_coords['instituto'] == 'FCA', ['latitude', 'longitude']] = [-22.55742,-47.4345065]
    return df_coords


data_path = './Dados/'

area_df = pd.read_excel(data_path + 'valor_cnpq_por_area.xlsx')
genero_df= pd.read_excel(data_path + 'valor_cnpq_por_raca_genero.xlsx')

consolidado_df= pd.read_excel(data_path + 'valor_cnpq_consolidado_v2.xlsx')

institutos=consolidado_df['instituto'].unique()
institutos=np.delete(institutos, [2,7])

campi=consolidado_df['15_Cidade'].unique()
campi=np.delete(campi, 0)

#coords_df=find_coordinates(institutos)
#coords_df.to_csv(data_path + 'coords_institutos.csv', index=False)
coords_df = pd.read_csv(data_path + 'coords_institutos.csv')
coords_piracicaba = coords_df.copy()
coords_piracicaba['latitude'] = -22.7018139
coords_piracicaba['longitude'] = -47.6503615

coords_limeira= coords_df.copy()
coords_limeira['latitude'] = -22.5551787
coords_limeira['longitude'] = -47.4339062

df_campinas = consolidado_df[consolidado_df['15_Cidade'] == 'Campinas'][['instituto', 'ano', 'valor2', '05 _Área', '08_Sexo', '09_Cor ou Raça']]
df_limeira  = consolidado_df[consolidado_df['15_Cidade'] == 'Limeira'][['instituto', 'ano', 'valor2', '05 _Área', '08_Sexo', '09_Cor ou Raça']]
df_piracicaba     = consolidado_df[consolidado_df['15_Cidade'] == 'Piracicaba'][['instituto', 'ano', 'valor2', '05 _Área', '08_Sexo', '09_Cor ou Raça']]

st.set_page_config(layout="wide")
st.title("Mapas de Investimentos da Unicamp")

anos_disponiveis = sorted(df_campinas["ano"].unique())
ano_selecionado = st.slider(
    "Selecione o ano",
    min_value=min(anos_disponiveis),
    max_value=max(anos_disponiveis),
    value=max(anos_disponiveis),
    step=1
)

# ============================================
# 🔹 Filtros adicionais no topo
# ============================================
col_f1, col_f2, col_f3 = st.columns(3)

sexo_select = col_f1.multiselect(
    "Sexo", df_campinas["08_Sexo"].unique()
)
raca_select = col_f2.multiselect(
    "Raça", df_campinas["09_Cor ou Raça"].unique()
)
area_select = col_f3.multiselect(
    "Área do conhecimento", df_campinas["05 _Área"].unique()
)

def aplicar_filtros(df):
    # Se não selecionar nada, usar todos os valores disponíveis
    sexo = sexo_select if sexo_select else df["08_Sexo"].unique()
    raca = raca_select if raca_select else df["09_Cor ou Raça"].unique()
    area = area_select if area_select else df["05 _Área"].unique()

    return df[
        (df["ano"] == ano_selecionado) &
        (df["08_Sexo"].isin(sexo)) &
        (df["09_Cor ou Raça"].isin(raca)) &
        (df["05 _Área"].isin(area))
    ]

camp_filtered = aplicar_filtros(df_campinas)
lime_filtered = aplicar_filtros(df_limeira)
pira_filtered = aplicar_filtros(df_piracicaba)

# ============================================
# 🔹 Preparar DataFrame agregado
# ============================================
def agregate_df(df, coords):
    df_agregado = df.groupby("instituto", as_index=False).agg({"valor2": "sum"})
    return df_agregado.merge(coords, on="instituto", how="left")

campinas = agregate_df(camp_filtered, coords_df)
limeira = agregate_df(lime_filtered, coords_limeira)
piracicaba = agregate_df(pira_filtered, coords_piracicaba)

# ============================================
# 🔹 Coordenadas fixas para Limeira e Piracicaba
# ============================================
campinas_center   = [-22.821, -47.0647]
limeira_center    = [-22.5551787,-47.4339062]
piracicaba_center = [-22.7018139,-47.6503615]

# ============================================
# 🔹 Função para criar círculos proporcionais ao investimento
# ============================================
def create_map(center, df, zoom=15, unique_point=False, tiles='CartoDB positron'):
    m = folium.Map(location=center, zoom_start=zoom, tiles=tiles)
    
    min_val = df["valor2"].min() if not df.empty else 0
    max_val = df["valor2"].max() if not df.empty else 1

    colormap = branca.colormap.LinearColormap(
        colors=['red','yellow','green'],
        vmin=min_val,
        vmax=max_val,
        caption='Investimento (R$)'
    )

    if unique_point:
        total = df["valor2"].sum()
        radius = max(5, (total/max_val)*30)
        color = colormap(total)
        folium.CircleMarker(
            location=center,
            radius=radius,
            popup=f"<b>Total Investido:</b> R$ {total:,.2f}",
            color="black",
            fill=True,
            fill_color=color,
            fill_opacity=0.8
        ).add_to(m)
    else:
        for _, row in df.iterrows():
            if pd.isna(row["latitude"]): continue
            radius = max(5, (row["valor2"]/max_val)*30)
            color = colormap(row["valor2"])
            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=radius,
                popup=f"<b>{row['instituto']}</b><br>R$ {row['valor2']:,.2f}",
                color="black",
                weight=0.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.8
            ).add_to(m)
    
    return m, colormap, min_val, max_val

def render_static_map(m, width, height):
    html_data = m.get_root().render()
    components.v1.html(html_data, width=width, height=height)
    

# ============================================
# 🔹 Layout dos mapas
# ============================================

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"Campinas – Ano {ano_selecionado}")
    mapa_campinas, colormap, min_val, max_val = create_map(campinas_center, campinas,zoom=15)
    colormap.add_to(mapa_campinas)
    render_static_map(mapa_campinas, 900, 676)

    

with col2:
    st.subheader("Campus Limeira")
    mapa_limeira, _, _, _ = create_map(limeira_center, limeira, zoom=16)
    render_static_map(mapa_limeira, 450, 300)

    
    st.subheader("Campus Piracicaba")
    mapa_piracicaba, _, _, _ = create_map(piracicaba_center, piracicaba, zoom=15)
    render_static_map(mapa_piracicaba, 450, 300)



st.header("📊 Análises Interativas de Investimento")

def aplicar_filtros_sem_ano(df):
    sexo = sexo_select if sexo_select else df["08_Sexo"].unique()
    raca = raca_select if raca_select else df["09_Cor ou Raça"].unique()
    area = area_select if area_select else df["05 _Área"].unique()

    return df[
        (df["08_Sexo"].isin(sexo)) &
        (df["09_Cor ou Raça"].isin(raca)) &
        (df["05 _Área"].isin(area))
    ]

# Aplicar os filtros da página
df_filtered = aplicar_filtros_sem_ano(df_campinas.copy())

anos_disponiveis = sorted(df_filtered["ano"].unique())

# Seletor de ano (com opção "Visão Geral")
ano_escolhido = st.selectbox(
    "Selecione o ano para detalhamento (ou escolha 'Visão Geral')",
    options=["Visão Geral"] + list(anos_disponiveis),
    index=0
)



# ================================================================
# 🔹 CASO 1 — VISÃO GERAL: gráfico stacked por ano
# ================================================================
if ano_escolhido == "Visão Geral":
    st.subheader("📈 Evolução do Investimento ao Longo dos Anos")

    # ----- Gráfico stacked por gênero -----
    df_genero = (
        df_filtered.groupby(["ano", "08_Sexo"], as_index=False)["valor2"].sum()
    )

    fig_genero = px.bar(
        df_genero,
        x="ano",
        y="valor2",
        color="08_Sexo",
        title="Investimento por Ano — Dividido por Gênero",
        labels={"valor2": "Investimento (R$)", "08_Sexo": "Gênero"},
    )
    fig_genero.update_layout(barmode="stack")
    st.plotly_chart(fig_genero, use_container_width=True)

    # ----- Gráfico stacked por raça -----
    df_raca = (
        df_filtered.groupby(["ano", "09_Cor ou Raça"], as_index=False)["valor2"].sum()
    )

    fig_raca = px.bar(
        df_raca,
        x="ano",
        y="valor2",
        color="09_Cor ou Raça",
        title="Investimento por Ano — Dividido por Raça",
        labels={"valor2": "Investimento (R$)", "09_Cor ou Raça": "Raça"},
    )
    fig_raca.update_layout(barmode="stack")
    st.plotly_chart(fig_raca, use_container_width=True)

# ================================================================
# 🔹 CASO 2 — ANO SELECIONADO: gráficos de pizza
# ================================================================
else:
    st.subheader(f"🥧 Distribuição do Investimento no Ano {ano_escolhido}")

    df_ano = df_filtered[df_filtered["ano"] == ano_escolhido]

    colA, colB = st.columns(2)

    # ----- Pizza por gênero -----
    with colA:
        df_genero_ano = df_ano.groupby("08_Sexo", as_index=False)["valor2"].sum()

        fig_pizza_genero = px.pie(
            df_genero_ano,
            values="valor2",
            names="08_Sexo",
            title=f"Distribuição por Gênero ({ano_escolhido})",
        )
        st.plotly_chart(fig_pizza_genero, use_container_width=True)

    # ----- Pizza por raça -----
    with colB:
        df_raca_ano = df_ano.groupby("09_Cor ou Raça", as_index=False)["valor2"].sum()

        fig_pizza_raca = px.pie(
            df_raca_ano,
            values="valor2",
            names="09_Cor ou Raça",
            title=f"Distribuição por Raça ({ano_escolhido})",
        )
        st.plotly_chart(fig_pizza_raca, use_container_width=True)
