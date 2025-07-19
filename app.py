import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO
import re

# CONFIGURACIÓN
login_url = "http://sigof.distriluz.com.pe/plus/usuario/login"
FILE_ID = "1PCheVtYVf839zjbg5PJuyc4-_OpSvsWbjQBOi7rC258"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": login_url,
}

def login_and_get_defecto_iduunn(session, usuario, password):
    credentials = {
        "data[Usuario][usuario]": usuario,
        "data[Usuario][pass]": password
    }
    login_page = session.get(login_url, headers=headers)
    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf_token = soup.find("input", {"name": "_csrf_token"})
    if csrf_token:
        credentials["_csrf_token"] = csrf_token["value"]

    response = session.post(login_url, data=credentials, headers=headers)
    match = re.search(r"var DEFECTO_IDUUNN\s*=\s*'(\d+)'", response.text)
    if not match:
        return None, False

    defecto_iduunn = int(match.group(1))
    dash = session.get("http://sigof.distriluz.com.pe/plus/dashboard/modulos", headers=headers)
    if "login" in dash.text:
        return None, False

    return defecto_iduunn, True

def download_excel_from_drive(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    resp = requests.get(url)
    return pd.read_excel(BytesIO(resp.content)) if resp.status_code == 200 else None

def descargar_archivo(session, codigo):
    zona = ZoneInfo("America/Lima")
    hoy = datetime.now(zona).strftime("%Y-%m-%d")
    url = (
        f"http://sigof.distriluz.com.pe/plus/Reportes/ajax_ordenes_historico_xls/"
        f"U/{hoy}/{hoy}/0/{codigo}/0/0/0/0/0/0/0/0/9/0"
    )
    resp = session.get(url, headers=headers)
    if resp.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return resp.content
    return None

def mostrar_login():
    with st.form("login_form"):
        usuario = st.text_input("🕤 Usuario SIGOF")
        password = st.text_input("🔐 Contraseña SIGOF", type="password")
        submit = st.form_submit_button("🔐 Iniciar sesión")

    if submit:
        if not usuario or not password:
            st.warning("⚠️ Ingrese usuario y contraseña.")
        else:
            sess = requests.Session()
            defecto_iduunn, ok = login_and_get_defecto_iduunn(sess, usuario, password)
            if not ok:
                st.error("❌ Usuario o contraseña incorrectos.")
            else:
                st.session_state.session = sess
                st.session_state.defecto_iduunn = defecto_iduunn
                st.session_state.usuario = usuario
                st.session_state.sesion_activa = True

                df = download_excel_from_drive(FILE_ID)
                if df is None:
                    st.error("❌ No se pudo descargar el Excel de ciclos.")
                    return

                df.columns = df.columns.str.strip()
                df['id_unidad'] = pd.to_numeric(df['id_unidad'], errors='coerce').fillna(-1).astype(int)
                filtro = df[df['id_unidad'] == defecto_iduunn]

                col_id = next((c for c in df.columns if c.strip().lower() in ['id_ciclo', 'id ciclo']), None)
                col_nom = next((c for c in df.columns if c.strip().lower() in ['nombre_ciclo', 'nombre del ciclo', 'nombre ciclo']), None)

                if not col_id or not col_nom:
                    st.error("❌ El archivo Excel no tiene columnas válidas de 'Id_ciclo' o 'Nombre_ciclo'")
                    return

                filtro['id_ciclo'] = filtro[col_id].astype(str)
                filtro['nombre_ciclo'] = filtro[col_nom].astype(str)
                filtro['display'] = filtro['id_ciclo'] + " " + filtro['nombre_ciclo']

                st.session_state.ciclo_display_dict = dict(zip(filtro['display'], filtro['id_ciclo']))
                st.session_state.ciclo_nombre_dict = dict(zip(filtro['id_ciclo'], filtro['display']))
                st.session_state.ciclos_disponibles = list(st.session_state.ciclo_display_dict.keys())

                st.session_state.sectores_dict = dict(zip(filtro['id_ciclo'], filtro.get('sectores_permitidos', "")))
                st.session_state.obs_flag_dict = dict(zip(filtro['id_ciclo'], filtro.get('aplicar_filtro_obs', "NO")))

                st.rerun()

def main():
    st.set_page_config(page_title="Descarga SIGOF", layout="centered")
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; width: 100%;">
        <h1 style="font-size: clamp(18px, 5vw, 35px); text-align: center; color: #0078D7;">
            🤖 Bienvenido al Sistema de Descarga SIGOF Lectura
        </h1>
    </div>
    """, unsafe_allow_html=True)

    for key, default in {
        "session": None,
        "defecto_iduunn": None,
        "usuario": "",
        "sesion_activa": False,
        "ciclos_disponibles": [],
        "ciclo_display_dict": {},
        "ciclo_nombre_dict": {},
        "sectores_dict": {},
        "obs_flag_dict": {},
        "archivos_descargados": {}
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    if not st.session_state.sesion_activa:
        mostrar_login()
        return

    st.success(f"🔓 Sesión iniciada como: **{st.session_state.usuario}**")

    if st.session_state.ciclos_disponibles:
        st.markdown("Selecciona los ciclos a descargar")
        seleccionar_todos = st.checkbox("Seleccionar todos los ciclos")
        if seleccionar_todos:
            elegidos_disp = st.multiselect(
                "Ciclos disponibles",
                options=st.session_state.ciclos_disponibles,
                default=st.session_state.ciclos_disponibles
            )
        else:
            elegidos_disp = st.multiselect(
                "Ciclos disponibles",
                options=st.session_state.ciclos_disponibles
            )

        if st.button("📅 Descargar ciclos seleccionados"):
            if not elegidos_disp:
                st.warning("⚠️ Selecciona al menos un ciclo.")
            else:
                st.session_state.archivos_descargados.clear()
                for display in elegidos_disp:
                    codigo = st.session_state.ciclo_display_dict[display]
                    contenido = descargar_archivo(st.session_state.session, codigo)

                    if contenido:
                        nombre_display = st.session_state.ciclo_nombre_dict.get(codigo, f"Ciclo_{codigo}")
                        fname = f"{nombre_display}.xlsx"
                        df = pd.read_excel(BytesIO(contenido))
                        df.columns = df.columns.str.strip()

                        # Filtrado automático por sectores y observaciones
                        sectores_str = st.session_state.sectores_dict.get(codigo, "")
                        aplicar_obs = st.session_state.obs_flag_dict.get(codigo, "NO").upper() == "SÍ"

                        if sectores_str:
                            sectores_lista = [int(s.strip()) for s in sectores_str.split(",") if s.strip().isdigit()]
                            df = df[df['sector'].isin(sectores_lista)]

                        if aplicar_obs:
                            df = df[df['obs_descripcion'].isin(["Riesgo eléctrico", "Tapa desoldada / doblada"])]

                        output = BytesIO()
                        df.to_excel(output, index=False)
                        st.session_state.archivos_descargados[fname] = output.getvalue()
                    else:
                        st.warning(f"⚠️ No se pudo descargar {display}")

    if st.session_state.archivos_descargados:
        st.markdown("### ✅ Archivos listos para descargar:")
        for fname, data in st.session_state.archivos_descargados.items():
            st.download_button(
                label=f"⬇️ {fname}",
                data=data,
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
