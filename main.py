import streamlit as st
from supabase import create_client
import pandas as pd

# 1. Conexión
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Viveres Pro", layout="wide", page_icon="🛒")

# 2. Menú Lateral
menu = ["📊 Dashboard", "📦 Productos", "🏪 Tiendas y Sucursales"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- SECCIÓN: PRODUCTOS (La que ya probamos) ---
if choice == "📦 Productos":
    st.title("📦 Gestión de Productos")
    # ... (aquí va tu formulario de carga anterior) ...
    # Sugerencia: Añadir un visualizador de lo que ya hay
    res = supabase.table("productos").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data), use_container_width=True)

# --- NUEVA SECCIÓN: TIENDAS ---
elif choice == "🏪 Tiendas y Sucursales":
    st.title("🏪 Configuración de Tiendas")
    
    tab1, tab2 = st.tabs(["🏢 Cadenas de Supermercados", "📍 Sucursales Específicas"])
    
    with tab1:
        st.subheader("Registrar Nueva Cadena")
        with st.form("form_super"):
            nombre_super = st.text_input("Nombre del Supermercado (Ej: Walmart)")
            logo = st.text_input("URL del Logo")
            if st.form_submit_button("Guardar Cadena"):
                supabase.table("supermercados").insert({"nombre_supermercado": nombre_super, "url_logo": logo}).execute()
                st.success(f"{nombre_super} agregado.")
                st.rerun()

    with tab2:
        st.subheader("Registrar Sucursal")
        # Obtenemos los supermercados para el menú desplegable
        supers = supabase.table("supermercados").select("*").execute()
        if supers.data:
            df_s = pd.DataFrame(supers.data)
            dict_supers = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
            
            with st.form("form_sucursal"):
                cadena = st.selectbox("Selecciona la Cadena", list(dict_supers.keys()))
                nombre_suc = st.text_input("Nombre de la Sucursal (Ej: Centro)")
                ciudad = st.text_input("Ciudad")
                
                if st.form_submit_button("Guardar Sucursal"):
                    nueva_suc = {
                        "id_super": dict_supers[cadena],
                        "nombre_sucursal": nombre_suc,
                        "ciudad": ciudad
                    }
                    supabase.table("sucursales").insert(nueva_suc).execute()
                    st.success("Sucursal guardada correctamente.")
                    st.rerun()
        else:
            st.warning("Primero debes registrar al menos un Supermercado en la pestaña anterior.")
