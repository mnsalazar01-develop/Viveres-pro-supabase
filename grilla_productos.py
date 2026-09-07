import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURACIÓN DE LA PANTALLA ---
st.set_page_config(page_title="Catálogo Filtrado Pro", page_icon="🛍️", layout="wide")
st.title("🛍️ Catálogo Visual con Filtros Avanzados")
st.write("Explora los productos registrados cruzando sus categorías y subcategorías en tiempo real.")

# Cargar secretos de forma segura
try:
    url_limpia = st.secrets["neon"]["url"]
except KeyError:
    st.error("❌ Error: Falta configurar la variable ['neon']['url'] en los Secrets.")
    st.stop()

# --- 1. FUNCIÓN PARA CARGAR TODAS LAS CATEGORÍAS ---
@st.cache_data(ttl=60)
def obtener_categorias():
    """Trae la lista de todas las categorías disponibles para el primer filtro."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id_cat, nombre FROM public.categorias ORDER BY nombre ASC;")
        return cur.fetchall()
    except Exception as e:
        st.error(f"Error al cargar categorías: {e}")
        return []
    finally:
        if conn: conn.close()

# --- 2. FUNCIÓN PARA CARGAR SUBCATEGORÍAS FILTRADAS POR CATEGORÍA ---
@st.cache_data(ttl=60)
def obtener_subcategorias(id_categoria):
    """Trae solo las subcategorías que pertenecen a la categoría seleccionada."""
    if not id_categoria:
        return []
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id_subcat, nombre FROM public.subcategorias WHERE id_cat = %s ORDER BY nombre ASC;",
            (id_categoria,)
        )
        return cur.fetchall()
    except Exception as e:
        st.error(f"Error al cargar subcategorías: {e}")
        return []
    finally:
        if conn: conn.close()

# --- 3. FUNCIÓN PRINCIPAL: CARGAR PRODUCTOS CON FILTROS ---
def cargar_productos_grilla(id_cat_filtro=None, id_subcat_filtro=None):
    """Trae los productos haciendo un JOIN con categorías y subcategorías aplicando los filtros elegidos."""
    conn = None
    try:
        conn = psycopg2.connect(url_limpia)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Consulta base: Traemos datos del producto y los nombres de sus categorías mediante JOINs
        query = """
            SELECT 
                p.id_producto, p.nombre, p.marca, p.tamano, p.unidad, p.url_imagen,
                c.nombre AS nombre_categoria,
                s.nombre AS nombre_subcategoria
            FROM public.productos p
            LEFT JOIN public.categorias c ON p.id_cat = c.id_cat
            LEFT JOIN public.subcategorias s ON p.id_subcat = s.id_subcat
            WHERE p.url_imagen IS NOT NULL AND p.url_imagen != ''
        """
        
        parametros = []
        
        # Aplicamos filtros dinámicos en SQL según lo que elija el usuario en la interfaz
        if id_cat_filtro:
            query += " AND p.id_cat = %s"
            parametros.append(id_cat_filtro)
            
        if id_subcat_filtro:
            query += " AND p.id_subcat = %s"
            parametros.append(id_subcat_filtro)
            
        query += " ORDER BY p.nombre ASC;"
        
        cur.execute(query, tuple(parametros))
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Error al consultar el catálogo: {e}")
        return []
    finally:
        if conn: conn.close()

# --- ESTRUCTURA DE FILTROS EN LA PARTE SUPERIOR (UI) ---
st.write("### 🔍 Filtros de Búsqueda")
col_cat, col_subcat = st.columns(2)

# Cargar el listado inicial de categorías de tu BD
lista_categorias = obtener_categorias()

with col_cat:
    # Creamos una opción por defecto para mostrar todo
    opciones_cat = [{"id_cat": None, "nombre": "Todas las Categorías"}] + lista_categorias
    categoria_seleccionada = st.selectbox(
        "Filtrar por Categoría:",
        options=opciones_cat,
        format_func=lambda c: c["nombre"]
    )
    id_cat_actual = categoria_seleccionada["id_cat"]

with col_subcat:
    # Si hay una categoría seleccionada, buscamos sus subcategorías específicas en Neon
    if id_cat_actual:
        lista_subcats = obtener_subcategorias(id_cat_actual)
        opciones_sub = [{"id_subcat": None, "nombre": "Todas las Subcategorías"}] + lista_subcats
    else:
        # Si eligió "Todas", el selector de subcategorías se inhabilita para evitar confusiones
        opciones_sub = [{"id_subcat": None, "nombre": "Selecciona una categoría primero"}]
    
    subcategoria_seleccionada = st.selectbox(
        "Filtrar por Subcategoría:",
        options=opciones_sub,
        format_func=lambda s: s["nombre"],
        disabled=(id_cat_actual is None)
    )
    id_subcat_actual = subcategoria_seleccionada["id_subcat"]

st.write("---")

# --- CONTROL Y RENDERIZADO DE LA GRILLA ---
productos = cargar_productos_grilla(id_cat_actual, id_subcat_actual)

if not productos:
    st.info("💡 No se encontraron productos con imagen para los filtros seleccionados.")
else:
    st.write(f"📊 Mostrando **{len(productos)}** productos en esta sección.")
    
    COLUMNAS_POR_FILA = 4
    
    for i in range(0, len(productos), COLUMNAS_POR_FILA):
        bloque_productos = productos[i:i + COLUMNAS_POR_FILA]
        columnas_ui = st.columns(COLUMNAS_POR_FILA)
        
        for index, prod in enumerate(bloque_productos):
            with columnas_ui[index]:
                with st.container(border=True):
                    # Imagen del producto
                    st.image(prod['url_imagen'], use_container_width=True)
                    
                    # Título del producto
                    st.subheader(prod['nombre'])
                    
                    # Detalles del producto extraídos de Neon
                    marca = prod['marca'] if prod['marca'] else "Sin Marca"
                    tamano = f"{prod['tamano']} {prod['unidad']}" if prod['tamano'] else ""
                    cat_txt = prod['nombre_categoria'] if prod['nombre_categoria'] else "No asignada"
                    sub_txt = prod['nombre_subcategoria'] if prod['nombre_subcategoria'] else "No asignada"
                    
                    st.caption(f"🏷️ **Marca:** {marca}")
                    if tamano:
                        st.caption(f"⚖️ **Contenido:** {tamano}")
                    
                    # Etiquetas sutiles de su ubicación en el árbol de categorías
                    st.caption(f"📂 **{cat_txt}** > *{sub_txt}*")
                    
                    st.code(f"ID: {prod['id_producto']}", language="text")
