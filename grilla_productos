import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURACIÓN DE LA PANTALLA ---
st.set_page_config(page_title="Catálogo Visual", page_icon="🛍️", layout="wide")
st.title("🛍️ Catálogo de Productos Registrados")
st.write("Visualización en tiempo real de los productos que ya cuentan con una imagen asociada en Neon.")

# Cargar secretos de forma segura
try:
    url_limpia = st.secrets["neon"]["url"]
except KeyError:
    st.error("❌ Error: Falta configurar la variable ['neon']['url'] en los Secrets.")
    st.stop()

# --- FUNCIÓN PARA TRAER LOS PRODUCTOS CON IMAGEN ---
@st.cache_data(ttl=30)  # Guarda la grilla en caché por 30 segundos para máxima velocidad
def cargar_productos_con_foto():
    """Trae de Neon solo los productos que ya tienen un enlace de imagen asignado."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Filtramos para omitir los registros que tengan la url de imagen vacía o nula
        query = """
            SELECT id_producto, nombre, marca, tamano, unidad, url_imagen 
            FROM public.productos 
            WHERE url_imagen IS NOT NULL AND url_imagen != ''
            ORDER BY nombre ASC;
        """
        cur.execute(query)
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Error al consultar Neon: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- RENDERIZADO DE LA GRILLA ---
productos = cargar_productos_con_foto()

if not productos:
    st.info("💡 Aún no hay productos con imágenes asociadas. Usa el cargador masivo para vincular las primeras fotos.")
else:
    st.write(f"📊 Mostrando **{len(productos)}** productos encontrados en la base de datos.")
    st.write("---")

    # Definimos cuántas columnas queremos por fila en nuestra grilla (ej. 4 productos por fila)
    COLUMNAS_POR_FILA = 4
    
    # Creamos un bucle que agrupa los productos de 4 en 4
    for i in range(0, len(productos), COLUMNAS_POR_FILA):
        bloque_productos = productos[i:i + COLUMNAS_POR_FILA]
        
        # Generamos los contenedores visuales para esta fila
        columnas_ui = st.columns(COLUMNAS_POR_FILA)
        
        # Colocamos cada producto en su respectiva columna
        for index, prod in enumerate(bloque_productos):
            with columnas_ui[index]:
                # Tarjeta visual del producto (Card)
                with st.container(border=True):
                    # Mostramos la imagen guardada en ImgBB. Si el link falla, muestra un texto alternativo.
                    st.image(
                        prod['url_imagen'], 
                        use_container_width=True
                    )
                    
                    # Datos del producto de forma ordenada
                    st.subheader(prod['nombre'])
                    
                    # Detalles secundarios en letra más pequeña
                    marca = prod['marca'] if prod['marca'] else "Sin Marca"
                    tamano = f"{prod['tamano']} {prod['unidad']}" if prod['tamano'] else ""
                    
                    st.caption(f"🏷️ **Marca:** {marca}")
                    if tamano:
                        st.caption(f"⚖️ **Contenido:** {tamano}")
                    st.code(f"ID: {prod['id_producto']}", language="text")

