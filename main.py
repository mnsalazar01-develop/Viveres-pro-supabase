import streamlit as st
from supabase import create_client
import pandas as pd

# 1. Conexión
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIÓN PARA SUBIR A STORAGE ---
def subir_a_storage(archivo):
    if archivo:
        try:
            nombre_archivo = f"img_{archivo.name}"
            # Subir el archivo al bucket 'imagenes'
            supabase.storage.from_("imagenes").upload(
                path=nombre_archivo, 
                file=archivo.getvalue(), 
                file_options={"content-type": archivo.type}
            )
            # Obtener la URL pública
            url_img = supabase.storage.from_("imagenes").get_public_url(nombre_archivo)
            return url_img
        except Exception as e:
            st.error(f"Error al subir: {e}")
    return None

st.title("🛒 Gestión de Productos e Imágenes")

# 2. Formulario de Carga
with st.form("registro_con_foto", clear_on_submit=True):
    st.subheader("📸 Registrar Nuevo Producto")
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.text_input("Nombre del Producto*")
        marca = st.text_input("Marca")
        
    with col2:
        # Opción para subir archivo real
        archivo_foto = st.file_uploader("Subir foto o Tomar captura", type=['jpg', 'png', 'jpeg'])
        url_respaldo = st.text_input("O pegar URL externa (opcional)")

    if st.form_submit_button("🚀 Guardar Producto"):
        if nombre:
            url_final = None
            
            # Prioridad 1: Archivo subido al Storage
            if archivo_foto:
                url_final = subir_a_storage(archivo_foto)
            # Prioridad 2: URL manual
            elif url_respaldo:
                url_final = url_respaldo
            
            # Guardar en la tabla 'productos'
            nuevo = {
                "nombre": nombre,
                "marca": marca,
                "url_imagen": url_final
            }
            supabase.table("productos").insert(nuevo).execute()
            st.success(f"¡{nombre} guardado!")
            st.balloons()
        else:
            st.warning("Escribe al menos el nombre.")

# 3. Visualización (Para ver si funciona)
st.divider()
st.subheader("📦 Vista Previa del Catálogo")
res = supabase.table("productos").select("*").execute()
if res.data:
    df = pd.DataFrame(res.data)
    # Mostramos la imagen en la tabla si existe
    st.data_editor(
        df,
        column_config={
            "url_imagen": st.column_config.ImageColumn("Vista Previa")
        },
        use_container_width=True
    )
