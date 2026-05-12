import streamlit as st
from supabase import create_client

# Conexión limpia a Supabase
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

st.title("🛒 Control de Víveres v2.0")

# Prueba rápida de conexión
try:
    # Intentamos leer la tabla de productos que creamos con el script SQL
    res = supabase.table("productos").select("*").limit(1).execute()
    st.success("✅ ¡Conexión perfecta con Supabase!")
    
    menu = ["📊 Dashboard", "📦 Productos", "🏷️ Ofertas"]
    choice = st.sidebar.selectbox("Menú", menu)
    
    if choice == "📦 Productos":
        st.subheader("Listado de Productos")
        df = pd.DataFrame(supabase.table("productos").select("*").execute().data)
        st.dataframe(df)

except Exception as e:
    st.error(f"Esperando configuración o datos: {e}")
