import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# ==============================
# CONFIGURAÇÕES
# ==============================

EMPRESA = "regimilson.silva@axe.gevan.com.br"
BASE_URL = "http://servicos.cittati.com.br/WSIntegracaoCittati"

st.set_page_config(page_title="Dashboard Operacional", layout="wide")


# ==============================
# AUTENTICAÇÃO
# ==============================

def autenticar():
    url = f"{BASE_URL}/Autenticacao/AutenticarUsuario/"
    headers = {
        "Content-type": "application/json",
        "Authorization": "Basic V1NJbnRlZ3JhY2FvUExUOndzcGx0"
    }

    response = requests.post(url, headers=headers, json={})

    if response.status_code == 200:
        return response.json().get("token")
    return None


# ==============================
# CONSULTA VIAGENS
# ==============================

def consultar_viagens(token, data):

    data_formatada = data.strftime('%d/%m/%Y')

    url = (
        f"{BASE_URL}/Operacional/ConsultarViagens"
        f"?data={data_formatada}&empresa={EMPRESA}"
    )

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        viagens = response.json().get("viagens", [])
        df = pd.DataFrame(viagens)
        return df

    return None


# ==============================
# INTERFACE
# ==============================

st.title("📊 Dashboard Operacional de Viagens")

st.subheader("Selecionar Data")

modo = st.radio(
    "Escolha o modo:",
    ["Datas rápidas", "Selecionar no calendário"]
)

hoje = datetime.today()

if modo == "Datas rápidas":
    opcoes_datas = {
        "Hoje": hoje,
        "Ontem": hoje - timedelta(days=1),
        "2 dias atrás": hoje - timedelta(days=2),
        "3 dias atrás": hoje - timedelta(days=3),
    }

    escolha = st.selectbox("Selecione:", list(opcoes_datas.keys()))
    data_selecionada = opcoes_datas[escolha]

else:
    data_selecionada = st.date_input(
        "Escolha a data:",
        value=hoje,
        max_value=hoje
    )

# ==============================
# BOTÃO CONSULTAR
# ==============================

if st.button("Consultar"):

    token = autenticar()

    if not token:
        st.error("Erro na autenticação.")
    else:

        df = consultar_viagens(token, data_selecionada)

        if df is None or df.empty:
            st.warning("Nenhuma viagem encontrada.")
        else:

            st.success(f"Dados carregados para {data_selecionada.strftime('%d/%m/%Y')}")

            # ==============================
            # TRATAMENTO DE DATAS
            # ==============================

            colunas_data_hora = [
                "inicioProgramado",
                "inicioRealizado",
                "fimProgramado",
                "fimRealizado"
            ]

            for coluna in colunas_data_hora:
                if coluna in df.columns:
                    df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

            # ==============================
            # VNR
            # ==============================

            df_vnr = df[df["veiculo"].str.contains("vnr", case=False, na=False)]
            total_vnr = len(df_vnr)

            # ==============================
            # EM ABERTO
            # ==============================

            df_sem_vnr = df[~df["veiculo"].str.contains("vnr", case=False, na=False)]

            df_aberto = df_sem_vnr[
                (df_sem_vnr["inicioRealizado"].isna()) |
                (df_sem_vnr["fimRealizado"].isna())
            ]

            total_aberto = len(df_aberto)

            # ==============================
            # OCIOSOS
            # ==============================

            saida_garagem = df[df["atividade"] == "Saída de Garagem"]
            recolhe = df[df["atividade"] == "Recolhe"]

            veiculos_somente_saida = saida_garagem[
                ~saida_garagem["veiculo"].isin(recolhe["veiculo"])
            ]

            veiculos_somente_recolhe = recolhe[
                ~recolhe["veiculo"].isin(saida_garagem["veiculo"])
            ]

            veiculos_ociosos = pd.concat(
                [veiculos_somente_saida, veiculos_somente_recolhe]
            )["veiculo"].drop_duplicates()

            total_ociosos = veiculos_ociosos.nunique()

            # ==============================
            # INCONSISTENTES
            # ==============================

            df_sem_vnr2 = df[~df["veiculo"].str.contains("vnr", case=False, na=False)]

            df_inconsistente = df_sem_vnr2[
                df_sem_vnr2.duplicated(
                    subset=["veiculo", "inicioRealizado"],
                    keep=False
                )
            ]

            total_inconsistente = len(df_inconsistente)

            # ==============================
            # ATRASOS
            # ==============================

            df["Atraso"] = (
                (df["inicioRealizado"] - df["inicioProgramado"])
                .dt.total_seconds() > 6 * 60
            )

            df_atraso = df[
                (df["atividade"] == "Viagem Normal") &
                (df["sentido"] == "I") &
                (df["Atraso"] == True)
            ]

            total_atraso = len(df_atraso)

            # ==============================
            # KPIs
            # ==============================

            col1, col2, col3, col4, col5, col6 = st.columns(6)

            col1.metric("Total Viagens", len(df))
            col2.metric("Atrasos", total_atraso)
            col3.metric("Queimadas (VNR)", total_vnr)
            col4.metric("Em Aberto", total_aberto)
            col5.metric("Ociosos", total_ociosos)
            col6.metric("Inconsistentes", total_inconsistente)

            st.divider()

            # ==============================
            # TABELAS
            # ==============================

            st.subheader("🔥 Viagens Queimadas (VNR)")
            st.dataframe(df_vnr)

            st.subheader("⏳ Viagens em Aberto")
            st.dataframe(df_aberto.sort_values("inicioProgramado"))

            st.subheader("💤 Veículos Ociosos")
            st.dataframe(veiculos_ociosos.to_frame(name="Veículo"))

            st.subheader("⚠️ Viagens Inconsistentes")
            st.dataframe(df_inconsistente)

            st.subheader("⏱ Viagens com Atraso")
            st.dataframe(df_atraso.sort_values("inicioProgramado"))

            st.subheader("📋 Tabela Completa")
            st.dataframe(df)