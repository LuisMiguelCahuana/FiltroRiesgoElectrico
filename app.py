
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# CONFIGURACIÓN GOOGLE SHEETS
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# ID de tu Google Sheet
SHEET_ID = "TU_GOOGLE_SHEET_ID"
sheet = client.open_by_key(SHEET_ID).sheet1
data = sheet.get_all_records()
df_config = pd.DataFrame(data)

st.title("Descarga de archivos SIGOF por Ciclo")

# Filtros: Selección de Ciclo
ciclos_disponibles = df_config['nombre_ciclo'].unique()
ciclo_seleccionado = st.selectbox("Selecciona un ciclo", ciclos_disponibles)

# Obtener datos del ciclo seleccionado
filtro_ciclo = df_config[df_config['nombre_ciclo'] == ciclo_seleccionado].iloc[0]
sectores = [s.strip() for s in filtro_ciclo['sectores'].split(',')] if filtro_ciclo['sectores'] else []
observaciones = [o.strip() for o in filtro_ciclo['observaciones_permitidas'].split(',')] if filtro_ciclo['observaciones_permitidas'] else []

# Mostrar filtros adicionales
sector = st.selectbox("Selecciona un sector", sectores) if sectores else None
observacion = st.selectbox("Selecciona observación", observaciones) if observaciones else None

# URL LOGIN Y DESCARGA
login_url = "http://sigof.distriluz.com.pe/plus/usuario/login"
download_url = "http://sigof.distriluz.com.pe/plus/facturacion/descargar/"

# CREDENCIALES
username = st.text_input("Usuario SIGOF")
password = st.text_input("Contraseña SIGOF", type="password")

if st.button("Iniciar sesión y descargar archivo"):
    with requests.Session() as s:
        payload = {"username": username, "password": password}
        login = s.post(login_url, data=payload)
        if "bienvenido" in login.text.lower():
            st.success("Login exitoso")
            id_ciclo = filtro_ciclo["Id_ciclo"]
            file_url = f"{download_url}{id_ciclo}"
            r = s.get(file_url)
            if r.status_code == 200:
                st.success("Archivo descargado correctamente")
                st.download_button(label="Descargar Excel", data=r.content, file_name=f"Ciclo_{id_ciclo}.xlsx")
            else:
                st.error("Error al descargar archivo")
        else:
            st.error("Credenciales incorrectas")
