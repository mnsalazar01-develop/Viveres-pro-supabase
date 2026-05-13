import streamlit as st
from supabase import create_client

# 1. CONFIGURACIÓN ESTRÉSTICA DE ARRANQUE GLOBAL
st.set_page_config(page_title="Control Víveres Pro v3.0", layout="wide", page_icon="🛒")

# 2. CONEXIÓN UNIFICADA COMPARTIDA A SUPABASE
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Error crítico de configuración en los Secrets de la App: {e}")
        st.stop()

# Inyectamos el motor de la base de datos en el estado global compartido de Streamlit
if "supabase" not in st.session_state:
    st.session_state["supabase"] = init_connection()

# 3. ENRUTADOR MODULAR FLUIDO (Nombres limpios sin caracteres especiales para Python 3.14+)
st.sidebar.title("🛒 Control Víveres")
st.sidebar.caption("Estructura Modular Sólida v3.0")

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
    st.title("🛒 Control Víveres Pro v3.0")
    st.warning("⚠️ Sincronizando módulos con el repositorio de GitHub...")
    with st.expander("Detalles de inicialización del servidor"):
        st.code(f"Error de mapeo modular: {e}")
