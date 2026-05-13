import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date

# 1. CONFIGURACIÓN DE PÁGINA E INICIALIZACIÓN
st.set_page_config(page_title="Control Víveres Pro", layout="wide", page_icon="🛒")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()
URL_FOTO_DEFECTO = "flaticon.com"

# --- FUNCIONES DE SOPORTE ---
def subir_a_storage(archivo):
    if archivo:
        try:
            nom_arc = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name.replace(' ', '_')}"
            supabase.storage.from_("imagenes").upload(path=nom_arc, file=archivo.getvalue(), file_options={"content-type": archivo.type})
            return supabase.storage.from_("imagenes").get_public_url(nom_arc)
        except: return None
    return None

def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras:
        q = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir: q = q.neq("id_producto", id_excluir)
        res = q.execute()
        if res.data: return "barras", res.data

    q_t = supabase.table("productos").select("*")
    if id_excluir: q_t = q_t.neq("id_producto", id_excluir)
    res_t = q_t.execute()
    if res_t.data:
        n_n = "".join(nombre.lower().split())
        m_n = "".join(marca.lower().split()) if marca else ""
        t_n = float(tamano)
        u_n = unidad.lower()
        for p in res_t.data:
            if n_n == "".join(p['nombre'].lower().split()) and m_n == "".join((p['marca'] or "").lower().split()) and t_n == float(p['tamano'] or 0) and u_n == (p['unidad'] or "").lower():
                return "atributos", p
    return None, None

# 2. MENÚ LATERAL DE NAVEGACIÓN
st.sidebar.title("Menú Principal")
menu = ["🔍 Alertas y Ofertas", "📊 Reportes de Mercado", "📦 Gestión de Productos", "📁 Estructura (Cat/Subcat)", "🏪 Tiendas y Sucursales", "🏷️ Registrar Ofertas"]
choice = st.sidebar.selectbox("Ir a:", menu)

# --- CONSULTAS DE DATOS GLOBALES MAESTROS ---
try:
    res_cat = supabase.table("categorias").select("*").order("id_cat").execute()
    c_dict = {c['nombre']: c['id_cat'] for c in res_cat.data} if res_cat.data else {}
    c_inv = {c['id_cat']: c['nombre'] for c in res_cat.data} if res_cat.data else {}
    lista_cat = [c['nombre'] for c in res_cat.data] if res_cat.data else []

    res_sub = supabase.table("subcategorias").select("*").order("nombre").execute()
    sc_dict = {f"{s['nombre']} (Cat {s['id_cat']})": s['id_subcat'] for s in res_sub.data} if res_sub.data else {}
    sc_inv = {s['id_subcat']: s['nombre'] for s in res_sub.data} if res_sub.data else {}
except:
    c_dict, c_inv, lista_cat, sc_dict, sc_inv = {}, {}, [], {}, {}

