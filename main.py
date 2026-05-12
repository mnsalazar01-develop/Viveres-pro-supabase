import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date

# 1. CONEXIÓN (Usando tus Secrets)
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNCIONES DE APOYO ---
def subir_a_storage(archivo):
    if archivo:
        try:
            nombre_archivo = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name.replace(' ', '_')}"
            supabase.storage.from_("imagenes").upload(
                path=nombre_archivo, 
                file=archivo.getvalue(), 
                file_options={"content-type": archivo.type}
            )
            return supabase.storage.from_("imagenes").get_public_url(nombre_archivo)
        except:
            return None
    return None

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Mi Ahorro Viveres", layout="wide", page_icon="🛒")

# 2. MENÚ LATERAL
st.sidebar.title("Menú Principal")
menu = ["🔍 Alertas y Ofertas", "📦 Catálogo de Productos", "🏪 Tiendas y Sucursales", "🏷️ Registrar Ofertas"]
choice = st.sidebar.selectbox("Ir a:", menu)

# --- SECCIÓN 1: ALERTAS Y OFERTAS (EL CORAZÓN DE LA APP) ---
if choice == "🔍 Alertas y Ofertas":
    st.title("🔔 Mis Alertas de Ahorro")
    
    # Punto 1: Solo lo que me interesa
    res_p = supabase.table("productos").select("nombre").execute()
    lista_productos = sorted(list(set([p['nombre'] for p in res_p.data])))
    
    productos_interes = st.multiselect(
        "⭐ Selecciona los productos que necesitas comprar hoy:", 
        lista_productos, 
        help="Si eliges 'Leche', solo verás ofertas de leche."
    )

    # Consulta de ofertas con relaciones
    res = supabase.table("ofertas").select("""
        precio_oferta, fecha_fin,
        productos(nombre, marca, url_imagen, tamano, unidad),
        supermercados(nombre_supermercado),
        sucursales(nombre_sucursal, ciudad)
    """).execute()

    if res.data:
        df = pd.json_normalize(res.data)
        
        # Filtrar por interés
        if productos_interes:
            df = df[df['productos.nombre'].isin(productos_interes)]

        if not df.empty:
            for _, o in df.iterrows():
                # Punto 2: Alarma de vencimiento
                fecha_vence = datetime.strptime(o['fecha_fin'], '%Y-%m-%d').date()
                dias_faltantes = (fecha_vence - date.today()).days
                
                with st.container(border=True):
                    c1, c2, c3 = st.columns([1, 2, 1])
                    with c1:
                        st.image(o['productos.url_imagen'] or "https://placeholder.com", use_container_width=True)
                    with c2:
                        st.subheader(f"{o['productos.nombre']} - {o['productos.marca']}")
                        st.write(f"🏢 {o['supermercados.nombre_supermercado']} ({o['sucursales.nombre_sucursal'] or 'Todas las sucursales'})")
                        
                        if 0 <= dias_faltantes <= 2:
                            st.error(f"🚨 ¡COMPRAR PRONTO! Vence en {dias_faltantes} días ({fecha_vence.strftime('%d/%m/%Y')})")
                        elif dias_faltantes < 0:
                            st.write("❌ Oferta vencida")
                        else:
                            st.info(f"⏳ Tienes tiempo: vence el {fecha_vence.strftime('%d/%m/%Y')}")
                    with c3:
                        st.metric("PRECIO", f"${o['precio_oferta']}")
        else:
            st.info("No hay ofertas para los productos seleccionados.")
    else:
        st.info("No hay ofertas registradas en el sistema.")

