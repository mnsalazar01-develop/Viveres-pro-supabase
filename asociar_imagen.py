import streamlit as st
import requests
import base64
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT ---
st.set_page_config(page_title="Asociador Pro", page_icon="📸", layout="centered")
st.title("📸 Asociador de Imágenes Pro (Neon + ImgBB)")
st.write("Selecciona un producto de la lista y sube su imagen para asociarla automáticamente.")

# Cargar secretos de forma segura desde Streamlit Cloud
try:
    url_limpia = st.secrets["neon"]["url"]
    IMGBB_API_KEY = st.secrets["imgbb"]["api_key"]
    IMGBB_ALBUM_ID = st.secrets["imgbb"]["album_id"]
except KeyError as e:
    st.error(f"❌ Error: Falta configurar la variable {e} en los Secrets de Streamlit.")
    st.stop()

# --- FUNCION PARA TRAER LOS PRODUCTOS AL SELECTBOX ---
@st.cache_data(ttl=60)  # Guarda la lista en memoria por 1 minuto para que cargue instantáneo
def obtener_lista_productos():
    """Conecta a Neon y trae el ID y Nombre de todos los productos para el buscador."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Traemos el ID y Nombre ordenados alfabéticamente
        cur.execute("SELECT id_producto, nombre FROM public.productos WHERE nombre IS NOT NULL ORDER BY nombre ASC;")
        productos = cur.fetchall()
        return productos
    except Exception as e:
        st.error(f"❌ Error al cargar catálogo de productos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def subir_imagen_a_album(imagen_bytes, nombre_producto):
    """Sube la imagen en memoria a ImgBB dentro del álbum especificado."""
    url_api = "https://imgbb.com"  # Dirección oficial corregida
    
    try:
        # Convertir los bytes de la imagen subida a formato Base64 de texto
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

def guardar_url_en_neon(id_producto, url_publica_imagen):
    """Hace el UPDATE directamente en la fila del producto elegido."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor()
        
        query_update = """
            UPDATE public.productos 
            SET url_imagen = %s 
            WHERE id_producto = %s;
        """
        cur.execute(query_update, (url_publica_imagen, id_producto))
        conn.commit()
        return True
    except Exception as error:
        st.error(f"❌ Error al guardar en Base de Datos: {error}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

# --- CARGAR CATÁLOGO AL INICIAR ---
catalogo = obtener_lista_productos()

if not catalogo:
    st.warning("⚠️ No se encontraron productos en la tabla 'productos' o la base de datos está vacía.")
else:
    # --- FORMULARIO VISUAL EN LA PANTALLA ---

    # 1. Selectbox Pro: Muestra el nombre, pero guarda internamente todo el objeto
    producto_seleccionado = st.selectbox(
        "1. Selecciona el Producto:",
        options=catalogo,
        format_func=lambda prod: f"{prod['nombre']} (ID: {prod['id_producto']})"
    )

    # 2. Componente de arrastrar y soltar para la imagen
    archivo_imagen = st.file_uploader("2. Selecciona o arrastra la imagen del producto", type=["jpg", "jpeg", "png", "webp"])

    # El proceso solo corre cuando el usuario presiona activamente el botón
    if archivo_imagen is not None:
        if st.button("🚀 Asociar foto y guardar en Neon"):
            with st.spinner("Procesando subida y actualizando base de datos..."):
                
                # Extraemos las variables del producto seleccionado en el selectbox
                id_prod = producto_seleccionado['id_producto']
                nombre_prod = producto_seleccionado['nombre']
                
                # Leemos la foto
                bytes_de_la_foto = archivo_imagen.read()
                
                # Paso A: Subir a ImgBB
                url_foto = subir_imagen_a_album(bytes_de_la_foto, nombre_prod)
                
                # Paso B: Si la subida fue exitosa, guardar en Neon
                if url_foto:
                    exito = guardar_url_en_neon(id_prod, url_foto)
                    if exito:
                        st.success(f"¡Éxito! Imagen asociada a '{nombre_prod}' correctamente. 🎉")
                        st.info(f"🔗 Enlace guardado: {url_foto}")
                        st.balloons()
    else:
        st.info("💡 Por favor, sube una imagen arriba para activar el botón de guardado.")
