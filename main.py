import streamlit as st
from supabase import create_client

# 1. CONFIGURACIÓN GLOBAL DE LA APP
st.set_page_config(page_title="Control Víveres Pro v3.0", layout="wide", page_icon="🛒")

# 2. CONEXIÓN MAESTRA COMPARTIDA A SUPABASE
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# Inicializamos la conexión en la memoria global de la app (Session State)
if "supabase" not in st.session_state:
    st.session_state["supabase"] = init_connection()

# 3. PANTALLA DE BIENVENIDA
st.title("🛒 Bienvenidos a Control Víveres Pro v3.0")
st.markdown("""
### ¡Tu asistente modular de ahorro está listo!
Mira la barra lateral de la izquierda. Ahora la aplicación está dividida en programas independientes para mayor velocidad y orden.
""")

with st.container(border=True):
    st.subheader("💡 Estado del Sistema")
    try:
        # Hacemos una mini prueba para garantizar que hay conexión antes de abrir los módulos
        st.session_state["supabase"].table("categorias").select("id_cat").limit(1).execute()
        st.success("✅ Base de Datos Supabase: **Conectada y lista**")
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")

st.info("👈 Selecciona cualquiera de los programas en el menú lateral para empezar a trabajar.")
