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

# 3. ENRUTADOR MODULAR UNIVERSAL (Garantiza el renderizado de la barra lateral en Python 3.14+)
st.sidebar.title("🛒 Control Víveres")
st.sidebar.caption("Versión 3.0 Modular Sólida")

# Forzamos la declaración explícita de rutas físicas de archivos para evitar bloqueos del servidor
try:
    pg = st.navigation([
        st.Page("pages/1_🔍_Alertas_y_Ofertas.py", title="🔔 Alertas y Ofertas", icon="🔍"),
        st.Page("pages/2_📊_Reportes_Estadisticos.py", title="📊 Reportes Estadísticos", icon="📈"),
        st.Page("pages/3_📦_Gestión_de_Productos.py", title="📦 Gestión de Productos", icon="🛠️"),
        st.Page("pages/4_📁_Estructura_Cat_Subcat.py", title="🗂️ Estructura (Cat/Subcat)", icon="🗂️"),
        st.Page("pages/5_🏪_Tiendas_y_Sucursales.py", title="🏪 Tiendas y Sucursales", icon="🏪"),
        st.Page("pages/6_🏷️_Registrar_Ofertas.py", title="📝 Registrar Ofertas", icon="📝"),
    ])
    pg.run()
except Exception as e:
    # Pantalla de auxilio por si GitHub tiene problemas de sincronización de carpetas
    st.title("🛒 Bienvenidos a Control Víveres Pro v3.0")
    st.warning("⚠️ El sistema modular se está sincronizando con tu repositorio de GitHub.")
    st.info("💡 **Guía de Activación:** Asegúrate de que los archivos de las pantallas estén guardados exactamente dentro de una carpeta llamada `pages` en tu GitHub. En cuanto GitHub termine de procesar las carpetas, los menús aparecerán a la izquierda automáticamente.")
    with st.expander("Detalles técnicos del arranque"):
        st.code(f"Ruta actual del servidor: {os.getcwd()}\nError de mapeo: {e}")
