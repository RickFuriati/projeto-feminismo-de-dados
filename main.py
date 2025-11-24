import pandas as pd
import numpy as np

import streamlit as st
import folium
from streamlit_folium import st_folium
import branca

import plotly.express as px

st.set_page_config(layout="wide")

@st.cache_data
def load_data(path):
    area_df = pd.read_excel(path + 'valor_cnpq_por_area.xlsx')
    genero_df= pd.read_excel(path + 'valor_cnpq_por_raca_genero.xlsx')
    consolidado_df= pd.read_excel(path + 'valor_cnpq_consolidado_v2.xlsx')
    
    coords_df = pd.read_csv(path + 'coords_institutos.csv')
    
    return area_df, genero_df, consolidado_df, coords_df

data_path = './Dados/'
area_df, genero_df, consolidado_df, coords_df = load_data(data_path)

institutos=consolidado_df['instituto'].unique()
institutos=np.delete(institutos, [2,7])

campi=consolidado_df['15_Cidade'].unique()
campi=np.delete(campi, 0)

areas=consolidado_df["05 _Área"].unique()

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

st.title("Mapa de Investimento CNPq - Unicamp")

col_f1, col_f2, col_f3, col_f4,col_f5 = st.columns([1,1,1,1,1])

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

@st.cache_data
def aplicar_filtros(df, sexo_select, raca_select, area_select, agrupar_todos, ano=None):
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

camp_filtered = aplicar_filtros(df_campinas, sexo_select, raca_select, area_select, agrupar_todos, ano=ano_selecionado)
lime_filtered = aplicar_filtros(df_limeira, sexo_select, raca_select, area_select, agrupar_todos, ano=ano_selecionado)
pira_filtered = aplicar_filtros(df_piracicaba, sexo_select, raca_select, area_select, agrupar_todos, ano=ano_selecionado)

@st.cache_data
def agregate_df(df, coords):
    df_agregado = df.groupby("instituto", as_index=False).agg({"valor2": "sum"})
    return df_agregado.merge(coords, on="instituto", how="left")

campinas = agregate_df(camp_filtered, coords_df)
limeira = agregate_df(lime_filtered, coords_limeira)
piracicaba = agregate_df(pira_filtered, coords_piracicaba)

campinas_center   = [-22.821, -47.0647]
limeira_center    = [-22.5544232,-47.429059]
piracicaba_center = [-22.7018139,-47.6503615]

@st.cache_data
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
        radius = max(5, (total/max_val)*30) if max_val > 0 else 5 
        color = colormap(total) if max_val > 0 else colormap(0)
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
            radius = max(5, (row["valor2"]/max_val)*30) if max_val > 0 else 5
            color = colormap(row["valor2"]) if max_val > 0 else colormap(0)
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

col1, col2 = st.columns([2, 1])

with col1:
    if agrupar_todos:
        st.subheader("Campinas – Todos os anos")
    else:
        st.subheader(f"Campinas – Ano {ano_selecionado}")
    mapa_campinas, colormap, min_val, max_val = create_map(campinas_center, campinas,zoom=15)
    colormap.add_to(mapa_campinas)
    
    st_folium(mapa_campinas, height=676, use_container_width=True)

with col2:
    st.subheader("Campus Limeira")
    mapa_limeira, _, _, _ = create_map(limeira_center, limeira, zoom=15, unique_point=True)
    
    st_folium(mapa_limeira, height=300, use_container_width=True)

    
    st.subheader("Campus Piracicaba")
    mapa_piracicaba, _, _, _ = create_map(piracicaba_center, piracicaba, zoom=15, unique_point=True)
    
    st_folium(mapa_piracicaba, height=300, use_container_width=True)


@st.cache_data
def aplicar_filtros_sem_ano(df, sexo_select, raca_select, area_select):
    sexo = sexo_select if sexo_select else df["08_Sexo"].unique()
    raca = raca_select if raca_select else df["09_Cor ou Raça"].unique()
    area = area_select if area_select else df["05 _Área"].unique()

    return df[
        (df["08_Sexo"].isin(sexo)) &
        (df["09_Cor ou Raça"].isin(raca)) &
        (df["05 _Área"].isin(area))
    ]

st.subheader("Investimento ao longo do tempo")

stack_mode = st.toggle("Gráfico Empilhado", value=True)

