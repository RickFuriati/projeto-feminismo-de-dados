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

    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

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

areas=consolidado_df["05 _Área"].unique()

#coords_df=find_coordinates(institutos)
#coords_df.to_csv(data_path + 'coords_institutos.csv', index=False)
coords_df = pd.read_csv(data_path + 'coords_institutos.csv')
coords_piracicaba = coords_df.copy()
coords_piracicaba['latitude'] = -22.7018139
coords_piracicaba['longitude'] = -47.6503615

coords_limeira= coords_df.copy()
coords_limeira['latitude'] = -22.5544232
coords_limeira['longitude'] = -47.429059


df_campinas = consolidado_df[consolidado_df['15_Cidade'] == 'Campinas'][['instituto', 'ano', 'valor2', '05 _Área', '08_Sexo', '09_Cor ou Raça']]
df_limeira  = consolidado_df[consolidado_df['15_Cidade'] == 'Limeira'][['instituto', 'ano', 'valor2', '05 _Área', '08_Sexo', '09_Cor ou Raça']]
df_piracicaba     = consolidado_df[consolidado_df['15_Cidade'] == 'Piracicaba'][['instituto', 'ano', 'valor2', '05 _Área', '08_Sexo', '09_Cor ou Raça']]

df_completo=consolidado_df[['instituto', 'ano', 'valor2', '05 _Área', '08_Sexo', '09_Cor ou Raça']]

st.set_page_config(layout="wide", page_title="Mapa de Investimento CNPq - Unicamp")

