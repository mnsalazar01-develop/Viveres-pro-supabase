import streamlit as st
from supabase import create_client
import pandas as pd

# 1. Conexión (Asegúrate de que esté al inicio de tu main.py)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- FUNCIÓN PARA SUBIR A STORAGE (ACTUALIZADA PARA WEBP) ---
def subir_a_storage(archivo):
    if archivo:
        try:
            # Quitamos espacios y caracteres raros del nombre
            nombre_limpio = archivo.name.replace(" ", "_")
            nombre_archivo = f"img_{nombre_limpio}"
            
            # Subir al bucket 'imagenes'
            supabase.storage.from_("imagenes").upload(
                path=nombre_archivo, 
                file=archivo.getvalue(), 
                file_options={"content-type": archivo.type} # Detecta image/webp automáticamente
            )
            # Obtener URL pública
            url_img = supabase.storage.from_("imagenes").get_public_url(nombre_archivo)
            return url_img
        except Exception as e:
            st.error(f"Error al subir imagen: {e}")
    return None

# --- EN EL FORMULARIO DE REGISTRO ---
# Agregamos 'webp' a la lista de tipos
#archivo_foto = st.file_uploader(
#    "📸 Subir foto o Tomar captura", 
#    type=['jpg', 'png', 'jpeg', 'webp'] 
#)


# 2. Formulario de Registro Completo
with st.form("registro_viveres", clear_on_submit=True):
    st.subheader("📝 Registrar Nuevo Producto")
    
    col1, col2 = st.columns(2)
    
    with col1:
        nombre = st.text_input("Nombre del Producto*")
        marca = st.text_input("Marca")
        tamano = st.number_input("Tamaño / Peso", min_value=0.0, step=0.1)
        unidad = st.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad", "pack"])
        
    with col2:
        archivo_foto = st.file_uploader("📸 Subir foto o Tomar captura", type=['jpg', 'png', 'jpeg', 'webp'])
        url_respaldo = st.text_input("O pegar URL externa (opcional)")
        st.caption("Si subes un archivo, este tendrá prioridad sobre la URL manual.")

    if st.form_submit_button("🚀 Guardar Producto"):
        if nombre:
            url_final = None
            
            # Lógica de imagen
            if archivo_foto:
                url_final = subir_a_storage(archivo_foto)
            elif url_respaldo:
                url_final = url_respaldo
            
            # Guardar en Supabase (campos en minúsculas)
            nuevo_registro = {
                "nombre": nombre,
                "marca": marca,
                "tamano": tamano,
                "unidad": unidad,
                "url_imagen": url_final
            }
            
            try:
                supabase.table("productos").insert(nuevo_registro).execute()
                st.success(f"✅ {nombre} guardado con éxito.")
                st.balloons()
            except Exception as e:
                st.error(f"Error al guardar en la base de datos: {e}")
        else:
            st.warning("El campo 'Nombre' es obligatorio.")

# 3. Tabla Visualizadora
st.divider()
st.subheader("📋 Catálogo Actualizado")
res = supabase.table("productos").select("*").execute()
if res.data:
    df = pd.DataFrame(res.data)
    # Configuración para que las imágenes se vean en la tabla
    st.dataframe(
        df[['nombre', 'marca', 'tamano', 'unidad', 'url_imagen']],
        column_config={
            "url_imagen": st.column_config.ImageColumn("Vista Previa")
        },
        use_container_width=True
    )
