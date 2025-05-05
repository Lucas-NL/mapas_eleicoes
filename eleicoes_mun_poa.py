import pandas as pd
import json, requests
from io import StringIO, BytesIO
import plotly.io as pio
import plotly.express as px
# import plotly.graph_objects as go
# from plotly.subplots import make_subplots
import random

import ast


import streamlit as st
st.set_page_config(layout="wide")
# @st.cache_data

### Definições globais: funções e estados de sessão
# st.session_state.mapa_col1_turno2 = False    
if 'mapa_col1_turno1' not in st.session_state:
    st.session_state['mapa_col1_turno1'] = False
if 'mapa_col1_turno2' not in st.session_state:
    st.session_state['mapa_col1_turno2'] = False


if 'mapa_col2_turno1' not in st.session_state:
    st.session_state['mapa_col2_turno1'] = False
if 'mapa_col2_turno2' not in st.session_state:
    st.session_state['mapa_col2_turno2'] = False


def click_map(chave):
    st.session_state[chave] = not st.session_state[chave]

def reset_ver(chave):
    st.session_state[chave] = None
    
#########################################################


st.title('Mapas de eleições')

paginas = [ 'Mapas por partido',
            'Mapas nominais'
          ]
pagina_atual = st.sidebar.selectbox('Escolha a página:',paginas)

