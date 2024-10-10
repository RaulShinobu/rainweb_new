import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
from datetime import datetime, timedelta
import leafmap.foliumap as leafmap
import folium
import glob
from folium.plugins import MarkerCluster

# URLs e caminhos de arquivos
#shp_mg_url = 'https://github.com/giuliano-macedo/geodata-br-states/raw/main/geojson/br_states/br_mg.json'
shp_sul_minas = 'https://github.com/RaulShinobu/rainweb_new/edit/main/MG_Mesorregioes_2022/MG_Mesorregioes_2022.shp'
csv_file_path = 'input;/lista_das_estacoes_CEMADEN_13maio2024.csv'

# Login e senha do CEMADEN (previamente fornecidos)
login = 'augustoflaviobob@gmail.com'
senha = 'Flaviobr123!'

# Carregar os dados do shapefile de Minas Gerais
sul_minas = gpd.read_file(shp_sul_minas)
#mg_gdf = gpd.read_file(shp_mg_url)

# Carregar os dados das estações
df = pd.read_csv(csv_file_path)
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']))

# Realizar o filtro espacial: apenas estações dentro de Minas Gerais
# Filtrar apenas as estações dentro do Sul de Minas
gdf_sul_mg = gpd.sjoin(gdf, sul_minas, predicate='within')
#gdf_mg = gpd.sjoin(gdf, mg_gdf, predicate='within')

# Recuperação do token
token_url = 'http://sgaa.cemaden.gov.br/SGAA/rest/controle-token/tokens'
login_payload = {'email': login, 'password': senha}
response = requests.post(token_url, json=login_payload)
content = response.json()
token = content['token']

# Função para baixar os dados do último mês e retornar a soma
def baixar_dados_estacao(codigo_estacao, sigla_estado, data_inicial, data_final, login, senha):
    dfs = []
    for ano_mes_dia in pd.date_range(data_inicial, data_final, freq='1M'):
        ano_mes = ano_mes_dia.strftime('%Y%m')
        sws_url = 'http://sws.cemaden.gov.br/PED/rest/pcds/df_pcd'
        params = dict(rede=11, uf=sigla_estado, inicio=ano_mes, fim=ano_mes, codigo=codigo_estacao)
        r = requests.get(sws_url, params=params, headers={'token': token})
        df_mes = pd.read_csv(pd.compat.StringIO(r.text))
        dfs.append(df_mes)
            
    files = sorted(glob.glob(f'/content/estacao_CEMADEN_{sigla_estado}_{codigo_estacao}*.csv'))

    # leitura dos arquivos
    dfs = pd.DataFrame()
    for file in files:
    
        # leitura da tabela
        df0 = pd.read_csv(file, delimiter=';', skiprows=1)
    
        # junta a tabela que foi lida com a anterior
        dfs = pd.concat([dfs, df0], ignore_index=True)

    #soma_selecionada = dfs['valor'].sum()

# Função principal do dashboard
def main():
    hoje = datetime.now()
    data_inicial = hoje.replace(day=1)
    data_final = hoje

    st.set_page_config(layout="wide")

    st.markdown(
        """
        <style>
            .main .block-container {
                padding: 0;
                margin: 0;
            }
            iframe {
                height: 100vh !important;
                width: 100vw !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    m = leafmap.Map(center=[-21.00, -45.00], zoom=7, draw_control=False, measure_control=False, fullscreen_control=False, attribution_control=True)

    # Adicionar marcadores das estações meteorológicas
    for i, row in gdf_sul_mg.iterrows():
        # Baixar dados da estação
        codigo_estacao = row['Código']
        dados_estacao= baixar_dados_estacao(codigo_estacao, 'MG', data_inicial, data_final, login, senha)

        # Definir cor com base no valor
        #if soma_selecionada <= 10:
            #cor = 'green'
        #elif 10 <soma_selecionada <= 30:
           # cor = 'yellow'
       # else:
         #   cor = 'red'

        # Adicionar marcador com valor
        folium.RegularPolygonMarker(
            location=[row['Latitude'], row['Longitude']],
            color='black',
            opacity=1,
            weight=2,
            fillColor='green',
            fillOpacity=1,
            numberOfSides=2,
            rotation=45,
            radius=10,
            popup=f"{row['Nome']} (Código: {row['Código']})<br>Soma do último mês:"
        ).add_to(m)

    m.add_gdf(
        gdf_sul_mg, 
        layer_name="Minas Gerais", 
        style={"color": "black", "weight": 1, "fillOpacity": 0, "interactive": False},
        info_mode=None
    )

    st.sidebar.header("Filtros de Seleção")
    modo_selecao = st.sidebar.radio("Selecionar Estação por:", ('Código'))

    if modo_selecao == 'Código':
        estacao_selecionada = st.sidebar.selectbox("Selecione a Estação", gdf_sul_mg['Nome'].unique())
        codigo_estacao = gdf_sul_mg[gdf_sul_mg['Nome'] == estacao_selecionada]['Código'].values[0]

    latitude_estacao = gdf_sul_mg[gdf_sul_mg['Nome'] == estacao_selecionada]['Latitude'].values[0]
    longitude_estacao = gdf_sul_mg[gdf_sul_mg['Nome'] == estacao_selecionada]['Longitude'].values[0]

    sigla_estado = 'MG'
    tipo_busca = st.sidebar.radio("Tipo de Busca:", ('Diária', 'Mensal'))

    if tipo_busca == 'Diária':
        data_inicial = st.sidebar.date_input("Data Inicial", value=data_inicial)
        data_final = st.sidebar.date_input("Data Final", value=data_final)
    else:
        ano_selecionado = st.sidebar.selectbox("Selecione o Ano", range(2020, datetime.now().year + 1))
        mes_selecionado = st.sidebar.selectbox("Selecione o Mês", range(1, 13))
        data_inicial = datetime(ano_selecionado, mes_selecionado, 1)
        data_final = datetime(ano_selecionado, mes_selecionado + 1, 1) - timedelta(days=1) if mes_selecionado != 12 else datetime(ano_selecionado, 12, 31)

    if st.sidebar.button("Baixar Dados"):
        data_inicial_str = data_inicial.strftime('%Y%m%d')
        data_final_str = data_final.strftime('%Y%m%d')
        dados_estacao= baixar_dados_estacao(codigo_estacao, sigla_estado, data_inicial, data_final, login, senha)

        if not dados_estacao.empty:
            st.subheader(f"Dados da Estação: {estacao_selecionada} (Código: {codigo_estacao})")
            st.write(dados_estacao)
        else:
            st.warning("Nenhum dado encontrado para o período selecionado.")

    m.to_streamlit()

if __name__ == "__main__":
    main()