# --- SECCIÓN 1: ALERTAS Y OFERTAS (CORREGIDA CON TIENDAS VISIBLES) ---
if choice == "🔍 Alertas y Ofertas":
    st.title("🔔 Mis Alertas y Ofertas")
    try:
        res_p = supabase.table("productos").select("nombre").execute()
        lista_productos = sorted(list(set([p['nombre'] for p in res_p.data]))) if res_p.data else []
    except: lista_productos = []
    
    productos_interes = st.multiselect("⭐ Filtrar por lo que necesitas comprar hoy:", lista_productos)

    try:
        # Traemos explícitamente los campos de texto de supermercado y sucursal
        res = supabase.table("ofertas").select("id_oferta, precio_oferta, fecha_fin, id_producto, productos(nombre, marca, url_imagen, tamano, unidad), supermercados(nombre_supermercado), sucursales(nombre_sucursal)").execute()
    except: res = None

    if res and res.data:
        df = pd.json_normalize(res.data)
        cols_criticas = {'productos.nombre': 'Desconocido', 'productos.marca': '', 'productos.url_imagen': '', 'productos.tamano': 0, 'productos.unidad': 'ud', 'supermercados.nombre_supermercado': 'Supermercado', 'sucursales.nombre_sucursal': 'Todas las sucursales'}
        for col, def_val in cols_criticas.items():
            df[col] = df[col].fillna(def_val) if col in df.columns else def_val

        if productos_interes:
            df = df[df['productos.nombre'].isin(productos_interes)]

        if not df.empty:
            df['fecha_dt'] = pd.to_datetime(df['fecha_fin'])
            for prod_id, grupo in df.groupby('id_producto'):
                grp = grupo.sort_values(by='precio_oferta')
                with st.container(border=True):
                    c_img, c_info = st.columns(2)
                    with c_img: st.image(grp['productos.url_imagen'].iloc[0] or URL_FOTO_DEFECTO, use_container_width=True)
                    with c_info:
                        st.subheader(f"{grp['productos.nombre'].iloc[0]} - {grp['productos.marca'].iloc[0]} ({grp['productos.tamano'].iloc[0]} {grp['productos.unidad'].iloc[0]})")
                        st.write("🛒 **Precios y Ubicaciones Disponibles:**")
                        cols_t = st.columns(len(grp))
                        for i, (_, f) in enumerate(grp.iterrows()):
                            dias = (f['fecha_dt'].date() - date.today()).days
                            es_b = (i == 0)
                            with cols_t[i]:
                                st.markdown(f'<div style="border: 2px solid {"#2bc443" if es_b else "#ccc"}; border-radius: 8px; padding: 10px; text-align: center; background-color: {"#f0fff4" if es_b else "#fff"}; margin-bottom:10px;"><b>{"🏆 MEJOR PRECIO" if es_b else "Oferta"}</b><h4 style="margin:5px 0;">{f["supermercados.nombre_supermercado"]}</h4><p style="font-size:0.8em; color:gray; margin:0;">{f["sucursales.nombre_sucursal"]}</p></div>', unsafe_allow_html=True)
                                st.metric(label="Precio", value=f"\${f['precio_oferta']:.2f}")
                                if 0 <= dias <= 2: st.error(f"🚨 Vence en {dias} día(s)")
                                elif dias < 0: st.warning("⚠️ Caducó")
                                else: st.caption(f"⏳ Vence: {f['fecha_dt'].date().strftime('%d/%m/%Y')}")
        else: st.warning("No hay ofertas para los productos seleccionados.")
    else: st.info("Aún no has registrado ninguna oferta.")

# --- SECCIÓN 2: REPORTES DE MERCADO (BUSCADOR AVANZADO SIN GRÁFICOS) ---
elif choice == "📊 Reportes de Mercado":
    st.title("📊 Buscador Estratégico de Ofertas")
    try:
        res = supabase.table("ofertas").select("precio_oferta, fecha_inicio, fecha_fin, productos(nombre, marca, tamano, unit:unidad, id_cat), supermercados(nombre_supermercado), sucursales(nombre_sucursal, ciudad)").execute()
        df = pd.json_normalize(res.data) if res.data else pd.DataFrame()
    except: df = pd.DataFrame()

    if not df.empty:
        df['productos.categoria'] = df['productos.id_cat'].map(c_inv).fillna("Sin Categoría")
        
        rep = st.sidebar.radio("Buscar ofertas por:", ["Ofertas por Producto", "Ofertas por Marca", "Ofertas por Supermercado", "Ofertas por Categoría"])
        
        # Formateo de columnas para mostrar la tabla limpia
        df_vista = df.rename(columns={
            'productos.nombre': 'Producto', 'productos.marca': 'Marca', 'productos.tamano': 'Tamaño',
            'productos.unit': 'Unidad', 'precio_oferta': 'Precio Oferta', 'fecha_inicio': 'Inicio',
            'fecha_fin': 'Fin', 'supermercados.nombre_supermercado': 'Supermercado',
            'sucursales.nombre_sucursal': 'Sucursal', 'sucursales.ciudad': 'Ciudad', 'productos.categoria': 'Categoría'
        })
        columnas_finales = ['Producto', 'Marca', 'Tamaño', 'Unidad', 'Precio Oferta', 'Supermercado', 'Sucursal', 'Ciudad', 'Inicio', 'Fin', 'Categoría']
        
        if rep == "Ofertas por Producto":
            st.subheader("🔍 Buscar por Nombre de Producto")
            txt_p = st.text_input("Escribe el nombre del producto (ej: Arroz, Leche):")
            if txt_p:
                df_filtrado = df_vista[df_vista['Producto'].str.contains(txt_p, case=False)]
                st.dataframe(df_filtrado[columnas_finales], use_container_width=True)
            else: st.dataframe(df_vista[columnas_finales], use_container_width=True)
            
        elif rep == "Ofertas por Marca":
            st.subheader("🏷️ Buscar por Marca")
            txt_m = st.text_input("Escribe la marca del producto:")
            if txt_m:
                df_filtrado = df_vista[df_vista['Marca'].str.contains(txt_m, case=False)]
                st.dataframe(df_filtrado[columnas_finales], use_container_width=True)
            else: st.dataframe(df_vista[columnas_finales], use_container_width=True)
            
        elif rep == "Ofertas por Supermercado":
            st.subheader("🏢 Buscar por Supermercado")
            txt_s = st.text_input("Escribe el nombre del supermercado:")
            if txt_s:
                df_filtrado = df_vista[df_vista['Supermercado'].str.contains(txt_s, case=False)]
                st.dataframe(df_filtrado[columnas_finales], use_container_width=True)
            else: st.dataframe(df_vista[columnas_finales], use_container_width=True)
            
        elif rep == "Ofertas por Categoría":
            st.subheader("📁 Buscar por Categoría")
            txt_c = st.text_input("Escribe la categoría:")
            if txt_c:
                df_filtrado = df_vista[df_vista['Categoría'].str.contains(txt_c, case=False)]
                st.dataframe(df_filtrado[columnas_finales], use_container_width=True)
            else: st.dataframe(df_vista[columnas_finales], use_container_width=True)
    else: st.info("No hay datos de ofertas disponibles para realizar búsquedas.")

