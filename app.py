import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO
import re
import xlwt

# CONFIGURACIÓN
login_url = "http://sigof.distriluz.com.pe/plus/usuario/login"
FILE_ID = "1td-2v5Dj_drpAwCJ8NfWZpNR6mIEvU3H"
ZONA_HORARIA = ZoneInfo("America/Lima")

# TÍTULO CENTRADO Y AJUSTADO
st.markdown(
    "<h1 style='text-align: center; font-size: 250%;'>📥 FILTRO DE SUMINISTROS</h1>",
    unsafe_allow_html=True,
)

# LOGIN
with st.form("login_form"):
    st.subheader("🔐 Iniciar sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    submitted = st.form_submit_button("Iniciar sesión")

if submitted:
    with requests.Session() as session:
        response = session.get(login_url)
        soup = BeautifulSoup(response.content, "html.parser")
        token = soup.find("input", {"name": "_token"}).get("value")

        login_data = {
            "_token": token,
            "usuario": username,
            "password": password,
        }

        login_response = session.post(login_url, data=login_data)

        if "Ha ocurrido un error" in login_response.text:
            st.error("❌ Usuario o contraseña incorrectos")
        else:
            st.success("✅ ¡Login exitoso!")
            st.session_state.session = session

# FUNCIONES
def descargar_excel(ciclo):
    url = f"http://sigof.distriluz.com.pe/plus/riesgoelectrico/exportar-excel/{ciclo}"
    response = st.session_state.session.get(url)
    if response.status_code == 200:
        return pd.read_excel(BytesIO(response.content))
    else:
        st.warning(f"No se pudo descargar el ciclo {ciclo}")
        return None

@st.cache_data
def obtener_ciclos_disponibles(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    content = requests.get(url).content
    df_ciclos = pd.read_excel(BytesIO(content), sheet_name=0)
    return df_ciclos

# EJECUCIÓN PRINCIPAL
def main():
    if "session" not in st.session_state:
        return

    df_ciclos = obtener_ciclos_disponibles(FILE_ID)

    ciclos = df_ciclos["Id_ciclo"].astype(str) + " " + df_ciclos["nombre_ciclo"]
    ciclo_seleccionado = st.selectbox("Selecciona el ciclo:", ciclos)

    if st.button("📤 Descargar archivo filtrado"):
        id_ciclo = ciclo_seleccionado.split(" ")[0]
        df = descargar_excel(id_ciclo)

        if df is not None:
            columnas = df.columns

            if "suministro" not in columnas:
                st.error("⚠️ No se encontró la columna 'suministro'")
                return

            df_solo_suministro = df[["suministro"]].drop_duplicates()

            # Crear archivo .xls usando xlwt
            workbook = xlwt.Workbook()
            sheet = workbook.add_sheet("Suministros")

            for row_idx, value in enumerate(df_solo_suministro["suministro"]):
                sheet.write(row_idx, 0, str(value))

            buffer_solo = BytesIO()
            workbook.save(buffer_solo)
            buffer_solo.seek(0)

            nombre_archivo = f"{id_ciclo} formato_suministros.xls"

            st.download_button(
                label="📥 Descargar formato suministros (.xls)",
                data=buffer_solo,
                file_name=nombre_archivo,
                mime="application/vnd.ms-excel"
            )
        else:
            st.error("❌ No se pudo descargar el archivo desde SIGOF.")

if __name__ == "__main__":
    main()