# CSS – Layout responsivo (Opção A)
st.markdown("""
<style>
/* Remove padding lateral para dar mais espaço */
.block-container {
    padding-left: 1rem;
    padding-right: 1rem;
}

/* Organização em colunas só no desktop */
@media (min-width: 800px) {
    .desktop-cols {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 20px;
    }
}

/* Mobile: tudo em uma coluna */
@media (max-width: 799px) {
    .desktop-cols {
        display: block;
    }
}

/* Footer bonitão e centralizado */
#custom-footer {
    margin-top: 80px;
    padding: 25px 0;
    text-align: center;
    color: #555;
    font-size: 15px;
}
#custom-footer ul {
    list-style: none;
    padding: 0;
    margin: 8px 0 0 0;
}
#custom-footer li {
    margin: 4px 0;
}

/* Tornar iframe dos mapas responsivo */
.responsive-map iframe {
    width: 100% !important;
    height: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------
# TÍTULO
# -------------------------------------
st.title("Mapa de Investimento CNPq - Unicamp")

# -------------------------------------
# FILTROS
# -------------------------------------
col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)

sexo_select = col_f1.multiselect(
    "Sexo",
    options=df_completo["08_Sexo"].dropna().unique(),
    default=[],
    placeholder="Selecione"
)

raca_select = col_f2.multiselect(
    "Raça",
    options=df_completo["09_Cor ou Raça"].dropna().unique(),
    default=[],
    placeholder="Selecione"
)

area_select = col_f3.multiselect(
    "Área do Conhecimento",
    options=df_completo["05 _Área"].dropna().unique(),
    default=[],
    placeholder="Selecione"
)

ano_selecionado = col_f4.slider(
    "Ano",
    2005,
    int(df_completo["ano"].max()),
    value=2022
)

agrupar_todos = col_f5.toggle(
    "Agregar anos",
    value=False
)

# -------------------------------------
# FUNÇÕES DE FILTRO
# -------------------------------------
def aplicar_filtros(df, ano=None):
    sexo = sexo_select if sexo_select else df["08_Sexo"].unique()
    raca = raca_select if raca_select else df["09_Cor ou Raça"].unique()
    area = area_select if area_select else df["05 _Área"].unique()

    df_f = df[
        (df["08_Sexo"].isin(sexo)) &
        (df["09_Cor ou Raça"].isin(raca)) &
        (df["05 _Área"].isin(area))
    ]

    if agrupar_todos:
        return df_f
    else:
        return df_f[df_f["ano"] == ano]


def aplicar_filtros_sem_ano(df):
    sexo = sexo_select if sexo_select else df["08_Sexo"].unique()
    raca = raca_select if raca_select else df["09_Cor ou Raça"].unique()
    area = area_select if area_select else df["05 _Área"].unique()

    return df[
        (df["08_Sexo"].isin(sexo)) &
        (df["09_Cor ou Raça"].isin(raca)) &
        (df["05 _Área"].isin(area))
    ]

# -------------------------------------
# PREPARAÇÃO DOS DADOS
# -------------------------------------
camp_filtered = aplicar_filtros(df_campinas, ano=ano_selecionado)
lime_filtered = aplicar_filtros(df_limeira, ano=ano_selecionado)
pira_filtered = aplicar_filtros(df_piracicaba, ano=ano_selecionado)

def agregate_df(df, coords):
    df_agregado = df.groupby("instituto", as_index=False).agg({"valor2": "sum"})
    return df_agregado.merge(coords, on="instituto", how="left")

campinas = agregate_df(camp_filtered, coords_df)
limeira = agregate_df(lime_filtered, coords_limeira)
piracicaba = agregate_df(pira_filtered, coords_piracicaba)

campinas_center   = [-22.821, -47.0647]
limeira_center    = [-22.5544232,-47.429059]
piracicaba_center = [-22.7018139,-47.6503615]

# -------------------------------------
# MAPA — função responsiva
# -------------------------------------
def create_map(center, df, zoom=15, tiles='CartoDB positron'):
    m = folium.Map(location=center, zoom_start=zoom, tiles=tiles)

    if df.empty:
        return m

    min_val = df["valor2"].min()
    max_val = df["valor2"].max()

    colormap = branca.colormap.LinearColormap(
        colors=['red','yellow','green'],
        vmin=min_val,
        vmax=max_val,
        caption='Investimento (R$)'
    ).add_to(m)

    for _, row in df.iterrows():
        if pd.isna(row["latitude"]): 
            continue

        radius = max(5, (row["valor2"]/max_val)*30)
        color = colormap(row["valor2"])

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=radius,
            popup=f"<b>{row['instituto']}</b><br>R$ {row['valor2']:,.2f}",
            color="black",
            weight=0.4,
            fill=True,
            fill_color=color,
            fill_opacity=0.85
        ).add_to(m)

    return m

def render_responsive_map(m):
    html_data = m.get_root().render()
    st.markdown('<div class="responsive-map">', unsafe_allow_html=True)
    components.v1.html(html_data, height=500)
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------
# MAPAS (LOCAIS + RESPONSIVOS)
# -------------------------------------
st.subheader("Campinas – " + ("Todos os anos" if agrupar_todos else f"Ano {ano_selecionado}"))

m_camp = create_map(campinas_center, campinas)
render_responsive_map(m_camp)

st.subheader("Campus Limeira")
m_lime = create_map(limeira_center, limeira)
render_responsive_map(m_lime)

st.subheader("Campus Piracicaba")
m_pira = create_map(piracicaba_center, piracicaba)
render_responsive_map(m_pira)

# -------------------------------------
# GRÁFICOS TEMPORAIS
# -------------------------------------
st.subheader("Investimento ao longo do tempo")

stack_mode = st.toggle("Gráfico Empilhado", value=True)

df_filtros_somente = aplicar_filtros_sem_ano(df_completo)

df_sexo = df_filtros_somente.groupby(["ano", "08_Sexo"], as_index=False)["valor2"].sum()
df_raca = df_filtros_somente.groupby(["ano", "09_Cor ou Raça"], as_index=False)["valor2"].sum()

if not stack_mode:
    fig_sexo = px.line(df_sexo, x="ano", y="valor2", color="08_Sexo", markers=True)
    fig_raca = px.line(df_raca, x="ano", y="valor2", color="09_Cor ou Raça", markers=True)
else:
    fig_sexo = px.bar(df_sexo, x="ano", y="valor2", color="08_Sexo")
    fig_sexo.update_layout(barmode="stack")

    fig_raca = px.bar(df_raca, x="ano", y="valor2", color="09_Cor ou Raça")
    fig_raca.update_layout(barmode="stack")

st.plotly_chart(fig_sexo, use_container_width=True)
st.plotly_chart(fig_raca, use_container_width=True)

# -------------------------------------
# PIZZAS
# -------------------------------------
st.subheader("Distribuição Percentual do Investimento")

if agrupar_todos:
    df_pie = df_filtros_somente
    titulo_extra = " (Todos os anos)"
else:
    df_pie = aplicar_filtros(df_completo, ano=ano_selecionado)
    titulo_extra = f" (Ano {ano_selecionado})"

col_p1, col_p2 = st.columns(2)

with col_p1:
    df_pie_sexo = df_pie.groupby("08_Sexo", as_index=False)["valor2"].sum()
    fig_pie1 = px.pie(df_pie_sexo, names="08_Sexo", values="valor2",
                      title="Distribuição por Sexo" + titulo_extra)
    st.plotly_chart(fig_pie1, use_container_width=True)

with col_p2:
    df_pie_raca = df_pie.groupby("09_Cor ou Raça", as_index=False)["valor2"].sum()
    fig_pie2 = px.pie(df_pie_raca, names="09_Cor ou Raça", values="valor2",
                      title="Distribuição por Raça" + titulo_extra)
    st.plotly_chart(fig_pie2, use_container_width=True)

# -------------------------------------
# FOOTER
# -------------------------------------
st.markdown("""
<div id="custom-footer">
    Projeto final desenvolvido na disciplina de Pós-Graduação 
    <b>Feminismo de Dados</b> do IC-Unicamp, ministrada pela 
    Professora <b>Sandra Ávila</b> em 2025.<br>
    <span style="color:#777;">Desenvolvido por:</span>
    <ul>
        <li>Amanda Imperial Girelli</li>
        <li>Ricardo Henrique Guedes Furiati</li>
        <li>Vitória Maria Carneiro Mathias</li>
    </ul>
</div>
""", unsafe_allow_html=True)