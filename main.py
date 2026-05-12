import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# 1. CONFIGURACIÓN E INICIALIZACIÓN
st.set_page_config(page_title="Viveres Pro v2.0", layout="wide", page_icon="🛒")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- FUNCIONES DE SOPORTE ---
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
        except Exception as e:
            st.error(f"Error al subir imagen: {e}")
    return None

# 2. MENÚ PRINCIPAL
menu = ["🔍 Dashboard de Ofertas", "📦 Administración de Productos", "🏪 Tiendas y Sucursales", "🏷️ Publicar Oferta"]
choice = st.sidebar.selectbox("Menú de Navegación", menu)

# --- SECCIÓN 1: DASHBOARD DE OFERTAS ---
if choice == "🔍 Dashboard de Ofertas":
    st.title("🚀 Ofertas Activas")
    res = supabase.table("ofertas").select("""
        precio_oferta, fecha_fin,
        productos(nombre, marca, url_imagen, tamano, unidad),
        supermercados(nombre_supermercado, url_logo),
        sucursales(nombre_sucursal, ciudad)
    """).execute()

    if res.data:
        df_o = pd.json_normalize(res.data)
        ciudades = ["Todas"] + sorted(list(df_o['sucursales.ciudad'].dropna().unique()))
        ciudad_sel = st.sidebar.selectbox("📍 Filtrar por Ciudad", ciudades)
        
        if ciudad_sel != "Todas":
            df_o = df_o[df_o['sucursales.ciudad'] == ciudad_sel]

        for _, o in df_o.iterrows():
            fecha_f = datetime.strptime(o['fecha_fin'], '%Y-%m-%d').strftime('%d/%m/%Y')
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.image(o['productos.url_imagen'] or "https://placeholder.com", use_container_width=True)
                with c2:
                    st.subheader(f"{o['productos.nombre']} ({o['productos.marca']})")
                    st.write(f"📏 {o['productos.tamano']} {o['productos.unidad']}")
                    suc = o['sucursales.nombre_sucursal'] if pd.notna(o['sucursales.nombre_sucursal']) else "Todas las Sucursales"
                    st.write(f"🏢 **{o['supermercados.nombre_supermercado']}** - 📍 {suc}")
                with c3:
                    st.metric("OFERTA", f"${o['precio_oferta']}")
                    st.warning(f"⌛ Vence: {fecha_f}")
    else:
        st.info("No hay ofertas activas.")

