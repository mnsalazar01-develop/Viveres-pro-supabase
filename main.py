import streamlit as st
from supabase import create_client
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

# 3. ENRUTADOR DE RUTAS INDEPENDIENTES (Evita el bucle de recursión de la carpeta pages)
st.sidebar.title("🛒 Control Víveres")
st.sidebar.caption("Versión 3.0 Modular Sólida")

try:
    # Vinculamos el archivo de productos apuntando de forma segura a la nueva carpeta 'vistas'
    p3 = st.Page("vistas/3.py", title="📦 Gestión de Productos")
    
    # El enrutador procesa únicamente la página de productos por el momento
    pg = st.navigation([p3])
    pg.run()
    
except Exception as e:
    st.title("🛒 Bienvenidos a Control Víveres Pro v3.0")
    st.warning("⚠️ El sistema modular se está sincronizando con tu repositorio de GitHub.")
    with st.expander("Detalles técnicos del arranque"):
        st.code(f"Ruta actual del servidor: {os.getcwd()}\nError de mapeo: {e}")