# --- SECCIÓN 3: GESTIÓN DE PRODUCTOS ---
elif choice == "📦 Gestión de Productos":
    st.title("📦 Administración del Catálogo de Productos")
    t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])
    
    try:
        res_p = supabase.table("productos").select("*").order("nombre").execute()
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
    except: df_p = pd.DataFrame()

    with t1:
        if not df_p.empty:
            df_m = df_p.copy()
            if 'id_cat' in df_m.columns: df_m['categoria'] = df_m['id_cat'].map(c_inv)
            if 'id_subcat' in df_m.columns: df_m['subcategoria'] = df_m['id_subcat'].map(sc_inv)
            st.dataframe(df_m, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
        else: st.info("El catálogo está vacío.")
            
    with t2:
        st.subheader("Formulario de Carga")
        c1, c2 = st.columns(2)
        n_nom = c1.text_input("Nombre del Producto*", key="n_n")
        n_mar = c2.text_input("Marca", key="n_m")
        n_bar = c1.text_input("Código de Barras", key="n_b").strip()
        n_tam = c2.number_input("Tamaño / Peso", min_value=0.0, step=0.1, key="n_t")
        n_uni = c1.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="n_u")
        n_fot = c2.file_uploader("Foto del Producto", type=['jpg', 'png', 'jpeg', 'webp'], key="n_f")
        
        cat_s = c1.selectbox("Categoría Principal (Orden Numérico)", ["--- Seleccionar ---"] + lista_cat, key="n_c_s")
        sub_ops = ["--- Seleccionar ---"]
        if cat_s != "--- Seleccionar ---":
            r_sf = supabase.table("subcategorias").select("*").eq("id_cat", c_dict[cat_s]).order("nombre").execute()
            if r_sf.data: sub_ops += [s['nombre'] for s in r_sf.data]
        sub_s = c2.selectbox("Subcategoría (Reactiva)", sub_ops, key="n_s_s")
        
        forzar = st.checkbox("⚠️ Forzar registro (Ignorar alertas de duplicados)")
        if st.button("🚀 Guardar Nuevo Producto", type="primary"):
            if n_nom:
                err, clon = validar_producto_existente(n_nom, n_mar, n_bar, n_tam, n_uni)
                if err and not forzar:
                    st.error(f"🚨 DUPLICADO DETECTADO: Coincide con {clon['nombre']} ({clon['marca']})")
                else:
                    u_img = subir_a_storage(n_fot)
                    v_cat = c_dict[cat_s] if cat_s != "--- Seleccionar ---" else None
                    v_sub = None
                    if sub_s != "--- Seleccionar ---" and v_cat:
                        r_b = supabase.table("subcategorias").select("id_subcat").eq("nombre", sub_s).eq("id_cat", v_cat).execute()
                        if r_b.data: v_sub = r_b.data[0]['id_subcat']
                    
                    supabase.table("productos").insert({"nombre": n_nom, "marca": n_mar, "codigo_barras": n_bar if n_bar else None, "tamano": n_tam, "unidad": n_uni, "url_imagen": u_img, "id_cat": v_cat, "id_subcat": v_sub}).execute()
                    st.success("¡Guardado!"); st.rerun()
            else: st.warning("El nombre es obligatorio.")

    with t3:
        if not df_p.empty:
            p_dict = {f"{p['nombre']} - {p['marca']} ({p['tamano']}{p['unidad']})": p for p in res_p.data}
            sel_e = st.selectbox("Selecciona un producto existente:", list(p_dict.keys()))
            p_e = p_dict[sel_e]
            
            st.write("---")
            ec1, ec2 = st.columns(2)
            en = ec1.text_input("Modificar Nombre", p_e['nombre'])
            em = ec2.text_input("Modificar Marca", p_e['marca'])
            eb = ec1.text_input("Modificar Código de Barras", p_e['codigo_barras'] or "").strip()
            et = ec2.number_input("Modificar Tamaño", value=float(p_e['tamano']) if p_e['tamano'] else 0.0)
            eu = ec1.selectbox("Modificar Unidad", ["gr", "kg", "ml", "lt", "unidad"], index=["gr", "kg", "ml", "lt", "unidad"].index(p_e['unidad']) if p_e['unidad'] in ["gr", "kg", "ml", "lt", "unidad"] else 0)
            ef = ec2.file_uploader("Cambiar Imagen", type=['jpg', 'png', 'jpeg', 'webp'])
            
            c_act = c_inv.get(p_e['id_cat'], "--- Seleccionar ---")
            l_cat_e = ["--- Seleccionar ---"] + lista_cat
            idx_c = l_cat_e.index(c_act) if c_act in l_cat_e else 0
            ecat = ec1.selectbox("Modificar Categoría Principal", l_cat_e, index=idx_c, key="e_c")
            
            s_act = sc_inv.get(p_e['id_subcat'], "--- Seleccionar ---")
            l_sub_e = ["--- Seleccionar ---"]
            if ecat != "--- Seleccionar ---":
                r_se = supabase.table("subcategorias").select("*").eq("id_cat", c_dict[ecat]).order("nombre").execute()
                if r_se.data: l_sub_e += [s['nombre'] for s in r_se.data]
            idx_s = l_sub_e.index(s_act) if s_act in l_sub_e else 0
            esub = ec2.selectbox("Modificar Subcategoría", l_sub_e, index=idx_s, key="e_s")
            
            f_ed = st.checkbox("⚠️ Forzar cambios en edición")
            b_del, b_upd = st.columns(2)
            
            if b_upd.button("💾 Guardar Cambios del Producto", type="primary"):
                err, clon = validar_producto_existente(en, em, eb, et, eu, id_excluir=p_e['id_producto'])
                if err and not f_ed: st.error(f"🚨 DUPLICADO: Conflicto con {clon['nombre']}")
                else:
                    n_url = subir_a_storage(ef) if ef else p_e['url_imagen']
                    v_c = c_dict[ecat] if ecat != "--- Seleccionar ---" else None
                    v_s = None
                    if esub != "--- Seleccionar ---" and v_c:
                        r_be = supabase.table("subcategorias").select("id_subcat").eq("nombre", esub).eq("id_cat", v_c).execute()
                        if r_be.data: v_s = r_be.data[0]['id_subcat']
                        
                    supabase.table("productos").update({"nombre": en, "marca": em, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": n_url, "id_cat": v_c, "id_subcat": v_s}).eq("id_producto", p_e['id_producto']).execute()
                    st.success("¡Cambios guardados!"); st.rerun()
                    
            if b_del.button("🗑️ Eliminar Producto Definitivamente"):
                supabase.table("productos").delete().eq("id_producto", p_e['id_producto']).execute()
                st.warning("Producto borrado."); st.rerun()

# --- SECCIÓN 4: ESTRUCTURA (CAT/SUBCAT HOMOLOGADA) ---
elif choice == "📁 Estructura (Cat/Subcat)":
    st.title("📁 Administración de Clasificación Jerárquica")
    t1, t2 = st.tabs(["📁 Categorías Principales", "🌿 Subcategorías (Hijos)"])
    
    try:
        res_c = supabase.table("categorias").select("*").order("id_cat").execute()
        df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
        res_sc = supabase.table("subcategorias").select("*, categorias(nombre, id_cat)").execute()
        df_sc = pd.json_normalize(res_sc.data) if res_sc.data else pd.DataFrame()
    except: df_c, df_sc = pd.DataFrame(), pd.DataFrame()

    with t1:
        tc1, tc2, tc3 = st.tabs(["📋 Ver Categorías", "➕ Nueva Categoría", "✏️ Editar/Borrar"])
        with tc1:
            if not df_c.empty: st.dataframe(df_c[['id_cat', 'nombre']], use_container_width=True)
            else: st.info("No hay categorías.")
        with tc2:
            n_cat = st.text_input("Nombre de la Nueva Categoría Principal")
            if st.button("🚀 Guardar Categoría"):
                if n_cat:
                    supabase.table("categorias").insert({"nombre": n_cat}).execute()
                    st.success("Guardada."); st.rerun()
        with tc3:
            if not df_c.empty:
                c_map = {c['nombre']: c for c in res_cat.data}
                s_c = st.selectbox("Selecciona Categoría:", list(c_map.keys()), key="s_c_e")
                c_d = c_map[s_c]
                un_c = st.text_input("Nombre", c_d['nombre'], key="u_c_n")
                bc1, bc2 = st.columns(2)
                if bc1.button("💾 Actualizar Categoría"):
                    supabase.table("categorias").update({"nombre": un_c}).eq("id_cat", c_d['id_cat']).execute()
                    st.success("Listo."); st.rerun()
                if bc2.button("🗑️ Eliminar Categoría"):
                    supabase.table("categorias").delete().eq("id_cat", c_d['id_cat']).execute()
                    st.warning("Borrada."); st.rerun()

    with t2:
        tsc1, tsc2, tsc3 = st.tabs(["📋 Ver Subcategorías", "➕ Nueva Subcategoría", "✏️ Editar/Borrar"])
        with tsc1:
            if not df_sc.empty:
                df_ord = df_sc.sort_values(by='categorias.id_cat')
                st.dataframe(df_ord.rename(columns={'nombre': 'Subcategoría', 'categorias.nombre': 'Categoría Padre', 'categorias.id_cat': 'N° Cat'})[['N° Cat', 'Categoría Padre', 'Subcategoría']], use_container_width=True)
            else: st.info("No hay subcategorías.")
        with tsc2:
            if lista_cat:
                c_padre = st.selectbox("Selecciona Categoría Padre (Orden Numérico):", lista_cat, key="sc_p")
                n_sub = st.text_input("Nombre de Subcategoría")
                if st.button("🚀 Guardar Subcategoría"):
                    if n_sub:
                        supabase.table("subcategorias").insert({"nombre": n_sub, "id_cat": c_dict[c_padre]}).execute()
                        st.success("Guardada."); st.rerun()
            else: st.warning("Crea una categoría primero.")
        with tsc3:
            if not df_sc.empty:
                sc_map = {f"{r['categorias.nombre']} -> {r['nombre']}": r for _, r in df_sc.iterrows()}
                s_sc = st.selectbox("Selecciona Subcategoría:", list(sc_map.keys()), key="s_sc_e")
                sc_d = sc_map[s_sc]
                un_sc = st.text_input("Modificar Nombre de Subcategoría", value=sc_d['nombre'], key="u_sc_n")
                bsc1, bsc2 = st.columns(2)
                if bsc1.button("💾 Actualizar Subcategoría"):
                    # CORREGIDO: Guarda correctamente los cambios en Supabase usando id_subcat
                    supabase.table("subcategorias").update({"nombre": un_sc}).eq("id_subcat", sc_d['id_subcat']).execute()
                    st.success("Subcategoría actualizada exitosamente."); st.rerun()
                if bsc2.button("🗑️ Eliminar Subcategoría"):
                    supabase.table("subcategorias").delete().eq("id_subcat", sc_d['id_subcat']).execute()
                    st.warning("Borrada."); st.rerun()

# --- SECCIÓN 5: TIENDAS Y SUCURSALES ---
elif choice == "🏪 Tiendas y Sucursales":
    st.title("🏪 Administración de Tiendas")
    t1, t2 = st.tabs(["🏢 Cadenas (Supermercados)", "📍 Sucursales"])
    try:
        supers = supabase.table("supermercados").select("*").order("nombre_supermercado").execute()
        df_s = pd.DataFrame(supers.data) if supers.data else pd.DataFrame()
        sucs = supabase.table("sucursales").select("*, supermercados(nombre_supermercado)").execute()
        df_suc = pd.json_normalize(sucs.data) if sucs.data else pd.DataFrame()
    except: df_s, df_suc = pd.DataFrame(), pd.DataFrame()

    with t1:
        sub_t1, sub_t2 = st.columns(2)
        with sub_t1:
            with st.form("super_add", clear_on_submit=True):
                nom = st.text_input("Nombre de la Cadena")
                if st.form_submit_button("Guardar Cadena"):
                    if nom: supabase.table("supermercados").insert({"nombre_supermercado": nom}).execute(); st.success("Registrado."); st.rerun()
        with sub_t2:
            if not df_s.empty:
                super_map = {r['nombre_supermercado']: r for r in supers.data}
                sel_super = st.selectbox("Modificar Cadena:", list(super_map.keys()))
                s_data = super_map[sel_super]
                with st.form("super_edit"):
                    enom = st.text_input("Editar Nombre", value=s_data['nombre_supermercado'])
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Guardar"): supabase.table("supermercados").update({"nombre_supermercado": enom}).eq("id_super", s_data['id_super']).execute(); st.success("Actualizado."); st.rerun()
                    if b2.form_submit_button("🗑️ Eliminar"): supabase.table("supermercados").delete().eq("id_super", s_data['id_super']).execute(); st.warning("Eliminado."); st.rerun()

    with t2:
        if not df_s.empty:
            super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
            c_add, c_edit = st.columns(2)
            with c_add:
                with st.form("suc_add", clear_on_submit=True):
                    s_sel = st.selectbox("Cadena perteneciente:", list(super_dict.keys()))
                    n_suc = st.text_input("Nombre de Sucursal")
                    ciu = st.text_input("Ciudad")
                    if st.form_submit_button("Guardar Sucursal"):
                        if n_suc and ciu: supabase.table("sucursales").insert({"id_super": super_dict[s_sel], "nombre_sucursal": n_suc, "ciudad": ciu}).execute(); st.success("Guardado."); st.rerun()
            with c_edit:
                if not df_suc.empty:
                    suc_map = {f"{r['supermercados.nombre_supermercado']} - {r['nombre_sucursal']}": r for _, r in df_suc.iterrows()}
                    sel_suc_edit = st.selectbox("Selecciona Sucursal:", list(suc_map.keys()))
                    suc_data = \
                    suc_map[sel_suc_edit]
                    with st.form("suc_edit_form"):
                        esuc_name = st.text_input("Nombre", value=suc_data['nombre_sucursal'] if 'nombre_sucursal' in suc_data else "")
                        eciu = st.text_input("Ciudad", value=suc_data['ciudad'] if 'ciudad' in suc_data else "")
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("💾 Actualizar"): supabase.table("sucursales").update({"nombre_sucursal": esuc_name, "ciudad": eciu}).eq("id_sucursal", suc_data['id_sucursal']).execute(); st.success("Actualizado."); st.rerun()
                        if b2.form_submit_button("🗑️ Borrar"): supabase.table("sucursales").delete().eq("id_sucursal", suc_data['id_sucursal']).execute(); st.warning("Borrado."); st.rerun()

# --- SECCIÓN 6: REGISTRAR OFERTAS (CON FECHA INICIO) ---
elif choice == "🏷️ Registrar Ofertas":
    st.title("🏷️ Cargar Ofertas por Catálogo")
    try: supers = supabase.table("supermercados").select("*").order("nombre_supermercado").execute()
    except: supers = None

    if supers and supers.data:
        df_s = pd.DataFrame(supers.data)
        super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        super_sel = st.selectbox("¿De qué Supermercado es el volante?", list(super_dict.keys()))
        
        try: sucs = supabase.table("sucursales").select("*").eq("id_super", super_dict[super_sel]).execute()
        except: sucs = None

        suc_dict = {"--- TODAS LAS SUCURSALES ---": None}
        if sucs and sucs.data:
            for s in sucs.data: suc_dict[s['nombre_sucursal']] = s['id_sucursal']
        suc_sel = st.selectbox("¿Aplica a una sucursal específica?", list(suc_dict.keys()))
        
        try: prods = supabase.table("productos").select("id_producto, nombre, marca, id_cat").execute()
        except: prods = None

        if prods and prods.data:
            p_df = pd.DataFrame(prods.data)
            p_df['cat_nombre'] = p_df['id_cat'].map(c_inv).fillna("Sin Categoría")
            p_df['label_visual'] = "[" + p_df['cat_nombre'] + "] " + p_df['nombre'] + " (" + p_df['marca'] + ")"
            p_dict = dict(zip(p_df['label_visual'], p_df['id_producto']))
            lista_prods_ordenada = sorted(list(p_dict.keys()))
            
            with st.form("form_of"):
                p_sel = st.selectbox("Producto en oferta", lista_prods_ordenada)
                precio = st.number_input