# --- SECCIÓN 2: ADMINISTRACIÓN DE PRODUCTOS (CRUD) ---
elif choice == "📦 Administración de Productos":
    st.title("🛠️ Gestión del Catálogo")
    t1, t2, t3 = st.tabs(["📋 Ver Inventario", "➕ Crear Nuevo", "✏️ Editar/Borrar"])

    with t1:
        busq = st.text_input("Buscar por nombre o código de barras")
        res_p = supabase.table("productos").select("*").execute()
        if res_p.data:
            df_p = pd.DataFrame(res_p.data)
            if busq:
                df_p = df_p[df_p.astype(str).apply(lambda x: x.str.contains(busq, case=False)).any(axis=1)]
            st.dataframe(df_p, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)

    with t2:
        with st.form("nuevo_p", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre*")
            marca = c2.text_input("Marca")
            barras = c1.text_input("Código de Barras")
            tam = c2.number_input("Tamaño", min_value=0.0)
            uni = c1.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"])
            foto = c2.file_uploader("Imagen (JPG, PNG, WEBP)", type=['jpg', 'png', 'jpeg', 'webp'])
            if st.form_submit_button("Guardar Producto"):
                url_img = subir_a_storage(foto)
                supabase.table("productos").insert({"nombre": nombre, "marca": marca, "codigo_barras": barras, "tamano": tam, "unidad": uni, "url_imagen": url_img}).execute()
                st.success("¡Producto registrado!"); st.rerun()

    with t3:
        res_p = supabase.table("productos").select("*").execute()
        if res_p.data:
            prod_dict = {f"{p['nombre']} - {p['marca']}": p for p in res_p.data}
            sel = st.selectbox("Selecciona producto", prod_dict.keys())
            p = prod_dict[sel]
            with st.form("edit_p"):
                en = st.text_input("Nombre", p['nombre'])
                eb = st.text_input("Código de Barras", p['codigo_barras'])
                c_del, c_upd = st.columns(2)
                if c_upd.form_submit_button("💾 Actualizar"):
                    supabase.table("productos").update({"nombre": en, "codigo_barras": eb}).eq("id_producto", p['id_producto']).execute()
                    st.success("Actualizado"); st.rerun()
                if c_del.form_submit_button("🗑️ Eliminar"):
                    supabase.table("productos").delete().eq("id_producto", p['id_producto']).execute()
                    st.warning("Eliminado"); st.rerun()

# --- SECCIÓN 3: TIENDAS Y SUCURSALES ---
elif choice == "🏪 Tiendas y Sucursales":
    st.title("🏪 Gestión de Establecimientos")
    with st.form("nueva_tienda"):
        nom_super = st.text_input("Nombre del Supermercado")
        if st.form_submit_button("Añadir Supermercado"):
            supabase.table("supermercados").insert({"nombre_supermercado": nom_super}).execute()
            st.success("Supermercado añadido"); st.rerun()
    
    st.divider()
    
    supers = supabase.table("supermercados").select("*").execute()
    if supers.data:
        df_s = pd.DataFrame(supers.data)
        dict_s = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        with st.form("nueva_suc"):
            sup_sel = st.selectbox("Pertenece a:", list(dict_s.keys()))
            nom_suc = st.text_input("Nombre Sucursal (Ej: Centro)")
            ciu = st.text_input("Ciudad")
            if st.form_submit_button("Añadir Sucursal"):
                supabase.table("sucursales").insert({"id_super": dict_s[sup_sel], "nombre_sucursal": nom_suc, "ciudad": ciu}).execute()
                st.success("Sucursal añadida"); st.rerun()

# --- SECCIÓN 4: PUBLICAR OFERTA ---
elif choice == "🏷️ Publicar Oferta":
    st.title("🏷️ Nueva Oferta")
    prods = supabase.table("productos").select("id_producto, nombre, marca").execute()
    supers = supabase.table("supermercados").select("id_super, nombre_supermercado").execute()
    
    if prods.data and supers.data:
        with st.form("form_of"):
            p_df = pd.DataFrame(prods.data)
            p_dict = dict(zip(p_df['nombre'] + " " + p_df['marca'], p_df['id_producto']))
            p_sel = st.selectbox("Producto", p_dict.keys())
            
            s_df = pd.DataFrame(supers.data)
            s_dict = dict(zip(s_df['nombre_supermercado'], s_df['id_super']))
            s_sel = st.selectbox("Supermercado", s_dict.keys())
            
            # Sucursales dinámicas
            sucs = supabase.table("sucursales").select("*").eq("id_super", s_dict[s_sel]).execute()
            suc_dict = {"--- TODAS ---": None}
            for sc in sucs.data: suc_dict[sc['nombre_sucursal']] = sc['id_sucursal']
            suc_sel = st.selectbox("Sucursal (Opcional)", suc_dict.keys())
            
            precio = st.number_input("Precio Oferta", min_value=0.0, format="%.2f")
            fecha = st.date_input("Vencimiento", format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Publicar"):
                supabase.table("ofertas").insert({
                    "id_producto": p_dict[p_sel], "id_super": s_dict[s_sel], 
                    "id_sucursal": suc_dict[suc_sel], "precio_oferta": precio, "fecha_fin": str(fecha)
                }).execute()
                st.success("¡Oferta publicada!"); st.balloons()
