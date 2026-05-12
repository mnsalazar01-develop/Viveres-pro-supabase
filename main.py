import streamlit as st
from supabase import create_client
import pandas as pd

# Conexión limpia
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.title("🛒 Control de Víveres v2.0")

# Prueba de conexión chismosa
try:
    # Intentamos listar las tablas para ver si el nombre es correcto
    res = supabase.table("productos").select("*").execute()
    st.success("✅ ¡Conexión perfecta con Supabase!")
    
    if res.data:
        st.dataframe(pd.DataFrame(res.data))
    else:
        st.info("La tabla 'productos' está vacía. ¡Usa el formulario para agregar uno!")

except Exception as e:
    st.error(f"Error de comunicación: {e}")
    st.info("💡 Consejo: Revisa que en Supabase la tabla se llame 'productos' (en minúsculas).")
