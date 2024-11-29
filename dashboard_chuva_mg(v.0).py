import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
import numpy as np
from datetime import datetime, timedelta
import leafmap.foliumap as leafmap
import folium
import calendar
from io import StringIO
import matplotlib.pyplot as plt
from folium.plugins import MarkerCluster

# Simulação de dados de chuva acumulada (substitua por dados reais)
chuva_ultima_hora = np.random.uniform(0, 5)  # Valor entre 0 e 5mm
chuva_ultimas_24_horas = np.random.uniform(5, 50)  # Valor entre 5 e 50mm
chuva_ultimas_48_horas = np.random.uniform(20, 100)  # Valor entre 20 e 100mm

# URLs e caminhos de arquivos
shp_mg_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
csv_file_path = 'input/estacoes_filtradas.csv'

# Credenciais para login no CEMADEN
login = 'd2020028915@unifei.edu.br'
senha = 'gLs24@ImgBR!'

# Carregar o shapefile de Minas Gerais
mg_gdf = gpd.read_file(shp_mg_url)

# Estações selecionadas no Sul de Minas Gerais
codigo_estacao = [
    '314790701A', '310710901A', '312870901A', '315180001A',
    '316930701A', '314780801A', '315250101A', '313240401A',
    '313360001A', '311410501A', '316230201A', '313300601A'
]

# Carregar os dados das estações meteorológicas
try:
    df1 = pd.read_csv(csv_file_path)
    gdf = gpd.GeoDataFrame(df1, geometry=gpd.points_from_xy(df1['Longitude'], df1['Latitude']))
except FileNotFoundError:
    st.error("Arquivo de estações não encontrado. Verifique o caminho e tente novamente.")
    st.stop()

# Filtrar estações dentro de Minas Gerais
gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Função para baixar dados das estações
def baixar_dados_estacoes(codigo_estacao, data_inicial, data_final, sigla_estado):
    dados_estacoes = {}
    for codigo in codigo_estacao:
        dados_completos = []
        for data_mes in pd.date_range(data_inicial, data_final, freq='1M'):
            ano_mes = data_mes.strftime('%Y%m')
            sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/dados_pcd'
            params = dict(
                rede=11, uf=sigla_estado, inicio=ano_mes, fim=ano_mes, codigo=codigo
            )
            r = requests.get(sws_url, params=params, headers={'token': token})
            if r.status_code == 200:
                dados = r.text
                linhas = dados.split("\n")[1:]  # Remove o cabeçalho
                if linhas:
                    df = pd.read_csv(StringIO("\n".join(linhas)), sep=";")
                    df['datahora'] = pd.to_datetime(df['datahora'])
                    df.set_index('datahora', inplace=True)
                    dados_completos.append(df[df['sensor'] == 'chuva'])
        if dados_completos:
            dados_estacoes[codigo] = pd.concat(dados_completos)
    return dados_estacoes

# Função para exibir gráficos de precipitação
def mostrar_graficos():
    horas = ['Última Hora', '24 Horas', '48 Horas']
    valores = [chuva_ultima_hora, chuva_ultimas_24_horas, chuva_ultimas_48_horas]
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(horas, valores, color=['blue', 'orange', 'green'])
    ax.set_ylabel('Precipitação (mm)')
    ax.set_title('Precipitação nas últimas horas')
    st.pyplot(fig)

# Exibir popup com informações de chuva
def exibir_popup():
    st.markdown("""
    <style>
        .popup {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 250px;
            background-color: rgba(255, 255, 255, 0.8);
            color: black;
            padding: 10px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            font-family: Arial, sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <div class="popup">
        <h4>Informações de Chuva</h4>
        <p>Última hora: {chuva_ultima_hora:.2f} mm</p>
        <p>Últimas 24 horas: {chuva_ultimas_24_horas:.2f} mm</p>
        <p>Últimas 48 horas: {chuva_ultimas_48_horas:.2f} mm</p>
    </div>
    """, unsafe_allow_html=True)

# Configuração da página no Streamlit
st.set_page_config(layout="wide")

# Mostrar o mapa com as estações meteorológicas
st.header("Monitoramento de Chuva - Sul de Minas Gerais")
m = leafmap.Map(center=[-21, -45], zoom_start=8)
for _, row in gdf_mg.iterrows():
    folium.Marker(
        location=[row['Latitude'], row['Longitude']],
        popup=f"{row['municipio']} - Código: {row['codEstacao']}",
        icon=folium.Icon(color="green")
    ).add_to(m)
m.to_streamlit(width=900, height=500)

# Exibição de filtros e gráficos
st.sidebar.header("Filtros")
mostrar_grafico = st.sidebar.checkbox("Mostrar Gráfico de Precipitação")
if mostrar_grafico:
    mostrar_graficos()

# Exibir popup de chuva
exibir_popup()