df_filtros_somente = aplicar_filtros_sem_ano(df_completo, sexo_select, raca_select, area_select)

@st.cache_data
def group_by_sexo(df):
    return df.groupby(["ano", "08_Sexo"], as_index=False)["valor2"].sum()

df_sexo = group_by_sexo(df_filtros_somente)

@st.cache_data
def group_by_raca(df):
    return df.groupby(["ano", "09_Cor ou Raça"], as_index=False)["valor2"].sum()

df_raca = group_by_raca(df_filtros_somente)

LEGEND_LAYOUT = dict(
    orientation="h",
    yanchor="bottom",
    y=1.02,
    xanchor="left",
    x=0
)

@st.cache_data
def create_chart_sexo(df_sexo, stack_mode):
    if not stack_mode:
        fig = px.line(df_sexo, x="ano", y="valor2", color="08_Sexo", markers=True, title="Investimento anual por Sexo")
        fig.update_layout(legend=LEGEND_LAYOUT)
    else:
        fig = px.bar(df_sexo, x="ano", y="valor2", color="08_Sexo", title="Investimento anual por Sexo")
        fig.update_layout(barmode="stack", legend=LEGEND_LAYOUT)
    return fig

@st.cache_data
def create_chart_raca(df_raca, stack_mode):
    if not stack_mode:
        fig = px.line(df_raca, x="ano", y="valor2", color="09_Cor ou Raça", markers=True, title="Investimento anual por Raça")
        fig.update_layout(legend=LEGEND_LAYOUT)
    else:
        fig = px.bar(df_raca, x="ano", y="valor2", color="09_Cor ou Raça", title="Investimento anual por Raça")
        fig.update_layout(barmode="stack", legend=LEGEND_LAYOUT)
    return fig

fig_sexo = create_chart_sexo(df_sexo, stack_mode)
fig_raca = create_chart_raca(df_raca, stack_mode)

st.plotly_chart(fig_sexo, use_container_width=True)
st.plotly_chart(fig_raca, use_container_width=True)

st.subheader("Distribuição Percentual do Investimento")

colP1, colP2 = st.columns(2)

if agrupar_todos:
    df_pie_base = df_filtros_somente
    titulo_extra = " (Todos os anos)"
else:
    df_pie_base = aplicar_filtros(df_completo, sexo_select, raca_select, area_select, agrupar_todos, ano=ano_selecionado)
    titulo_extra = f" (Ano {ano_selecionado})"

@st.cache_data
def group_pie_sexo(df):
    return df.groupby("08_Sexo", as_index=False)["valor2"].sum()

df_pie_sexo = group_pie_sexo(df_pie_base)

with colP1:
    fig_pie1 = px.pie(
        df_pie_sexo,
        names="08_Sexo",
        values="valor2",
        title="Distribuição por Sexo" + titulo_extra
    )
    st.plotly_chart(fig_pie1, use_container_width=True)

@st.cache_data
def group_pie_raca(df):
    return df.groupby("09_Cor ou Raça", as_index=False)["valor2"].sum()

df_pie_raca = group_pie_raca(df_pie_base)

with colP2:
    fig_pie2 = px.pie(
        df_pie_raca,
        names="09_Cor ou Raça",
        values="valor2",
        title="Distribuição por Raça" + titulo_extra
    )
    st.plotly_chart(fig_pie2, use_container_width=True)

st.markdown(
    """
    <style>
    #custom-footer {
        margin-top: 60px;
        padding: 20px 0;
        text-align: center;
        background-color: rgba(255, 255, 255, 0);
        color: #555;
        font-size: 15px;
    }

    #custom-footer ul {
        list-style: none;
        padding: 0;
        margin: 8px 0 0 0;
    }

    #custom-footer li {
        margin: 3px 0;
    }
    </style>

    <div id="custom-footer">
        Projeto final desenvolvido na disciplina de Pós-Graduação 
        <b>Feminismo de Dados</b> do IC-Unicamp, ministrada pela 
        Professora <b>Sandra Ávila</b> em 2025.
        <br>
        <span style="color:#777;">Desenvolvido por:</span>
        <ul>
            <li>Amanda Imperial Girelli</li>
            <li>Ricardo Henrique Guedes Furiati</li>
            <li>Vitória Maria Carneiro Mathias</li>
        </ul>
    </div>
    """,
    unsafe_allow_html=True
)