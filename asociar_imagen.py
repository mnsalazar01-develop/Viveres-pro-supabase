import streamlit as st
import requests
import base64
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT ---
st.set_page_config(page_title="Carga Masiva Pro", page_icon="📦", layout="centered")
st.title("📦 Carga y Asociación Masiva de Imágenes")
st.write("Arrastra múltiples imágenes a la vez. El programa buscará el producto en Neon por el nombre de la foto.")

# Cargar secretos de forma segura desde Streamlit Cloud
try:
    url_limpia = st.secrets["neon"]["url"]
    IMGBB_API_KEY = st.secrets["imgbb"]["api_key"]
    IMGBB_ALBUM_ID = st.secrets["imgbb"]["album_id"]
except KeyError as e:
    st.error(f"❌ Error: Falta configurar la variable {e} en los Secrets de Streamlit.")
    st.stop()

# --- FUNCIÓN PARA SUBIR A IMGBB ---
def subir_imagen_a_album(imagen_bytes, nombre_limpio_foto):
    """Sube la imagen en memoria a ImgBB dentro del álbum especificado."""
    # ✅ URL Oficial de la API corregida para evitar el error de JSON
    url_api = "https://api.imgbb.com/1/upload"  
    
    try:
        # ✅ Incluye .decode('utf-8') para enviar texto limpio a ImgBB
        imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
        
        datos = {
            "key": IMGBB_API_KEY,
            "image": imagen_base64,
            "album_id": IMGBB_ALBUM_ID,
            "name": f"prod_{nombre_limpio_foto.replace(' ', '_').lower()}"
        }
        
        respuesta = requests.post(url_api, data=datos)
        resultado = respuesta.json()
        
        if resultado.get("status") == 200:
            return resultado["data"]["url"]
        return None
    except Exception:
        return None

# --- FUNCIÓN PARA PROCESAR EL LOTE ---
def procesar_lote_imagenes(archivos_subidos):
    """Recorre las fotos, busca el producto en Neon y actualiza las URLs."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        exitos = 0
        errores = 0
        
        # Barra de progreso visual en Streamlit
        barra_progreso = st.progress(0)
        total_archivos = len(archivos_subidos)
        
        for index, archivo in enumerate(archivos_subidos):
            # 1. Obtener el nombre del archivo sin la extensión (.jpg, .png, etc.)
            nombre_archivo_completo = archivo.name
            # ✅ Corrección de sintaxis para extraer correctamente el nombre limpio
            nombre_sin_extension = nombre_archivo_completo.rsplit('.', 1)[0].strip()
            
            # 2. Buscar en Neon si existe un producto con ese nombre exacto (ignorando mayúsculas/minúsculas)
            query_buscar = "SELECT id_producto, nombre FROM public.productos WHERE LOWER(nombre) = LOWER(%s) LIMIT 1;"
            cur.execute(query_buscar, (nombre_sin_extension,))
            producto = cur.fetchone()
            
            if producto:
                id_prod = producto['id_producto']
                nombre_real_prod = producto['nombre']
                
                # 3. Leer los bytes de la foto y subirla a ImgBB
                bytes_foto = archivo.read()
                url_foto = subir_imagen_a_album(bytes_foto, nombre_sin_extension)
                
                if url_foto:
                    # 4. Actualizar el registro en Neon
                    query_update = "UPDATE public.productos SET url_imagen = %s WHERE id_producto = %s;"
                    cur.execute(query_update, (url_foto, id_prod))
                    conn.commit()
                    
                    st.success(f"✅ **{nombre_archivo_completo}** -> Asociado correctamente a **{nombre_real_prod}**")
                    exitos += 1
                else:
                    st.error(f"❌ **{nombre_archivo_completo}** -> Error al subir la imagen a ImgBB.")
                    errores += 1
            else:
                st.warning(f"⚠️ **{nombre_archivo_completo}** -> No se encontró ningún producto llamado '{nombre_sin_extension}' en Neon.")
                errores += 1
                
            # Actualizar la barra de progreso
            barra_progreso.progress((index + 1) / total_archivos)
            
        st.write("---")
        st.info(f"📊 **Resumen del proceso:** {exitos} exitosas, {errores} omitidas/con error.")
        if exitos > 0:
            st.balloons()

    except Exception as error:
        st.error(f"❌ Error crítico en la Base de Datos: {error}")
    finally:
        if conn:
            conn.close()

# --- COMPONENTE VISUAL ---

# accept_multiple_files=True permite arrastrar todas tus fotos juntas
lote_fotos = st.file_uploader(
    "Selecciona o arrastra TODAS las imágenes de tus productos simultáneamente:", 
    type=["jpg", "jpeg", "png", "webp"], 
    accept_multiple_files=True
)

if lote_fotos:
    st.write(f"📂 Has cargado **{len(lote_fotos)}** archivos listos para procesar.")
    
    if st.button("🚀 Iniciar carga masiva y vinculación"):
        with st.spinner("Procesando lote... Esto puede tomar un momento dependiendo de la cantidad de fotos."):
            procesar_lote_imagenes(lote_fotos)
else:
    st.info("💡 Consejo: Asegúrate de que el nombre de tus archivos `.jpg` coincida exactamente con el nombre del producto guardado en Neon.")
