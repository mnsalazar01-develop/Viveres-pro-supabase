import streamlit as st
import requests
import base64
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT ---
st.set_page_config(page_title="Asociador Pro", page_icon="📸", layout="centered")
st.title("📸 Administrador de Imágenes de Productos (Neon + ImgBB)")
st.write("Selecciona un producto y elige el método para asignarle su imagen.")

# Cargar secretos de forma segura desde Streamlit Cloud
try:
    url_limpia = st.secrets["neon"]["url"]
    IMGBB_API_KEY = st.secrets["imgbb"]["api_key"]
    IMGBB_ALBUM_ID = st.secrets["imgbb"]["album_id"]
except KeyError as e:
    st.error(f"❌ Error: Falta configurar la variable {e} en los Secrets de Streamlit.")
    st.stop()

# --- FUNCIÓN PARA TRAER LOS PRODUCTOS AL SELECTBOX ---
@st.cache_data(ttl=60)
def obtener_lista_productos():
    """Conecta a Neon y trae el ID y Nombre de todos los productos para el buscador."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id_producto, nombre, marca, tamano, unidad FROM public.productos WHERE nombre IS NOT NULL ORDER BY nombre ASC;")
        productos = cur.fetchall()
        return productos
    except Exception as e:
        st.error(f"❌ Error al cargar catálogo de productos: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- FUNCIÓN PARA SUBIR A IMGBB ---
def subir_imagen_a_album(imagen_bytes, nombre_producto):
    """Sube la imagen en memoria a ImgBB dentro del álbum especificado."""
    url_api = "https://api.imgbb.com/1/upload"  # URL correcta de la API
    
    try:
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
            return resultado["data"]["url"]
        else:
            st.error(f"❌ Error ImgBB: {resultado.get('error', {}).get('message')}")
            return None
    except Exception as e:
        st.error(f"❌ Error al procesar la subida: {e}")
        return None

# --- FUNCIÓN PARA GUARDAR EN NEON ---
def guardar_url_en_neon(id_producto, url_foto):
    """
    Actualiza de forma persistente el campo url_imagen aceptando 
    IDs de productos que contengan espacios en blanco (Tipo Texto/VARCHAR).
    """
    # 1. Aseguramos que el ID se maneje estrictamente como TEXTO, respetando sus espacios
    id_parametro = str(id_producto)

    # Validamos que no esté completamente vacío
    if not id_parametro.strip():
        st.error("❌ El ID de producto proporcionado está vacío.")
        return False

    query_update = """
        UPDATE public.productos 
        SET url_imagen = %s 
        WHERE id_producto = %s;
    """
    
    conn = None
    try:
        # Conexión directa a Neon
        conn = psycopg2.connect(st.secrets["neon"]["url"])
        cur = conn.cursor()
        
        # Ejecutamos pasando el ID como string con sus espacios exactos
        cur.execute(query_update, (str(url_foto).strip(), id_parametro))
        
        # Verificar cuántas filas coincidieron con ese ID exacto
        filas_afectadas = cur.rowcount
        
        if filas_afectadas == 0:
            st.warning(f"⚠️ No se encontró ningún producto con el ID exacto: '{id_parametro}' (Verifica si faltan o sobran espacios).")
            conn.rollback()
            return False
            
        # Confirmamos la transacción en Neon
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Fallo crítico al escribir en la tabla productos de Neon: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


# --- FLUJO PRINCIPAL DEL PROGRAMA ---
catalogo = obtener_lista_productos()

if not catalogo:
    st.warning("⚠️ No se encontraron productos en la tabla 'productos' o la base de datos está vacía.")
else:
    # 1. Buscador de productos común para ambas opciones
    producto_seleccionado = st.selectbox(
        "1. Selecciona el Producto:",
        options=catalogo,
        format_func=lambda prod: f"{prod['nombre']} {prod['marca']} {prod['tamano']} {prod['unidad']}"
    )
    
    id_prod = producto_seleccionado['id_producto']
    nombre_prod = producto_seleccionado['nombre']

    st.write("---")

    # 2. Selector de modalidad
    opcion_metodo = st.radio(
        "2. Selecciona el método para la imagen:",
        options=["Subir imagen desde la computadora", "Asociar a imagen existente en el álbum"]
    )

    st.write("---")

    # === MODALIDAD 1: SUBIR DESDE DISCO ===
    if opcion_metodo == "Subir imagen desde la computadora":
        archivo_imagen = st.file_uploader("Selecciona o arrastra la imagen del producto", type=["jpg", "jpeg", "png", "webp"])
        
        # Guardar el archivo en el estado para evitar pérdidas al hacer clic en botones
        if archivo_imagen is not None:
            # Almacenamos los bytes en memoria persistentemente
            st.session_state["bytes_archivo_subido"] = archivo_imagen.getvalue()
            st.session_state["nombre_archivo_subido"] = archivo_imagen.name
        else:
            if "bytes_archivo_subido" in st.session_state:
                del st.session_state["bytes_archivo_subido"]
                del st.session_state["nombre_archivo_subido"]

        # Si existen bytes en el estado, habilitamos la interacción de guardado
        if "bytes_archivo_subido" in st.session_state:
            st.success(f"📸 Archivo cargado en memoria listo para procesar: {st.session_state['nombre_archivo_subido']}")
            
            if st.button("🚀 Subir e Inyectar en Neon", type="primary", use_container_width=True):
                with st.spinner("Procesando subida a ImgBB y guardando en Neon..."):
                    # Extraemos los bytes seguros desde la memoria persistente
                    bytes_de_la_foto = st.session_state["bytes_archivo_subido"]
                    
                    # Ejecuta la subida a internet primero
                    url_foto = subir_imagen_a_album(bytes_de_la_foto, nombre_prod)
                    
                    # Si funcionó, guarda en la base de datos
                    if url_foto:
                        if guardar_url_en_neon(id_prod, url_foto):
                            st.success(f"¡Éxito! Foto subida y asociada a '{nombre_prod}' correctamente. 🎉")
                            st.info(f"🔗 Enlace guardado: {url_foto}")
                            st.balloons()
                            
                            # Limpieza opcional del estado para evitar dobles envíos accidentales
                            del st.session_state["bytes_archivo_subido"]
                            st.rerun()
                    else:
                        st.error("❌ No se pudo obtener la URL de ImgBB. Revisa las credenciales de la API.")
        else:
            st.info("💡 Sube una imagen desde tu PC para habilitar el botón de guardado.")


    # === MODALIDAD 2: ENLACE DEL ÁLBUM ===
    elif opcion_metodo == "Asociar a imagen existente en el álbum":
        url_existente = st.text_input("Pega la URL directa de la imagen que ya está en tu álbum:", placeholder="https://ibb.co...")
        
        if url_existente:
            # Vista previa opcional si el usuario pega un enlace directo válido
            if url_existente.startswith("http"):
                st.image(url_existente, caption="Vista previa de la imagen detectada", width=200)

            if st.button("🔗 Asociar Enlace Directamente"):
                with st.spinner("Actualizando registro en Neon..."):
                    url_limpia_foto = url_existente.strip()
                    
                    # Guarda el texto directo en Neon saltándose a ImgBB
                    if guardar_url_en_neon(id_prod, url_limpia_foto):
                        st.success(f"¡Asociación exitosa! La URL ya está vinculada a '{nombre_prod}'. 🎉")
                        st.balloons()
        else:
            st.info("💡 Pega un enlace válido de ImgBB para habilitar el botón de asociación.")
