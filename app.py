import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

# CONFIGURACIÓN
st.set_page_config(layout="wide")
st.title("📥 Descarga de archivos SIGOF por ciclo")

# ID DEL ARCHIVO DE GOOGLE SHEETS CON CONFIGURACIÓN
CONFIG_SHEET_ID = "1td-2WGFN0FUlas0Vx8yYUSb7EZc7MbGWjHDtJYhEY-0"

@st.cache_data(ttl=3600)
def cargar_configuracion():
    url = f"https://docs.google.com/spreadsheets/d/{CONFIG_SHEET_ID}/export?format=csv"
    df = pd.read_csv(url, dtype=str).fillna("")
    return df

def obtener_archivo_desde_sigof(codigo):
    url_login = "http://sigof.distriluz.com.pe/plus/usuario/login"
    url_lista = "http://sigof.distriluz.com.pe/plus/facturacion/consultaarchivos/"
    sesion = requests.Session()
    sesion.post(url_login, data={"username": "censo", "password": "distriluz"})
    respuesta = sesion.get(url_lista)
    soup = BeautifulSoup(respuesta.content, "html.parser")
    enlace = soup.find("a", string=lambda text: text and codigo in text)
    if enlace:
        url_descarga = "http://sigof.distriluz.com.pe" + enlace["href"]
        archivo = sesion.get(url_descarga)
        return BytesIO(archivo.content)
    return None

def formatear_fecha():
    tz = ZoneInfo("America/Lima")
    ahora = datetime.now(tz)
    return ahora.strftime("%Y-%m-%d %H:%M:%S")

# CARGAR CONFIGURACIÓN DESDE GOOGLE SHEETS
df_config = cargar_configuracion()
st.session_state.obs_dict = dict(zip(df_config['Id_ciclo'], df_config['observaciones_permitidas']))
st.session_state.sector_dict = dict(zip(df_config['Id_ciclo'], df_config['sectores']))

# FORMULARIO
with st.form("formulario"):
    codigo = st.selectbox("Selecciona el ciclo", df_config['Id_ciclo'].unique())
    aplicar_obs = st.checkbox("Filtrar por observaciones permitidas")
    submit = st.form_submit_button("Descargar y filtrar")

if submit:
    archivo = obtener_archivo_desde_sigof(codigo)
    if archivo:
        df = pd.read_excel(archivo)

        # Filtrar sectores
        sectores_str = st.session_state.sector_dict.get(codigo, "")
        sectores_lista = [int(s.strip()) for s in sectores_str.split(",") if s.strip().isdigit()]
        if sectores_lista:
            df['sector'] = pd.to_numeric(df['sector'], errors='coerce')
            df = df[df['sector'].isin(sectores_lista)]

        # Filtrar observaciones
        obs_raw = st.session_state.obs_dict.get(codigo, "")
        obs_permitidas = [o.strip() for o in obs_raw.split(",") if o.strip()]
        if aplicar_obs and obs_permitidas:
            df = df[df['obs_descripcion'].isin(obs_permitidas)]

        # Mostrar resultados
        st.success(f"✅ Archivo filtrado correctamente ({len(df)} registros)")
        st.write(df)

        # Descargar archivo
        nombre_salida = f"SIGOF_filtrado_{codigo}_{formatear_fecha().replace(':', '-')}.xlsx"
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Descargar archivo filtrado", buffer.getvalue(), file_name=nombre_salida)
    else:
        st.error("❌ No se encontró el archivo para el ciclo indicado.")
