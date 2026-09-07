import streamlit as st
import requests
import base64
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT ---
st.title("📸 Asociador de Imágenes a Productos (Neon + ImgBB)")
st.write("Ingresa el ID del producto y sube su imagen para guardarla automáticamente en tu álbum privado y actualizar Neon.")

# Cargar secretos de forma segura desde Streamlit Cloud
try:
    url_limpia = st.secrets["neon"]["url"]
    IMGBB_API_KEY = st.secrets["imgbb"]["api_key"]
    IMGBB_ALBUM_ID = st.secrets["imgbb"]["album_id"]
except KeyError as e:
    st.error(f"❌ Error: Falta configurar la variable {e} en los Secrets de Streamlit.")
    st.stop()

def subir_imagen_a_album(imagen_bytes, nombre_producto):
    """Sube la imagen en memoria a ImgBB dentro del álbum especificado."""
    # Dirección oficial corregida para la API de ImgBB
    url_api = "https://imgbb.com"
    
    try:
        # Convertir los bytes de la imagen subida a formato Base64 de texto (.decode)
        imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
        
        datos = {
            "key": IMGBB_API_KEY,
            "image": imagen_base64,
            "album_id": IMGBB_ALBUM_ID,
            "name": f"prod_{nombre_producto.replace(' ', '_').lower()}"
        }
        
        respuesta = requests.post(url_api, data=datos)
        resultado = respuesta.json()
        
        if resultado.get("status") == 200:
            return resultado["data"]["url"]  # Devuelve el enlace directo (.jpg / .png)
        else:
            st.error(f"❌ Error ImgBB: {resultado.get('error', {}).get('message')}")
            return None
    except Exception as e:
        st.error(f"❌ Error al procesar la subida: {e}")
        return None

def asociar_imagen_a_producto_existente(id_producto, imagen_bytes):
    """Busca el producto en Neon, sube la foto y actualiza la base de datos."""
    conn = None
    try:
        # Conectarse a Neon
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Verificar si el producto existe
        cur.execute("SELECT nombre FROM public.productos WHERE id_producto = %s;", (id_producto,))
        producto = cur.fetchone()
        
        if not producto:
            st.error(f"❌ El producto con ID {id_producto} no existe en la base de datos.")
            return False
        
        nombre_prod = producto['nombre']
        st.write(f"📦 Producto encontrado: **{nombre_prod}**")
        
        # 2. Subir la imagen usando la función de arriba
        st.write("⏳ Subiendo imagen al álbum privado de ImgBB...")
        url_publica_imagen = subir_imagen_a_album(imagen_bytes, nombre_prod)
        
        if not url_publica_imagen:
            return False
        
        # 3. Guardar el link en la tabla de productos de Neon
        st.write("📤 Guardando enlace en la base de datos...")
        query_update = """
            UPDATE public.productos 
            SET url_imagen = %s 
            WHERE id_producto = %s;
        """
        cur.execute(query_update, (url_publica_imagen, id_producto))
        conn.commit()
        
        st.success(f"¡Éxito! Imagen asociada a '{nombre_prod}' correctamente. 🎉")
        st.info(f"🔗 Enlace guardado: {url_publica_imagen}")
        st.balloons()
        return True

    except Exception as error:
        st.error(f"❌ Error de Base de Datos: {error}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            cur.close()
            conn.close()

# --- FORMULARIO VISUAL EN LA PANTALLA ---

# 1. Entrada para colocar el ID del producto (convertido a número entero Bigint)
id_entrada = st.number_input("1. Escribe el ID del Producto:", min_value=1, step=1, format="%d")

# 2. Componente de arrastrar y soltar para la imagen
archivo_imagen = st.file_uploader("2. Selecciona o arrastra la imagen del producto", type=["jpg", "jpeg", "png", "webp"])

# El proceso solo corre cuando el usuario presiona activamente el botón
if archivo_imagen is not None:
    if st.button("🚀 Asociar foto y guardar en Neon"):
        # Al igual que en el CSV, el spinner previene que la app se cuelgue o se quede en negro
        with st.spinner("Conectando sistemas y procesando archivo..."):
            # Leemos los bytes del archivo cargado en memoria de la app
            bytes_de_la_foto = archivo_imagen.read()
            # Ejecutamos el flujo completo
            asociar_imagen_a_producto_existente(id_producto=id_entrada, imagen_bytes=bytes_de_la_foto)
else:
    st.info("💡 Por favor, sube una imagen arriba para activar el botón de guardado.")
