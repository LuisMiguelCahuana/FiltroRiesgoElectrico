import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime

# CONFIGURACIÓN: ID del archivo de configuración (NO MODIFICAR)
FILE_ID = "1PCheVtYVf839zjbg5PJuyc4-_OpSvsWbjQBOi7rC258"

# FUNCIÓN: Descargar archivo de configuración desde Google Sheets
@st.cache_data
def cargar_configuracion(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    response = requests.get(url)
    return pd.read_excel(BytesIO(response.content))

# FUNCIÓN: Descargar archivo Excel de un ciclo desde la web
def descargar_archivo_excel(url):
    response = requests.get(url)
    return BytesIO(response.content)

# CARGAR CONFIGURACIÓN
df_config = cargar_configuracion(FILE_ID)

# FORMULARIO
with st.form("Filtro de ciclo"):
    ciclo_seleccionado = st.selectbox("Selecciona un ciclo disponible:", df_config["nombre_ciclo"].unique())
    st.write("Solo se filtrarán sectores y observaciones si existen.")
    boton_filtrar = st.form_submit_button("Descargar suministros filtrados")

# PROCESAMIENTO
if boton_filtrar:
    datos_ciclo = df_config[df_config["nombre_ciclo"] == ciclo_seleccionado].iloc[0]
    id_ciclo = datos_ciclo["Id_ciclo"]
    sectores_str = str(datos_ciclo["sectores"]) if pd.notna(datos_ciclo["sectores"]) else ""
    obs_str = str(datos_ciclo["observaciones_permitidas"]) if pd.notna(datos_ciclo["observaciones_permitidas"]) else ""

    # Descargar Excel del SIGOF (adaptar si tu URL cambia)
    url_excel = f"http://sigof.distriluz.com.pe/plus/facturacion/archivo/ciclo/{id_ciclo}"
    archivo = descargar_archivo_excel(url_excel)
    df = pd.read_excel(archivo)

    # Aplicar filtro por sectores
    if sectores_str:
        lista_sectores = [s.strip() for s in sectores_str.split(',')]
        df = df[df["sector"].astype(str).isin(lista_sectores)]

    # Aplicar filtro por observaciones
    if obs_str:
        lista_obs = [o.strip() for o in obs_str.split(',')]
        df = df[df["obs_descripcion"].astype(str).isin(lista_obs)]

    # Construir archivo final con solo columna "Suministros"
    df_final = pd.DataFrame()
    df_final["Suministros"] = df["suministro"]

    # Guardar archivo como formato_suministros.xls con hoja "Hoja1"
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlwt') as writer:
        df_final.to_excel(writer, sheet_name="Hoja1", index=False)
    output.seek(0)

    # Botón de descarga
    st.success("✅ Archivo generado correctamente.")
    st.download_button(
        label="📥 Descargar formato_suministros.xls",
        data=output,
        file_name="formato_suministros.xls",
        mime="application/vnd.ms-excel"
    )