# --- SECCIÓN 2: CATÁLOGO DE PRODUCTOS (ADMINISTRACIÓN) ---
elif choice == "📦 Catálogo de Productos":
    st.title("📦 Administración de Productos")
    t1, t2 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto"])
    
    with t1:
        res_p = supabase.table("productos").select("*").execute()
        if res_p.data:
            st.dataframe(pd.DataFrame(res_p.data), column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
            
    with t2:
        with st.form("nuevo_p", clear_on_submit=True):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre del Producto*")
            marca = col2.text_input("Marca")
            barras = col1.text_input("Código de Barras")
            tam = col2.number_input("Tamaño", min_value=0.0)
            uni = col1.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"])
            foto = col2.file_uploader("Foto", type=['jpg', 'png', 'jpeg', 'webp'])
            
            if st.form_submit_button("Guardar Producto"):
                url_img = subir_a_storage(foto)
                supabase.table("productos").insert({
                    "nombre": nombre, "marca": marca, "codigo_barras": barras, 
                    "tamano": tam, "unidad": uni, "url_imagen": url_img
                }).execute()
                st.success("Producto guardado.")
                st.rerun()

# --- SECCIÓN 3: TIENDAS ---
elif choice == "🏪 Tiendas y Sucursales":
    st.title("🏪 Registro de Tiendas")
    with st.form("super"):
        nom = st.text_input("Nombre del Supermercado")
        if st.form_submit_button("Guardar Super"):
            supabase.table("supermercados").insert({"nombre_supermercado": nom}).execute()
            st.success("Supermercado guardado.")
    
    st.divider()
    
    supers = supabase.table("supermercados").select("*").execute()
    if supers.data:
        df_s = pd.DataFrame(supers.data)
        super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        with st.form("suc"):
            s_sel = st.selectbox("Selecciona Supermercado", list(super_dict.keys()))
            n_suc = st.text_input("Nombre Sucursal")
            ciu = st.text_input("Ciudad")
            if st.form_submit_button("Guardar Sucursal"):
                supabase.table("sucursales").insert({"id_super": super_dict[s_sel], "nombre_sucursal": n_suc, "ciudad": ciu}).execute()
                st.success("Sucursal guardada.")

# --- SECCIÓN 4: REGISTRAR OFERTAS (CARGA POR SUPERMERCADO) ---
elif choice == "🏷️ Registrar Ofertas":
    st.title("🏷️ Cargar Ofertas por Catálogo")
    
    supers = supabase.table("supermercados").select("*").execute()
    if supers.data:
        df_s = pd.DataFrame(supers.data)
        super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        
        # Punto 3: Seleccionas el Super primero, como te llega el volante
        super_sel = st.selectbox("¿De qué Supermercado es el volante/oferta?", list(super_dict.keys()))
        
        # Sucursales de ese Super
        sucs = supabase.table("sucursales").select("*").eq("id_super", super_dict[super_sel]).execute()
        suc_dict = {"--- TODAS LAS SUCURSALES ---": None}
        for s in sucs.data: suc_dict[s['nombre_sucursal']] = s['id_sucursal']
        
        suc_sel = st.selectbox("¿Aplica a una sucursal específica?", list(suc_dict.keys()))
        
        st.divider()
        
        # Formulario de carga
        prods = supabase.table("productos").select("id_producto, nombre, marca").execute()
        p_df = pd.DataFrame(prods.data)
        p_dict = dict(zip(p_df['nombre'] + " (" + p_df['marca'] + ")", p_df['id_producto']))
        
        with st.form("form_of"):
            p_sel = st.selectbox("Producto en oferta", list(p_dict.keys()))
            precio = st.number_input("Precio Oferta", min_value=0.0, format="%.2f")
            vence = st.date_input("¿Cuándo termina la oferta?", format="DD/MM/YYYY")
            
            if st.form_submit_button("Publicar Oferta"):
                supabase.table("ofertas").insert({
                    "id_producto": p_dict[p_sel],
                    "id_super": super_dict[super_sel],
                    "id_sucursal": suc_dict[suc_sel],
                    "precio_oferta": precio,
                    "fecha_fin": str(vence)
                }).execute()
                st.success("Oferta publicada con éxito.")
    else:
        st.warning("Primero debes registrar un Supermercado.")
