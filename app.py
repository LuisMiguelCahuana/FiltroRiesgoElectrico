import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO
import re

# CONFIG 
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
    match_iduunn = re.search(r"var DEFECTO_IDUUNN\s*=\s*'(\d+)'", response.text)
    if not match_iduunn:
        return None, False

    defecto_iduunn = int(match_iduunn.group(1))
    dashboard_response = session.get("http://sigof.distriluz.com.pe/plus/dashboard/modulos", headers=headers)
    if "login" in dashboard_response.text:
        return None, False

    return defecto_iduunn, True

def download_excel_from_drive(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    response = requests.get(url)
    return pd.read_excel(BytesIO(response.content)) if response.status_code == 200 else None

def descargar_archivo(session, codigo):
    zona = ZoneInfo("America/Lima")
    hoy = datetime.now(zona).strftime("%Y-%m-%d")
    url = f"http://sigof.distriluz.com.pe/plus/Reportes/ajax_ordenes_historico_xls/U/{hoy}/{hoy}/0/{codigo}/0/0/0/0/0/0/0/0/9/0"
    response = session.get(url, headers=headers)

    if response.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return response.content, f"ciclo_{codigo}_{hoy}.xlsx"
    else:
        return None, None

def filtrar_por_sector_y_obs(df, sectores_permitidos, obs_permitidas):
    df['sector'] = df['sector'].astype(str).str.strip()
    df['obs_descripcion'] = df['obs_descripcion'].astype(str).str.strip()
    return df[
        df['sector'].isin(sectores_permitidos) &
        df['obs_descripcion'].isin(obs_permitidas)
    ]

def main():
    st.set_page_config(page_title="Lmc Lectura", layout="centered")
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; width: 100%;">
        <h1 style="font-size: clamp(18px, 5vw, 35px); text-align: center; color: #0078D7;">
            🤖 Bienvenido al Sistema de Descarga SIGOF Lectura
        </h1>
    </div>
    """, unsafe_allow_html=True)

    if "session" not in st.session_state:
        st.session_state.session = None
    if "defecto_iduunn" not in st.session_state:
        st.session_state.defecto_iduunn = None
    if "ciclos_disponibles" not in st.session_state:
        st.session_state.ciclos_disponibles = {}
    if "archivos_descargados" not in st.session_state:
        st.session_state.archivos_descargados = {}

    if st.session_state.session is None:
        usuario = st.text_input("👤 Humano ingrese su usuario SIGOF")
        password = st.text_input("🔒 Humano ingrese su contraseña SIGOF", type="password")

        if st.button("Iniciar sesión"):
            if not usuario or not password:
                st.warning("⚠️ Humano ingrese usuario y contraseña.")
            else:
                session = requests.Session()
                defecto_iduunn, login_ok = login_and_get_defecto_iduunn(session, usuario, password)

                if not login_ok:
                    st.error("❌ Humano login fallido. Verifique sus credenciales.")
                else:
                    st.session_state.session = session
                    st.session_state.defecto_iduunn = defecto_iduunn

                    df_ciclos = download_excel_from_drive(FILE_ID)
                    if df_ciclos is None:
                        st.error("❌ Humano no se pudo descargar el Excel con ciclos.")
                        return

                    df_ciclos['id_unidad'] = pd.to_numeric(df_ciclos['id_unidad'], errors='coerce').fillna(-1).astype(int)
                    df_ciclos = df_ciclos[df_ciclos['id_unidad'] == defecto_iduunn]

                    ciclos_dict = {
                        f"{row['Id_ciclo']} {row['nombre_ciclo']}": str(row['Id_ciclo'])
                        for _, row in df_ciclos.iterrows()
                        if pd.notnull(row['Id_ciclo']) and pd.notnull(row['nombre_ciclo'])
                    }

                    if not ciclos_dict:
                        st.warning("⚠️ Humano no se encontraron ciclos para este ID.")
                    else:
                        st.session_state.ciclos_disponibles = ciclos_dict

                    st.rerun()

    if st.session_state.ciclos_disponibles:
        st.markdown("""
        <div style="display: flex; justify-content: left; align-items: left; width: 100%;">
            <h5 style="font-size: clamp(14px, 5vw, 25px); text-align: center; color: #0078D7;">
                🔎 Humano seleccione uno o más ciclos para descargar:
            </h5>
        </div>
        """, unsafe_allow_html=True)

        opciones = list(st.session_state.ciclos_disponibles.keys())
        seleccionar_todos = st.checkbox("Humano si desea puede seleccionar todos los ciclos")

        if seleccionar_todos:
            seleccionados = st.multiselect("Ciclos disponibles", options=opciones, default=opciones)
        else:
            seleccionados = st.multiselect("Ciclos disponibles", options=opciones)

        if st.button("📥 Descargar Ciclos Seleccionados"):
            if not seleccionados:
                st.warning("⚠️ Humano seleccione al menos un ciclo.")
            else:
                st.session_state.archivos_descargados.clear()
                df_ciclos = download_excel_from_drive(FILE_ID)

                for nombre_concatenado in seleccionados:
                    codigo = st.session_state.ciclos_disponibles[nombre_concatenado]
                    datos_filtro = df_ciclos[df_ciclos['Id_ciclo'] == int(codigo)].iloc[0]

                    sectores = [s.strip() for s in str(datos_filtro['sectores']).split(',')]
                    observaciones = [o.strip() for o in str(datos_filtro['observaciones_permitidas']).split(',')]

                    contenido, _ = descargar_archivo(st.session_state.session, codigo)

                    if contenido:
                        df_archivo = pd.read_excel(BytesIO(contenido))
                        columnas = df_archivo.columns.str.lower()

                        if 'sector' in columnas.tolist() and 'obs_descripcion' in columnas.tolist():
                            df_archivo.columns = columnas
                            df_filtrado = filtrar_por_sector_y_obs(df_archivo, sectores, observaciones)
                            buffer = BytesIO()
                            df_filtrado.to_excel(buffer, index=False)
                            buffer.seek(0)

                            filename = f"{nombre_concatenado}.xlsx"
                            st.session_state.archivos_descargados[filename] = buffer.read()
                        else:
                            st.warning(f"⚠️ El archivo del ciclo {codigo} no tiene las columnas necesarias.")
                    else:
                        st.warning(f"⚠️ Error al descargar ciclo {codigo}")

    # ⬇️ Sección modificada: Solo exportar la columna 'suministro'
    if st.session_state.archivos_descargados:
        st.markdown("### ✅ Archivos listos para descargar:")
        for filename, contenido in st.session_state.archivos_descargados.items():
            df_completo = pd.read_excel(BytesIO(contenido))

            if 'suministro' in df_completo.columns:
                df_solo_suministro = df_completo[['suministro']].copy()
                buffer_solo = BytesIO()
                df_solo_suministro.to_excel(buffer_solo, index=False)
                buffer_solo.seek(0)

                st.download_button(
                    label=f"⬇️ Descargar {filename} (solo suministro)",
                    data=buffer_solo,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning(f"⚠️ El archivo {filename} no contiene la columna 'suministro'.")

if __name__ == "__main__":
    main()

# PIE DE PÁGINA
st.markdown("""
    <style>
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        background-color: white;
        padding: 10px 8px;
        text-align: center;
        font-size: 14px;
        color: gray;
        z-index: 9999;
        border-top: 1px solid #ddd;
    }
    </style>
    <div class="footer">
        Desarrollado por Luis M. Cahuana F.
    </div>
""", unsafe_allow_html=True)