if pagina_atual == 'Mapas por partido':
    st.subheader('Mapas por partido')

    col1, col2 = st.columns(2)
    anos_disponiveis = ['2020','2024']

    # with open('bairros_simplificado.geojson','r', encoding='utf-8') as f:
    #     bairros = json.load(f)   # json com delimitações dos bairros
    url = "https://raw.githubusercontent.com/Lucas-NL/geo_jsons/refs/heads/main/bairros_POA_2016.geojson"
    resp = requests.get(url)
    bairros = json.loads(resp.text)      


    locais_voto = pd.read_csv("locais_votacao_poa.csv")  # carrega locais de voto: zona, seção e bairro (arq tratado anteriormente)
    locais_voto["Seções"] = locais_voto["Seções"].apply(ast.literal_eval)  # confere strings? 

    with col1:

        st.info("Selecione o ano para comparação:")
        ano_coluna1 = st.selectbox(
            label="Anos disponíveis:",
            options=anos_disponiveis,
            index=None,
            placeholder="Clique aqui e escolha um ano...",
            key="select_ano1"
        )
        #TODO colocar uma trava se não escolher ano (para não mostrar aviso de erro)
        ### LOAD E TRATAMENTO GERAL DOS DADOS

        url_munzona = "https://github.com/Lucas-NL/mapas_eleicoes/raw/refs/heads/main/dados_votacao_e_locais/votacao_partido_munzona_"+ano_coluna1+"_RS.csv"
        url_secao = "https://raw.githubusercontent.com/Lucas-NL/mapas_eleicoes/refs/heads/main/dados_votacao_e_locais/votacao_secao_"+ano_coluna1+"_RS_reduzido.csv"

        partidos_col1_full = pd.read_csv(url_munzona, encoding="latin-1", delimiter=';')


        # partidos_col1_full = pd.read_csv('../votacao_partido_munzona_' + ano_coluna1 + '_RS.csv', encoding="latin-1", delimiter=';') #arquivo com partidos e coligações
        partidos_col1 = partidos_col1_full[partidos_col1_full.NM_MUNICIPIO == "PORTO ALEGRE"][
                                            ['DS_CARGO', 'NR_PARTIDO', 'SG_PARTIDO', 'NM_PARTIDO', 'NM_COLIGACAO', 'DS_COMPOSICAO_COLIGACAO']
                                                                                            ].drop_duplicates().reset_index(drop=1)
        
        df_col1_completo = pd.read_csv(url_secao) # arquivo com dados da votação
        # st.write(df_col1_completo)

        df_col1_resumo = df_col1_completo[['ANO_ELEICAO','NM_MUNICIPIO','NR_ZONA','NR_SECAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','QT_VOTOS','NR_TURNO']
            ][ (df_col1_completo['NM_MUNICIPIO'] == 'PORTO ALEGRE')  
                # & (df_col1_completo['DS_CARGO'] == 'Prefeito')  
                # & (df_col1_completo.NR_TURNO == 1)
                ]

        locais=locais_voto.explode(["Seções"])

        df_col1 = df_col1_resumo.merge(locais, left_on=['NR_ZONA','NR_SECAO'],right_on=['Zona','Seções'])
        df_col1 = df_col1[['ANO_ELEICAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','NR_ZONA','NR_SECAO','Bairro','QT_VOTOS','NR_TURNO']]
        df_col1['NR_PARTIDO'] = df_col1['NR_VOTAVEL'].astype(str).str[:2]
        df_col1['NR_PARTIDO'] = df_col1['NR_PARTIDO'].astype(int)

        df_col1 = df_col1.merge(partidos_col1, on=['DS_CARGO','NR_PARTIDO'], how='left')
        df_col1['PARTIDO'] = df_col1['SG_PARTIDO'] + ' - ' + df_col1['NR_PARTIDO'].astype(str)
        df_col1.loc[df_col1['NR_VOTAVEL'] == 95, 'PARTIDO'] = 'VOTO BRANCO'
        df_col1.loc[df_col1['NR_VOTAVEL'] == 96, 'PARTIDO'] = 'VOTO NULO'
        # Dicionário de correspondência (nome atual : nome padronizado). Tentar resolver com melhor arquivo geojson
        mapeamento_bairros = { # válido para 2020 e 2024
            'CORONEL APARíCIO BORGES': 'CEL. APARICIO BORGES',
            'HIGIENOPOLIS': 'HIGIENÓPOLIS',
            'MONT SERRAT': 'MONTSERRAT',
            'PARQUE SÃO SEBASTIÃO': 'SÃO SEBASTIÃO',
            "PASSO D'AREIA": 'PASSO DA AREIA',
            'SANTA CECILIA': 'SANTA CECÍLIA',
            'SANTO ANTONIO': 'SANTO ANTÔNIO',
            'SÃO JOSÉ': 'VILA SÃO JOSÉ',
            'VILA ASSUNÇÃO': 'VILA  ASSUNÇÃO', #futuramente preciso tratar melhor isso, com strips e afins
            'VILA FARRAPOS': 'FARRAPOS',
            'VILA FLORESTA': 'JARDIM FLORESTA'
        }
        for nome_antigo, nome_novo in mapeamento_bairros.items():
            mask = df_col1['Bairro'] == nome_antigo
            df_col1.loc[mask, 'Bairro'] = nome_novo

        # Para garantir que tudo está em maiúsculas (opcional)
        # df_col1['Bairro'] = df_col1['Bairro'].str.upper()

        ###---------------------------------------------------------------------------------###
        ###                        Tratamento para cargos específicos                       ###   

        #### ano referente à primeira coluna
        df_col1_ver = df_col1[(df_col1['DS_CARGO'] == 'Vereador')  
                        & (df_col1.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_PARTIDO','PARTIDO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        
        candidaturas_ver_col1 = df_col1_ver[  (df_col1_ver.NR_PARTIDO != 95) #ignorar votos em branco
                                            & (df_col1_ver.NR_PARTIDO != 96) #ignorar votos nulos
                                        ].sort_values(by=['QT_VOTOS']).PARTIDO.drop_duplicates().tolist()

        df_col1_pref1 = df_col1[(df_col1['DS_CARGO'] == 'Prefeito')  
                        & (df_col1.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_PARTIDO','PARTIDO','NR_TURNO','DS_COMPOSICAO_COLIGACAO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref1_col1 = df_col1_pref1.PARTIDO.tolist() # lista de condidaturas para prefeitura 1 turno
        df_col1_pref1_total = df_col1_pref1.groupby(['ANO_ELEICAO','PARTIDO','DS_COMPOSICAO_COLIGACAO']
                                       )[['QT_VOTOS']
                                        ].sum().sort_values(by=['QT_VOTOS'],ascending=0).reset_index()

        df_col1_pref2 = df_col1[(df_col1['DS_CARGO'] == 'Prefeito')  
                        & (df_col1.NR_TURNO == 2)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_PARTIDO','PARTIDO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref2_col1 = df_col1_pref2.PARTIDO.tolist() # lista de condidaturas para prefeitura 2 turno
        ##----------------------##
        ## DF de vereancia PARA VOTOS TOTAIS POR PARTIDO (incluindo legenda)
        df_col1_ver_total = df_col1_ver.groupby(['ANO_ELEICAO','PARTIDO']
                                       )[['QT_VOTOS']
                                        ].sum().sort_values(by=['QT_VOTOS'],ascending=0).reset_index()

        ###---------------------------------------------------------------------------------###
        ###                       Tratamento para visualização no mapa                      ###  

        #### Primeira coluna
        df_col1_pref1= df_col1_pref1.pivot_table(
                    index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
                    columns='PARTIDO',     # Valores que virarão colunas
                    values='QT_VOTOS',       # Valores que preencherão as novas colunas
                    aggfunc='sum',           # Caso haja duplicatas, soma os votos
                    fill_value=0             # Preenche com 0 onde não houver votos
                ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col1_pref2= df_col1_pref2.pivot_table(
                    index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
                    columns='PARTIDO',     # Valores que virarão colunas
                    values='QT_VOTOS',       # Valores que preencherão as novas colunas
                    aggfunc='sum',           # Caso haja duplicatas, soma os votos
                    fill_value=0             # Preenche com 0 onde não houver votos
                ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col1_ver= df_col1_ver.pivot_table(
                    index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
                    columns='PARTIDO',     # Valores que virarão colunas
                    values='QT_VOTOS',       # Valores que preencherão as novas colunas
                    aggfunc='sum',           # Caso haja duplicatas, soma os votos
                    fill_value=0             # Preenche com 0 onde não houver votos
                ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col1_pref1['Maior_votação'] = df_col1_pref1[candidaturas_pref1_col1].idxmax(axis=1)
        df_col1_pref2['Maior_votação'] = df_col1_pref2[candidaturas_pref2_col1].idxmax(axis=1)
        df_col1_ver['Maior_votação'] = df_col1_ver[candidaturas_ver_col1].idxmax(axis=1)
        # st.write(df_col1_ver[['Bairro','Maior_votação']].drop_duplicates())
        # TODO escrever lista de mais votados para bairros que não estao no mapa

        ###---------------------------------------------------------------------------------###
        ###                               Montagem dos mapas                                ###

        coordenada_POA = {'RS': {"lat": -30.0277, "lon": -51.2287}}

        #### 1º TURNO
        ##### PREFEITURA
        st.write('Mapa Prefeitura 1º turno:')
        st.button('Gerar mapa 1º turno',
                on_click=click_map,
                args=['mapa_col1_turno1'],
                key='botao_mapa_col1_t1'
                )    
        if st.session_state['mapa_col1_turno1']:

            fig = px.choropleth_mapbox(data_frame=df_col1_pref1,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col1_pref1,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=900,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.show()
            st.plotly_chart(fig)
        st.write("Votação total por partido:", df_col1_pref1_total)


        #### 2º TURNO
        ##### PREFEITURA

        # Atualiza o estado quando o botão é clicado
        st.write('Mapa Prefeitura 2º turno:')
        st.button('Gerar mapa 2º turno',
                on_click=click_map,
                args=['mapa_col1_turno2'],
                key='botao_mapa_col1_t2'
                )

        if st.session_state['mapa_col1_turno2']:
            fig = px.choropleth_mapbox(data_frame=df_col1_pref2,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col1_pref2,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.update_traces(legendwidth=1)
            # fig.show()
            st.plotly_chart(fig)


        #### 1º TURNO
        ##### Vereância

        # setup para hover no mapa
        st.info("Selecione candidatura(s) para mostrar nos dados:")

        vereador_alvo_col1 = st.selectbox(
            label="Lista de candidaturas:",
            options=candidaturas_ver_col1,
            index=None,
            placeholder="Clique aqui e escolha uma candidatura...",
            key="select_vereador_col1"
        )

        st.session_state.mapa_col1_ver_visivel = False
        botao_ver = True    
        # Atualiza o estado quando o selectbox é alterado
        if st.session_state.select_vereador_col1 is not None:
            st.session_state.mapa_col1_ver_visivel = True
            botao_ver = False
        st.button('Esconder mapa',
                on_click=reset_ver,
                args=['select_vereador_col1'],
                disabled = botao_ver,
                key='botao_mapa_col1_ver'
                )

        dados_mostrados_ver_col1 = {
            'ANO_ELEICAO': True,
            'DS_CARGO': True,
            'Bairro': True,
            'Maior_votação': True,
            'Votos_vencedor': df_col1_ver.apply(lambda row: row[row['Maior_votação']], axis=1),  # Busca os votos do vencedor
            vereador_alvo_col1: True,
            'VOTO BRANCO': ':.0f',
            'VOTO NULO': ':.0f'
        }

        # colours = px.colors.qualitative.Alphabet + px.colors.qualitative.Light24 + px.colors.qualitative.Dark24
        # cores_aleatorias = [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(100)]

        st.write('Mapa vereância:')
        if st.session_state.mapa_col1_ver_visivel:

            fig = px.choropleth_mapbox(data_frame=df_col1_ver,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=dados_mostrados_ver_col1,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Dark24,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[2]}</b><br>"
                    "Ano: %{customdata[0]}<br>"
                    "Cargo: %{customdata[1]}<br>"
                    "Vencedor: %{customdata[3]}: %{customdata[4]:.0f} votos<br>"
                    f"{vereador_alvo_col1}: %{{customdata[5]}} votos<br>"
                    "Votos brancos: %{customdata[6]:.0f}<br>"
                    "Votos nulos: %{customdata[7]:.0f}"
                    "<extra></extra>"
                )
            )
            st.plotly_chart(fig)
        else:
            st.warning("Selecione um vereador para exibir o mapa.")  # Mensagem inicial   


        st.write("Votação total por partido:", df_col1_ver_total)
    # fig.show()


    ############### COLUNA 2

    with col2:

        st.info("Selecione o ano para comparação:")
        ano_coluna2 = st.selectbox(
            label="Anos disponíveis:",
            options=anos_disponiveis,
            index=None,
            placeholder="Clique aqui e escolha um ano...",
            key="select_ano2"
        )
        #TODO colocar uma trava se não escolher ano (para não mostrar aviso de erro)
        ### LOAD E TRATAMENTO GERAL DOS DADOS
        url_munzona2 = "https://github.com/Lucas-NL/mapas_eleicoes/raw/refs/heads/main/dados_votacao_e_locais/votacao_partido_munzona_"+ano_coluna2+"_RS.csv"
        url_secao2 = "https://raw.githubusercontent.com/Lucas-NL/mapas_eleicoes/refs/heads/main/dados_votacao_e_locais/votacao_secao_"+ano_coluna2+"_RS_reduzido.csv"


        partidos_col2_full = pd.read_csv(url_munzona2, encoding="latin-1", delimiter=';') #arquivo com partidos e coligações
        partidos_col2 = partidos_col2_full[partidos_col2_full.NM_MUNICIPIO == "PORTO ALEGRE"][
                                            ['DS_CARGO', 'NR_PARTIDO', 'SG_PARTIDO', 'NM_PARTIDO', 'NM_COLIGACAO', 'DS_COMPOSICAO_COLIGACAO']
                                                                                            ].drop_duplicates().reset_index(drop=1)
        
        df_col2_completo = pd.read_csv(url_secao2) # arquivo com dados da votação

        df_col2_resumo = df_col2_completo[['ANO_ELEICAO','NM_MUNICIPIO','NR_ZONA','NR_SECAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','QT_VOTOS','NR_TURNO']
            ][ (df_col2_completo['NM_MUNICIPIO'] == 'PORTO ALEGRE')  
                # & (df_col2_completo['DS_CARGO'] == 'Prefeito')  
                # & (df_col2_completo.NR_TURNO == 1)
                ]

        locais=locais_voto.explode(["Seções"])

        df_col2 = df_col2_resumo.merge(locais, left_on=['NR_ZONA','NR_SECAO'],right_on=['Zona','Seções'])
        df_col2 = df_col2[['ANO_ELEICAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','NR_ZONA','NR_SECAO','Bairro','QT_VOTOS','NR_TURNO']]
        df_col2['NR_PARTIDO'] = df_col2['NR_VOTAVEL'].astype(str).str[:2]
        df_col2['NR_PARTIDO'] = df_col2['NR_PARTIDO'].astype(int)

        df_col2 = df_col2.merge(partidos_col2, on=['DS_CARGO','NR_PARTIDO'], how='left')
        df_col2['PARTIDO'] = df_col2['SG_PARTIDO'] + ' - ' + df_col2['NR_PARTIDO'].astype(str)
        df_col2.loc[df_col2['NR_VOTAVEL'] == 95, 'PARTIDO'] = 'VOTO BRANCO'
        df_col2.loc[df_col2['NR_VOTAVEL'] == 96, 'PARTIDO'] = 'VOTO NULO'
        # Dicionário de correspondência (nome atual : nome padronizado). Tentar resolver com melhor arquivo geojson
        mapeamento_bairros = { # válido para 2020 e 2024
            'CORONEL APARíCIO BORGES': 'CEL. APARICIO BORGES',
            'HIGIENOPOLIS': 'HIGIENÓPOLIS',
            'MONT SERRAT': 'MONTSERRAT',
            'PARQUE SÃO SEBASTIÃO': 'SÃO SEBASTIÃO',
            "PASSO D'AREIA": 'PASSO DA AREIA',
            'SANTA CECILIA': 'SANTA CECÍLIA',
            'SANTO ANTONIO': 'SANTO ANTÔNIO',
            'SÃO JOSÉ': 'VILA SÃO JOSÉ',
            'VILA ASSUNÇÃO': 'VILA  ASSUNÇÃO', #futuramente preciso tratar melhor isso, com strips e afins
            'VILA FARRAPOS': 'FARRAPOS',
            'VILA FLORESTA': 'JARDIM FLORESTA'
        }
        for nome_antigo, nome_novo in mapeamento_bairros.items():
            mask = df_col2['Bairro'] == nome_antigo
            df_col2.loc[mask, 'Bairro'] = nome_novo

        # Para garantir que tudo está em maiúsculas (opcional)
        # df_col2['Bairro'] = df_col2['Bairro'].str.upper()

        ###---------------------------------------------------------------------------------###
        ###                        Tratamento para cargos específicos                       ###   

        #### ano referente à primeira coluna
        df_col2_ver = df_col2[(df_col2['DS_CARGO'] == 'Vereador')  
                        & (df_col2.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_PARTIDO','PARTIDO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        
        candidaturas_ver_col2 = df_col2_ver[  (df_col2_ver.NR_PARTIDO != 95) #ignorar votos em branco
                                            & (df_col2_ver.NR_PARTIDO != 96) #ignorar votos nulos
                                        ].sort_values(by=['QT_VOTOS']).PARTIDO.drop_duplicates().tolist()

        df_col2_pref1 = df_col2[(df_col2['DS_CARGO'] == 'Prefeito')  
                        & (df_col2.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_PARTIDO','PARTIDO','NR_TURNO','DS_COMPOSICAO_COLIGACAO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref1_col2 = df_col2_pref1.PARTIDO.tolist() # lista de condidaturas para prefeitura 1 turno

        df_col2_pref1_total = df_col2_pref1.groupby(['ANO_ELEICAO','PARTIDO','DS_COMPOSICAO_COLIGACAO']
                                       )[['QT_VOTOS']
                                        ].sum().sort_values(by=['QT_VOTOS'],ascending=0).reset_index()

        df_col2_pref2 = df_col2[(df_col2['DS_CARGO'] == 'Prefeito')  
                        & (df_col2.NR_TURNO == 2)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_PARTIDO','PARTIDO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref2_col2 = df_col2_pref2.PARTIDO.tolist() # lista de condidaturas para prefeitura 2 turno
        ##----------------------##
        ## DF de vereancia PARA VOTOS TOTAIS POR PARTIDO (incluindo legenda)
        df_col2_ver_total = df_col2_ver.groupby(['ANO_ELEICAO','PARTIDO']
                                       )[['QT_VOTOS']
                                        ].sum().sort_values(by=['QT_VOTOS'],ascending=0).reset_index()

        ###---------------------------------------------------------------------------------###
        ###                       Tratamento para visualização no mapa                      ###  

        #### Primeira coluna
        df_col2_pref1= df_col2_pref1.pivot_table(
                    index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
                    columns='PARTIDO',     # Valores que virarão colunas
                    values='QT_VOTOS',       # Valores que preencherão as novas colunas
                    aggfunc='sum',           # Caso haja duplicatas, soma os votos
                    fill_value=0             # Preenche com 0 onde não houver votos
                ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col2_pref2= df_col2_pref2.pivot_table(
                    index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
                    columns='PARTIDO',     # Valores que virarão colunas
                    values='QT_VOTOS',       # Valores que preencherão as novas colunas
                    aggfunc='sum',           # Caso haja duplicatas, soma os votos
                    fill_value=0             # Preenche com 0 onde não houver votos
                ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col2_ver= df_col2_ver.pivot_table(
                    index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
                    columns='PARTIDO',     # Valores que virarão colunas
                    values='QT_VOTOS',       # Valores que preencherão as novas colunas
                    aggfunc='sum',           # Caso haja duplicatas, soma os votos
                    fill_value=0             # Preenche com 0 onde não houver votos
                ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col2_pref1['Maior_votação'] = df_col2_pref1[candidaturas_pref1_col2].idxmax(axis=1)
        df_col2_pref2['Maior_votação'] = df_col2_pref2[candidaturas_pref2_col2].idxmax(axis=1)
        df_col2_ver['Maior_votação'] = df_col2_ver[candidaturas_ver_col2].idxmax(axis=1)
        # st.write(df_col2_ver[['Bairro','Maior_votação']].drop_duplicates())
        # TODO escrever lista de mais votados para bairros que não estao no mapa

        ###---------------------------------------------------------------------------------###
        ###                               Montagem dos mapas                                ###

        coordenada_POA = {'RS': {"lat": -30.0277, "lon": -51.2287}}

        #### 1º TURNO
        ##### PREFEITURA
        st.write('Mapa Prefeitura 1º turno:')
        st.button('Gerar mapa 1º turno',
                on_click=click_map,
                args=['mapa_col2_turno1'],
                key='botao_mapa_col2_t1'
                )    
        if st.session_state['mapa_col2_turno1']:

            fig = px.choropleth_mapbox(data_frame=df_col2_pref1,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col2_pref1,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=900,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.show()
            st.plotly_chart(fig)
        st.write("Votação total por partido:", df_col2_pref1_total)


        #### 2º TURNO
        ##### PREFEITURA

        # Atualiza o estado quando o botão é clicado
        st.write('Mapa Prefeitura 2º turno:')
        st.button('Gerar mapa 2º turno',
                on_click=click_map,
                args=['mapa_col2_turno2'],
                key='botao_mapa_col2_t2'
                )

        if st.session_state['mapa_col2_turno2']:
            fig = px.choropleth_mapbox(data_frame=df_col2_pref2,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col2_pref2,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.update_traces(legendwidth=1)
            # fig.show()
            st.plotly_chart(fig)


        #### 1º TURNO
        ##### Vereância

        # setup para hover no mapa
        st.info("Selecione candidatura(s) para mostrar nos dados:")

        vereador_alvo_col2 = st.selectbox(
            label="Lista de candidaturas:",
            options=candidaturas_ver_col2,
            index=None,
            placeholder="Clique aqui e escolha uma candidatura...",
            key="select_vereador_col2"
        )

        st.session_state.mapa_col2_ver_visivel = False
        botao_ver = True    
        # Atualiza o estado quando o selectbox é alterado
        if st.session_state.select_vereador_col2 is not None:
            st.session_state.mapa_col2_ver_visivel = True
            botao_ver = False
        st.button('Esconder mapa',
                on_click=reset_ver,
                args=['select_vereador_col2'],
                disabled = botao_ver,
                key='botao_mapa_col2_ver'
                )

        dados_mostrados_ver_col2 = {
            'ANO_ELEICAO': True,
            'DS_CARGO': True,
            'Bairro': True,
            'Maior_votação': True,
            'Votos_vencedor': df_col2_ver.apply(lambda row: row[row['Maior_votação']], axis=1),  # Busca os votos do vencedor
            vereador_alvo_col2: True,
            'VOTO BRANCO': ':.0f',
            'VOTO NULO': ':.0f'
        }

        # colours = px.colors.qualitative.Alphabet + px.colors.qualitative.Light24 + px.colors.qualitative.Dark24
        # cores_aleatorias = [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(100)]

        st.write('Mapa vereância:')
        if st.session_state.mapa_col2_ver_visivel:

            fig = px.choropleth_mapbox(data_frame=df_col2_ver,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=dados_mostrados_ver_col2,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Dark24,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[2]}</b><br>"
                    "Ano: %{customdata[0]}<br>"
                    "Cargo: %{customdata[1]}<br>"
                    "Vencedor: %{customdata[3]}: %{customdata[4]:.0f} votos<br>"
                    f"{vereador_alvo_col2}: %{{customdata[5]}} votos<br>"
                    "Votos brancos: %{customdata[6]:.0f}<br>"
                    "Votos nulos: %{customdata[7]:.0f}"
                    "<extra></extra>"
                )
            )
            st.plotly_chart(fig)
        else:
            st.warning("Selecione um vereador para exibir o mapa.")  # Mensagem inicial   


        st.write("Votação total por partido:", df_col2_ver_total)
    # fig.show()


if pagina_atual == 'Mapas nominais':
    st.header('Mapas nominais')

    col1, col2 = st.columns(2)
    anos_disponiveis = ['2020','2024']

    url = "https://raw.githubusercontent.com/Lucas-NL/geo_jsons/refs/heads/main/bairros_POA_2016.geojson"
    resp = requests.get(url)
    bairros = json.loads(resp.text)  

    locais_voto = pd.read_csv("locais_votacao_poa.csv")  # carrega locais de voto: zona, seção e bairro (arq tratado anteriormente)
    locais_voto["Seções"] = locais_voto["Seções"].apply(ast.literal_eval)  # confere strings? 

    with col1:

        st.info("Selecione o ano para comparação:")
        ano_coluna1 = st.selectbox(
            label="Anos disponíveis:",
            options=anos_disponiveis,
            index=None,
            placeholder="Clique aqui e escolha um ano...",
            key="select_ano1"
        )
        #TODO colocar uma trava se não escolher ano (para não mostrar aviso de erro)
        ### LOAD E TRATAMENTO GERAL DOS DADOS
        url_secao1 = "https://raw.githubusercontent.com/Lucas-NL/mapas_eleicoes/refs/heads/main/dados_votacao_e_locais/votacao_secao_"+ano_coluna1+"_RS_reduzido.csv"

        df_col1_completo = pd.read_csv(url_secao1) # arquivo com dados da votação

        df_col1_resumo = df_col1_completo[['ANO_ELEICAO','NM_MUNICIPIO','NR_ZONA','NR_SECAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','QT_VOTOS','NR_TURNO']
            ][ (df_col1_completo['NM_MUNICIPIO'] == 'PORTO ALEGRE')  
                # & (df_col1_completo['DS_CARGO'] == 'Prefeito')  
                # & (df_col1_completo.NR_TURNO == 1)
                ]

        locais=locais_voto.explode(["Seções"])

        df_col1 = df_col1_resumo.merge(locais, left_on=['NR_ZONA','NR_SECAO'],right_on=['Zona','Seções'])
        df_col1 = df_col1[['ANO_ELEICAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','NR_ZONA','NR_SECAO','Bairro','QT_VOTOS','NR_TURNO']]
        df_col1['CANDIDATO'] = df_col1['NR_VOTAVEL'].astype(str) + ' - ' + df_col1['NM_VOTAVEL']

        # Dicionário de correspondência (nome atual : nome padronizado). Tentar resolver com melhor arquivo geojson
        mapeamento_bairros = { # válido para 2020 e 2024
            'CORONEL APARíCIO BORGES': 'CEL. APARICIO BORGES',
            'HIGIENOPOLIS': 'HIGIENÓPOLIS',
            'MONT SERRAT': 'MONTSERRAT',
            'PARQUE SÃO SEBASTIÃO': 'SÃO SEBASTIÃO',
            "PASSO D'AREIA": 'PASSO DA AREIA',
            'SANTA CECILIA': 'SANTA CECÍLIA',
            'SANTO ANTONIO': 'SANTO ANTÔNIO',
            'SÃO JOSÉ': 'VILA SÃO JOSÉ',
            'VILA ASSUNÇÃO': 'VILA  ASSUNÇÃO', #futuramente preciso tratar melhor isso, com strips e afins
            'VILA FARRAPOS': 'FARRAPOS',
            'VILA FLORESTA': 'JARDIM FLORESTA'
        }
        for nome_antigo, nome_novo in mapeamento_bairros.items():
            mask = df_col1['Bairro'] == nome_antigo
            df_col1.loc[mask, 'Bairro'] = nome_novo

        # Para garantir que tudo está em maiúsculas (opcional)
        # df_col1['Bairro'] = df_col1['Bairro'].str.upper()

        ###---------------------------------------------------------------------------------###
        ###                        Tratamento para cargos específicos                       ###   

        #### ano referente à primeira coluna
        df_col1_ver = df_col1[(df_col1['DS_CARGO'] == 'Vereador')  
                        & (df_col1.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_VOTAVEL','CANDIDATO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_ver_col1 = df_col1_ver[  (df_col1_ver.NR_VOTAVEL != 95) #ignorar votos em branco
                                    & (df_col1_ver.NR_VOTAVEL != 96) #ignorar votos nulos
                                    ].sort_values(by=['NR_VOTAVEL']).CANDIDATO.drop_duplicates().tolist() # lista de condidaturas para vereancia, usada para contagem quem ganhou
                ## ou df_col1_ver.CANDIDATO.sort_values().drop_duplicates().tolist() aí divide por partido

        df_col1_pref1 = df_col1[(df_col1['DS_CARGO'] == 'Prefeito')  
                        & (df_col1.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_VOTAVEL','CANDIDATO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref1_col1 = df_col1_pref1.CANDIDATO.tolist() # lista de condidaturas para prefeitura 1 turno


        df_col1_pref2 = df_col1[(df_col1['DS_CARGO'] == 'Prefeito')  
                        & (df_col1.NR_TURNO == 2)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_VOTAVEL','CANDIDATO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref2_col1 = df_col1_pref2.CANDIDATO.tolist() # lista de condidaturas para prefeitura 2 turno
        ##----------------------##


        ###---------------------------------------------------------------------------------###
        ###                       Tratamento para visualização no mapa                      ###  

        #### Primeira coluna
        df_col1_pref2= df_col1_pref2.pivot_table(
            index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
            columns='CANDIDATO',     # Valores que virarão colunas
            values='QT_VOTOS',       # Valores que preencherão as novas colunas
            aggfunc='sum',           # Caso haja duplicatas, soma os votos
            fill_value=0             # Preenche com 0 onde não houver votos
        ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col1_pref1= df_col1_pref1.pivot_table(
            index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'], 
            columns='CANDIDATO',     
            values='QT_VOTOS',       
            aggfunc='sum',           
            fill_value=0             
        ).reset_index().rename_axis(None, axis=1)         

        df_col1_ver= df_col1_ver.pivot_table(
            index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'], 
            columns='CANDIDATO',     
            values='QT_VOTOS',       
            aggfunc='sum',          
            fill_value=0             
        ).reset_index().rename_axis(None, axis=1)              

        # Encontra o nome do candidato com maior votação por linha (bairro)
        df_col1_ver['Maior_votação'] = df_col1_ver[candidaturas_ver_col1].idxmax(axis=1)
        df_col1_pref1['Maior_votação'] = df_col1_pref1[candidaturas_pref1_col1].idxmax(axis=1)
        df_col1_pref2['Maior_votação'] = df_col1_pref2[candidaturas_pref2_col1].idxmax(axis=1)
        # st.write(df_col1_ver[['Bairro','Maior_votação']].drop_duplicates())
        # TODO escrever lista de mais votados para bairros que não estao no mapa

        ###---------------------------------------------------------------------------------###
        ###                               Montagem dos mapas                                ###

        coordenada_POA = {'RS': {"lat": -30.0277, "lon": -51.2287}}

        #### 1º TURNO
        ##### PREFEITURA
        st.write('Mapa Prefeitura 1º turno:')
        st.button('Gerar mapa 1º turno',
                on_click=click_map,
                args=['mapa_col1_turno1'],
                key='botao_mapa_col1_t1'
                )    
        if st.session_state['mapa_col1_turno1']:

            fig = px.choropleth_mapbox(data_frame=df_col1_pref1,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col1_pref1,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=900,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.show()
            st.plotly_chart(fig)


        #### 2º TURNO
        ##### PREFEITURA

        # Atualiza o estado quando o botão é clicado
        st.write('Mapa Prefeitura 2º turno:')
        st.button('Gerar mapa 2º turno',
                on_click=click_map,
                args=['mapa_col1_turno2'],
                key='botao_mapa_col1_t2'
                )

        if st.session_state['mapa_col1_turno2']:
            fig = px.choropleth_mapbox(data_frame=df_col1_pref2,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col1_pref2,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.update_traces(legendwidth=1)
            # fig.show()
            st.plotly_chart(fig)


        #### 1º TURNO
        ##### Vereância

        # setup para hover no mapa
        st.info("Selecione candidatura(s) para mostrar nos dados:")

        vereador_alvo_col1 = st.selectbox(
            label="Lista de candidaturas:",
            options=candidaturas_ver_col1,
            index=None,
            placeholder="Clique aqui e escolha uma candidatura...",
            key="select_vereador_col1"
        )
        # vereador_alvo = "13300 - LAURA SOARES SITO SILVEIRA"
        # if(st.write(vereador_alvo)): TODO se for = None, mostrar todos
            # st.write("OK")

        st.session_state.mapa_col1_ver_visivel = False
        botao_ver = True    
        # Atualiza o estado quando o selectbox é alterado
        if st.session_state.select_vereador_col1 is not None:
            st.session_state.mapa_col1_ver_visivel = True
            botao_ver = False
        st.button('Esconder mapa',
                on_click=reset_ver,
                args=['select_vereador_col1'],
                disabled = botao_ver,
                key='botao_mapa_col1_ver'
                )

        dados_mostrados_ver_col1 = {
            'ANO_ELEICAO': True,
            'DS_CARGO': True,
            'Bairro': True,
            'Maior_votação': True,
            'Votos_vencedor': df_col1_ver.apply(lambda row: row[row['Maior_votação']], axis=1),  # Busca os votos do vencedor
            vereador_alvo_col1: True,
            '95 - VOTO BRANCO': ':.0f',
            '96 - VOTO NULO': ':.0f'
        }

        # colours = px.colors.qualitative.Alphabet + px.colors.qualitative.Light24 + px.colors.qualitative.Dark24
        cores_aleatorias = [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(100)]

        st.write('Mapa vereância:')
        if st.session_state.mapa_col1_ver_visivel:

            fig = px.choropleth_mapbox(data_frame=df_col1_ver,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=dados_mostrados_ver_col1,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=cores_aleatorias,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[2]}</b><br>"
                    "Ano: %{customdata[0]}<br>"
                    "Cargo: %{customdata[1]}<br>"
                    "Vencedor: %{customdata[3]}: %{customdata[4]:.0f} votos<br>"
                    f"{vereador_alvo_col1}: %{{customdata[5]}} votos<br>"
                    "Votos brancos: %{customdata[6]:.0f}<br>"
                    "Votos nulos: %{customdata[7]:.0f}"
                    "<extra></extra>"
                )
            )
            st.plotly_chart(fig)
        else:
            st.warning("Selecione um vereador para exibir o mapa.")  # Mensagem inicial   

    # fig.show()


    ############### COLUNA 2

    with col2:

        st.info("Selecione o ano para comparação:")
        ano_coluna2 = st.selectbox(
            label="Anos disponíveis:",
            options=anos_disponiveis,
            index=None,
            placeholder="Clique aqui e escolha um ano...",
            key="select_ano2"
        )
        ### LOAD E TRATAMENTO GERAL DOS DADOS
        url_secao2 = "https://raw.githubusercontent.com/Lucas-NL/mapas_eleicoes/refs/heads/main/dados_votacao_e_locais/votacao_secao_"+ano_coluna2+"_RS_reduzido.csv"

        df_col2_completo = pd.read_csv(url_secao2) # arquivo com dados da votação

        df_col2_resumo = df_col2_completo[['ANO_ELEICAO','NM_MUNICIPIO','NR_ZONA','NR_SECAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','QT_VOTOS','NR_TURNO']
            ][ (df_col2_completo['NM_MUNICIPIO'] == 'PORTO ALEGRE')  
                # & (df_col1_completo['DS_CARGO'] == 'Prefeito')  
                # & (df_col1_completo.NR_TURNO == 1)
                ]

        locais=locais_voto.explode(["Seções"])

        df_col2 = df_col2_resumo.merge(locais, left_on=['NR_ZONA','NR_SECAO'],right_on=['Zona','Seções'])
        df_col2 = df_col2[['ANO_ELEICAO','DS_CARGO','NR_VOTAVEL','NM_VOTAVEL','NR_ZONA','NR_SECAO','Bairro','QT_VOTOS','NR_TURNO']]
        df_col2['CANDIDATO'] = df_col2['NR_VOTAVEL'].astype(str) + ' - ' + df_col2['NM_VOTAVEL']

        # Dicionário de correspondência (nome atual : nome padronizado). Tentar resolver com melhor arquivo geojson
        mapeamento_bairros = { # válido para 2020 e 2024
            'CORONEL APARíCIO BORGES': 'CEL. APARICIO BORGES',
            'HIGIENOPOLIS': 'HIGIENÓPOLIS',
            'MONT SERRAT': 'MONTSERRAT',
            'PARQUE SÃO SEBASTIÃO': 'SÃO SEBASTIÃO',
            "PASSO D'AREIA": 'PASSO DA AREIA',
            'SANTA CECILIA': 'SANTA CECÍLIA',
            'SANTO ANTONIO': 'SANTO ANTÔNIO',
            'SÃO JOSÉ': 'VILA SÃO JOSÉ',
            'VILA ASSUNÇÃO': 'VILA  ASSUNÇÃO', #futuramente preciso tratar melhor isso, com strips e afins
            'VILA FARRAPOS': 'FARRAPOS',
            'VILA FLORESTA': 'JARDIM FLORESTA'
        }

        for nome_antigo, nome_novo in mapeamento_bairros.items():
            mask = df_col2['Bairro'] == nome_antigo
            df_col2.loc[mask, 'Bairro'] = nome_novo
        # Para garantir que tudo está em maiúsculas (opcional)
        # df_col1['Bairro'] = df_col1['Bairro'].str.upper()

        ###---------------------------------------------------------------------------------###
        ###                        Tratamento para cargos específicos                       ###   

        #### ano referente à segunda coluna
        df_col2_ver = df_col2[(df_col2['DS_CARGO'] == 'Vereador')  
                        & (df_col2.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_VOTAVEL','CANDIDATO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_ver_col2 = df_col2_ver[  (df_col2_ver.NR_VOTAVEL != 95) #ignorar votos em branco
                                    & (df_col2_ver.NR_VOTAVEL != 96) #ignorar votos nulos
                                    ].sort_values(by=['NR_VOTAVEL']).CANDIDATO.drop_duplicates().tolist() # lista de condidaturas para vereancia, usada para contagem quem ganhou
                ## ou df_col1_ver.CANDIDATO.sort_values().drop_duplicates().tolist() aí divide por partido

        df_col2_pref1 = df_col2[(df_col2['DS_CARGO'] == 'Prefeito')  
                        & (df_col2.NR_TURNO == 1)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_VOTAVEL','CANDIDATO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref1_col2 = df_col2_pref1.CANDIDATO.tolist() # lista de condidaturas para prefeitura 1 turno


        df_col2_pref2 = df_col2[(df_col2['DS_CARGO'] == 'Prefeito')  
                        & (df_col2.NR_TURNO == 2)
                        ].groupby(['ANO_ELEICAO','DS_CARGO','Bairro','NR_VOTAVEL','CANDIDATO','NR_TURNO'])[['QT_VOTOS']].sum().reset_index()
        candidaturas_pref2_col2 = df_col2_pref2.CANDIDATO.tolist() # lista de condidaturas para prefeitura 2 turno
        ##----------------------##
        ###---------------------------------------------------------------------------------###
        ###                       Tratamento para visualização no mapa                      ###  

        df_col2_pref2= df_col2_pref2.pivot_table(
            index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'],  # Colunas que serão mantidas como índice
            columns='CANDIDATO',     # Valores que virarão colunas
            values='QT_VOTOS',       # Valores que preencherão as novas colunas
            aggfunc='sum',           # Caso haja duplicatas, soma os votos
            fill_value=0             # Preenche com 0 onde não houver votos
        ).reset_index().rename_axis(None, axis=1)              # Transforma o índice em colunas normais

        df_col2_pref1= df_col2_pref1.pivot_table(
            index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'], 
            columns='CANDIDATO',     
            values='QT_VOTOS',       
            aggfunc='sum',           
            fill_value=0             
        ).reset_index().rename_axis(None, axis=1)         

        df_col2_ver= df_col2_ver.pivot_table(
            index=['ANO_ELEICAO', 'DS_CARGO', 'Bairro', 'NR_TURNO'], 
            columns='CANDIDATO',     
            values='QT_VOTOS',       
            aggfunc='sum',          
            fill_value=0             
        ).reset_index().rename_axis(None, axis=1)              

        # Encontra o nome do candidato com maior votação por linha (bairro)
        df_col2_ver['Maior_votação'] = df_col2_ver[candidaturas_ver_col2].idxmax(axis=1)
        df_col2_pref1['Maior_votação'] = df_col2_pref1[candidaturas_pref1_col2].idxmax(axis=1)
        df_col2_pref2['Maior_votação'] = df_col2_pref2[candidaturas_pref2_col2].idxmax(axis=1)
        # st.write(df_col1_ver[['Bairro','Maior_votação']].drop_duplicates())
        # TODO escrever lista de mais votados para bairros que não estao no mapa

    ###---------------------------------------------------------------------------------###
    ###                               Montagem dos mapas                                ###

        coordenada_POA = {'RS': {"lat": -30.0277, "lon": -51.2287}}

        #### 1º TURNO
        ##### PREFEITURA
        st.write('Mapa Prefeitura 1º turno:')
        st.button('Gerar mapa 1º turno',
                on_click=click_map,
                args=['mapa_col2_turno1'],
                key='botao_mapa_col2_t1'
                )
        if st.session_state['mapa_col2_turno1']:
            fig = px.choropleth_mapbox(data_frame=df_col2_pref1,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col2_pref1,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=900,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.show()
            st.plotly_chart(fig)


        #### 2º TURNO
        ##### PREFEITURA
        st.write('Mapa Prefeitura 2º turno:')
        st.button('Gerar mapa 2º turno',
                on_click=click_map,
                args=['mapa_col2_turno2'],
                key='botao_mapa_col2_t2'
                )
        if st.session_state['mapa_col2_turno2']:
            fig = px.choropleth_mapbox(data_frame=df_col2_pref2,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=df_col2_pref2,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=px.colors.qualitative.Safe,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            # fig.update_traces(legendwidth=1)
            # fig.show()
            st.plotly_chart(fig)


        #### 1º TURNO
        ##### Vereância

        # setup para hover no mapa
        st.info("Selecione candidatura(s) para mostrar nos dados:")

        vereador_alvo_col2 = st.selectbox(
            label="Lista de candidaturas:",
            options=candidaturas_ver_col2,
            index=None,
            placeholder="Clique aqui e escolha uma candidatura...",
            key="select_vereador_col2"
        )
        # if(st.write(vereador_alvo)): TODO se for = None, mostrar todos
            # st.write("OK")

        st.session_state.mapa_col2_ver_visivel = False
        botao_ver = True    
        # Atualiza o estado quando o selectbox é alterado
        if st.session_state.select_vereador_col2 is not None:
            st.session_state.mapa_col2_ver_visivel = True
            botao_ver = False
        st.button('Esconder mapa',
                on_click=reset_ver,
                args=['select_vereador_col2'],
                disabled = botao_ver,
                key='botao_mapa_col2_ver'
                )
        dados_mostrados_ver_col2 = {
            'ANO_ELEICAO': True,
            'DS_CARGO': True,
            'Bairro': True,
            'Maior_votação': True,
            'Votos_vencedor': df_col2_ver.apply(lambda row: row[row['Maior_votação']], axis=1),  # Busca os votos do vencedor
            vereador_alvo_col2: True,
            '95 - VOTO BRANCO': ':.0f',
            '96 - VOTO NULO': ':.0f'
        }

        # colours = px.colors.qualitative.Alphabet + px.colors.qualitative.Light24 + px.colors.qualitative.Dark24
        cores_aleatorias = [f"#{random.randint(0, 0xFFFFFF):06x}" for _ in range(100)]

        st.write('Mapa vereância:')
        if st.session_state.mapa_col2_ver_visivel:

            fig = px.choropleth_mapbox(data_frame=df_col2_ver,
                                        locations="Bairro",
                                        geojson=bairros,
                                        featureidkey='properties.Name',
                                        center={"lat": -30.1046, "lon": -51.1577},
                                        hover_data=dados_mostrados_ver_col2,
                                        zoom=10,
                                        opacity=0.3,
                                        color="Maior_votação",
                                        labels={
                                                "Maior_votação": "Maior votação por bairro"
                                            },
                                        color_discrete_sequence=cores_aleatorias,
                                        #    color_discrete_sequence=["blue", "red"], # Obrigatório no streamlit...
                                        # mapbox_style='open-street-map'
                                        mapbox_style='carto-positron'
                                    )
            fig.update_layout(
                width=800,  # Largura
                height=600,  # Altura
                margin=dict(l=0, r=0, t=0, b=0),  # Margens mínimas
                autosize=False  # Desativa redimensionamento automático
            )
            fig.update_traces(
                hovertemplate=(
                    "<b>%{customdata[2]}</b><br>"
                    "Ano: %{customdata[0]}<br>"
                    "Cargo: %{customdata[1]}<br>"
                    "Vencedor: %{customdata[3]}: %{customdata[4]:.0f} votos<br>"
                    f"{vereador_alvo_col2}: %{{customdata[5]}} votos<br>"
                    "Votos brancos: %{customdata[6]:.0f}<br>"
                    "Votos nulos: %{customdata[7]:.0f}"
                    "<extra></extra>"
                )
            )
            st.plotly_chart(fig)
        else:
            st.warning("Selecione um vereador para exibir o mapa.")  # Mensagem inicial   
