import requests
import pandas as pd
from typing import Optional

EMPRESA = "regimilson.silva@axe.gevan.com.br"
BASE_URL = "http://servicos.cittati.com.br/WSIntegracaoCittati"


# ==============================
# AUTENTICAÇÃO
# ==============================
def autenticar() -> Optional[str]:
    url = f"{BASE_URL}/Autenticacao/AutenticarUsuario/"
    headers = {
        "Content-type": "application/json",
        "Authorization": "Basic V1NJbnRlZ3JhY2FvUExUOndzcGx0"
    }

    try:
        response = requests.post(url, headers=headers, json={})
        response.raise_for_status()
        return response.json().get("token")

    except requests.RequestException as e:
        print(f"Erro na autenticação: {e}")
        return None


# ==============================
# CONSULTA VIAGENS
# ==============================
def consultar_viagens(token: str, data: str) -> Optional[pd.DataFrame]:

    data_formatada = pd.to_datetime(data, format='%d/%m/%Y').strftime('%d/%m/%Y')

    url = (
        f"{BASE_URL}/Operacional/ConsultarViagens"
        f"?data={data_formatada}&empresa={EMPRESA}"
    )

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        viagens = response.json().get("viagens", [])

        if not viagens:
            print("Nenhuma viagem encontrada.")
            return None

        df = pd.DataFrame(viagens)
        return df

    except requests.RequestException as e:
        print(f"Erro ao consultar viagens: {e}")
        return None


# ==============================
# PREPARAÇÃO DOS DADOS
# ==============================
def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:

    colunas_data = [
        "inicioProgramado",
        "inicioRealizado",
        "fimProgramado",
        "fimRealizado"
    ]

    for coluna in colunas_data:
        if coluna in df.columns:
            df[coluna] = pd.to_datetime(df[coluna], errors="coerce")

    return df


# ==============================
# ANÁLISE 1 - VEÍCULOS VNR
# ==============================
def analise_vnr(df: pd.DataFrame):

    filtrado = df[df["veiculo"].str.contains("VNR", case=False, na=False)]

    print("\n=== VEÍCULOS VNR ===")
    print(filtrado[["veiculo", "inicioProgramado"]].to_string(index=False))


# ==============================
# ANÁLISE 2 - SAÍDA SEM RECOLHE
# ==============================
def analise_sem_par_saida_recolhe(df: pd.DataFrame):

    saida = df[df["atividade"] == "Saída de Garagem"]
    recolhe = df[df["atividade"] == "Recolhe"]

    somente_saida = saida[~saida["veiculo"].isin(recolhe["veiculo"])]
    somente_recolhe = recolhe[~recolhe["veiculo"].isin(saida["veiculo"])]

    resultado = pd.concat([somente_saida, somente_recolhe])

    print("\n=== VEÍCULOS SEM PAR SAÍDA/RECOLHE ===")
    print(resultado[["veiculo"]].drop_duplicates().to_string(index=False))


# ==============================
# ANÁLISE 3 - ATRASOS (>6 MIN)
# ==============================
def analise_atrasos(df: pd.DataFrame):

    df = df.copy()

    df["Atraso"] = (
        (df["inicioRealizado"] - df["inicioProgramado"])
        .dt.total_seconds()
        > 6 * 60
    )

    filtrado = df[
        (df["atividade"] == "Viagem Normal") &
        (df["sentido"] == "I") &
        (df["Atraso"])
    ].sort_values("inicioProgramado")

    print("\n=== VIAGENS COM ATRASO > 6 MIN ===")
    print(
        filtrado[
            [
                "atividade",
                "linha",
                "veiculo",
                "inicioProgramado",
                "inicioRealizado",
                "Atraso"
            ]
        ].to_string(index=False)
    )


# ==============================
# MAIN
# ==============================
def main():

    token = autenticar()
    if not token:
        return

    df = consultar_viagens(token, "16/02/2026")
    if df is None:
        return

    df = preparar_dados(df)

    analise_vnr(df)
    analise_sem_par_saida_recolhe(df)
    analise_atrasos(df)


if __name__ == "__main__":
    main()