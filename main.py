import streamlit as st
from supabase import create_client
import pandas as pd

# 1. Conexión (Ya sabemos que funciona)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Viveres Pro", layout="wide", page_icon="🛒")
st.title("🛒 Control de Víveres v2.0")

# 2. Barra Lateral para Navegación
menu = ["📦 Catálogo de Productos", "➕ Registrar Producto", "📊 Dashboard"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if choice == "📦 Catálogo de Productos":
    st.subheader("📦 Productos en Inventario")
    try:
        res = supabase.table("productos").select("*").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Reordenamos columnas para que se vea mejor
            cols = ['codigo_barras', 'nombre', 'marca', 'tamano', 'unidad']
            st.dataframe(df[cols], use_container_width=True)
        else:
            st.info("El catálogo está vacío. Ve a 'Registrar Producto' para empezar.")
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")

elif choice == "➕ Registrar Producto":
    st.subheader("📝 Nuevo Registro de Vívere")
    
    with st.form("form_registro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nombre = st.text_input("Nombre del Producto*", placeholder="Ej: Arroz")
            marca = st.text_input("Marca", placeholder="Ej: Diana")
            codigo = st.text_input("Código de Barras", placeholder="EAN-13 / UPC")
            
        with col2:
            tamano = st.number_input("Tamaño (Cantidad)", min_value=0.0, step=0.1)
            unidad = st.selectbox("Unidad de Medida", ["kg", "gr", "lt", "ml", "unidad", "pack"])
            url_img = st.text_input("URL de la Imagen", placeholder="https://enlace-a-la-foto.com")
            
        submit = st.form_submit_button("🚀 Guardar Producto")
        
        if submit:
            if nombre: # Validación básica
                nuevo_prod = {
                    "nombre": nombre,
                    "marca": marca,
                    "codigo_barras": codigo if codigo else None,
                    "tamano": tamano,
                    "unidad": unidad,
                    "url_imagen": url_img
                }
                try:
                    supabase.table("productos").insert(nuevo_prod).execute()
                    st.success(f"¡{nombre} guardado correctamente!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("El nombre del producto es obligatorio.")

elif choice == "📊 Dashboard":
    st.info("Aquí configuraremos el análisis de ofertas próximamente.")
