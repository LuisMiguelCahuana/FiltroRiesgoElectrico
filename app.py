import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO

# CONFIGURACIÓN
login_url = "http://sigof.distriluz.com.pe/plus/usuario/login"
FILE_ID = "1td-2WGFN0FUlas0Vx8yYUSb7EZc7MbGWjHDtJYhEY-0"  # ID del archivo Google Sheets
EXCEL_URL = f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx"

# DESCARGAR ARCHIVO DE CONFIGURACIÓN DESDE GOOGLE DRIVE
@st.cache_data
def download_excel_from_drive(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    response = requests.get(url)
    if response.status_code == 200:
        return pd.read_excel(BytesIO(response.content))
    else:
        st.error("❌ No se pudo descargar el archivo de configuración.")
        return pd.DataFrame()

# INICIAR SESIÓN EN SIGOF
def iniciar_sesion(usuario, clave):
    session = requests.Session()
    data = {
        'username': usuario,
        'password': clave
    }
    response = session.post(login_url, data=data)
    if response.url.endswith("/login"):
        return None
    return session

# DESCARGAR ARCHIVO POR ID DE CICLO
def descargar_archivo(session, ciclo_id):
    ciclo_url = f"http://sigof.distriluz.com.pe/plus/visita/listar?id={ciclo_id}"
    response = session.get(ciclo_url)
    if "Exportar Excel" not in response.text:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    export_link = soup.find('a', string="Exportar Excel")
    if export_link:
        href = export_link.get('href')
        archivo_url = f"http://sigof.distriluz.com.pe{href}"
        archivo_response = session.get(archivo_url)
        if archivo_response.status_code == 200:
            return archivo_response.content
    return None

# INTERFAZ PRINCIPAL
def main():
    st.set_page_config(page_title="SIGOF Downloader", layout="wide")
    st.title("📥 SIGOF Downloader")
    st.markdown("Esta app permite descargar archivos Excel por ciclos desde el sistema SIGOF.")

    if "session" not in st.session_state:
        st.session_state.session = None
        st.session_state.archivos_descargados = {}
        st.session_state.ciclo_display_dict = {}
        st.session_state.ciclo_nombre_dict = {}

    if st.session_state.session is None:
        st.subheader("🔐 Inicio de sesión SIGOF")
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        if st.button("Iniciar sesión"):
            session = iniciar_sesion(usuario, clave)
            if session:
                st.success("✅ Inicio de sesión exitoso.")
                st.session_state.session = session
            else:
                st.error("❌ Usuario o contraseña incorrectos.")
        return

    st.subheader("📄 Selección de ciclos")
    df = download_excel_from_drive(FILE_ID)

    if df.empty:
        st.warning("⚠️ No se pudo cargar el archivo de configuración.")
        return

    ciclos = df["Nombre_ciclo"].tolist()
    st.session_state.ciclo_display_dict = dict(zip(df["Nombre_ciclo"], df["Id_ciclo"]))
    st.session_state.ciclo_nombre_dict = dict(zip(df["Id_ciclo"], df["Nombre_ciclo"]))

    elegidos_disp = st.multiselect("Seleccione uno o más ciclos:", ciclos)

    if st.button("📥 Descargar ciclos seleccionados"):
        if not elegidos_disp:
            st.warning("⚠️ Seleccione al menos un ciclo.")
        else:
            st.session_state.archivos_descargados.clear()

            for display in elegidos_disp:
                codigo = st.session_state.ciclo_display_dict[display]
                row = df[df['Id_ciclo'].astype(str) == str(codigo)].iloc[0]

                # Obtener filtros de sector y observación
                sectores = [s.strip() for s in str(row.get('sectores', '')).split(',') if s.strip()]
                observaciones = [o.strip() for o in str(row.get('observaciones_permitidas', '')).split(',') if o.strip()]

                # Mostrar filtros si están disponibles
                if sectores:
                    st.selectbox(f"📌 Seleccione sector para {display}", sectores, key=f"sector_{codigo}")
                if observaciones:
                    st.selectbox(f"📋 Seleccione observación para {display}", observaciones, key=f"obs_{codigo}")

                contenido = descargar_archivo(st.session_state.session, codigo)
                if contenido:
                    nombre_display = st.session_state.ciclo_nombre_dict.get(codigo, f"Ciclo_{codigo}")
                    fname = f"{nombre_display}.xlsx"
                    st.session_state.archivos_descargados[fname] = contenido
                    st.success(f"✅ Descargado: {fname}")
                else:
                    st.warning(f"⚠️ No se pudo descargar {display}")

    if st.session_state.archivos_descargados:
        st.subheader("📂 Archivos descargados")
        for nombre, contenido in st.session_state.archivos_descargados.items():
            st.download_button(
                label=f"⬇️ Descargar {nombre}",
                data=contenido,
                file_name=nombre,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
