import streamlit as st
from supabase import create_client
import importlib.util
import os

# 1. CONFIGURACIÓN GLOBAL FORZADA DE LA APP
st.set_page_config(page_title="Control Víveres Pro v3.0", layout="wide", page_icon="🛒")

# 2. CONEXIÓN MAESTRA CENTRALIZADA A SUPABASE
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Falta configurar las llaves en los Secrets de Streamlit: {e}")
        st.stop()

if "supabase" not in st.session_state:
    st.session_state["supabase"] = init_connection()

# 3. INTERFAZ DE EMERGENCIA SIN BUCO DE CACHÉ
st.sidebar.title("🛒 Control Víveres")
st.sidebar.caption("Modo de Contingencia Sólido")

# Definimos el menú manual en la barra lateral
opcion = st.sidebar.selectbox("Ir a:", ["📦 Gestión de Productos"])

# Carga forzada del archivo de productos saltando el st.navigation() corrupto de la nube
if opcion == "📦 Gestión de Productos":
    # Buscamos el archivo en la raíz o en la carpeta vistas de forma segura
    ruta_raiz = "3.py"
    ruta_vistas = "vistas/3.py"
    
    archivo_a_cargar = None
    if os.path.exists(ruta_raiz):
        archivo_a_cargar = ruta_raiz
    elif os.path.exists(ruta_vistas):
        archivo_a_cargar = ruta_vistas

    if archivo_a_cargar:
        try:
            # Ejecutamos el archivo de productos directamente en la pantalla actual
            spec = importlib.util.spec_from_file_location("modulo_productos", archivo_a_cargar)
            modulo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modulo)
        except Exception as err_ejecucion:
            st.error(f"🚨 Error al renderizar la pantalla de productos: {err_ejecucion}")
    else:
        st.error("⚠️ No se encontró el archivo '3.py'. Asegúrate de tenerlo en la raíz de tu GitHub o dentro de la carpeta 'vistas/3.py'.")
