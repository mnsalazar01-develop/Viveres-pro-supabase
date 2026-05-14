import streamlit as st
from supabase import create_client
import os

# 1. CONFIGURACIÓN GLOBAL FORZADA DE LA APP (Línea de arranque obligatoria)
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

# Inicializamos y blindamos la conexión en el Session State global
if "supabase" not in st.session_state:
    st.session_state["supabase"] = init_connection()

# 3. ENRUTADOR MODULAR SECUENCIAL (Elimina el error de índices de texto)
st.sidebar.title("🛒 Control Víveres")
st.sidebar.caption("Versión 3.0 Modular Sólida")

try:
    pg = st.navigation([
        st.Page("pages/1.py", title="🔔 Alertas y Ofertas"),
        st.Page("pages/2.py", title="📊 Reportes Estadísticos"),
        st.Page("pages/3.py", title="📦 Gestión de Productos"),
        st.Page("pages/4.py", title="🗂️ Estructura (Cat/Subcat)"),
        st.Page("pages/5.py", title="🏪 Tiendas y Sucursales"),
        st.Page("pages/6.py", title="📝 Registrar Ofertas")
    ])
    pg.run()
except Exception as e:
    st.title("🛒 Bienvenidos a Control Víveres Pro v3.0")
    st.warning("⚠️ El sistema modular se está sincronizando con tu repositorio de GitHub.")
    with st.expander("Detalles técnicos del arranque"):
        st.code(f"Ruta actual del servidor: {os.getcwd()}\nError de mapeo: {e}")
