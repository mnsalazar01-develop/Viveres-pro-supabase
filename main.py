import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date

# 1. CONFIGURACIÓN GLOBAL FORZADA DE LA APP Y CONEXIÓN
st.set_page_config(page_title="Control Víveres Pro v3.0", layout="wide", page_icon="🛒")

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()
URL_DEFECTO = "flaticon.com"

# --- FUNCIONES DE SOPORTE MAESTRAS ---
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
        n_n, m_n = "".join(nombre.lower().split()), "".join((marca or "").lower().split())
        t_n = float(tamano if tamano is not None else 0)
        u_n = unidad.lower()
        for p in res_t.data:
            if n_n == "".join(p['nombre'].lower().split()) and m_n == "".join((p['marca'] or "").lower().split()) and t_n == float(p['tamano'] or 0) and u_n == (p['unidad'] or "").lower():
                return "atributos", p
    return None, None

# 2. ENRUTADOR DEL MENÚ PRINCIPAL
st.sidebar.title("🛒 Control Víveres")
st.sidebar.caption("Versión 3.0 Estable Sólida")
menu = ["🔍 Alertas y Ofertas", "📊 Reportes Estadísticos", "📦 Gestión de Productos", "🗂️ Estructura (Cat/Subcat)", "🏪 Tiendas y Sucursales", "🏷️ Registrar Ofertas"]
choice = st.sidebar.selectbox("Ir a:", menu)

# --- CONSULTAS DE DATOS GLOBALES MAESTROS ---
try:
    res_cat = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_cat.data} if res_cat.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_cat.data} if res_cat.data else {}
    lista_cat = [c['nombre'] for c in res_cat.data] if res_cat.data else []

    res_todos_p = supabase.table("productos").select("marca").execute()
    lista_todas_marcas = sorted(list(set([p['marca'] for p in res_todos_p.data if p.get('marca') and p['marca'].strip() != ""]))) if res_todos_p.data else []

    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
except:
    cat_dict, cat_inv_dict, lista_cat, lista_todas_marcas, subcat_inv_dict = {}, {}, [], [], {}

# --- SECCIÓN 1: ALERTAS Y OFERTAS ---
if choice == "🔍 Alertas y Ofertas":
    st.title("🔔 Mis Alertas y Ofertas")
    try:
        res_p = supabase.table("productos").select("nombre").execute()
        lista_productos = sorted(list(set([p['nombre'] for p in res_p.data]))) if res_p.data else []
    except: lista_productos = []
    productos_interes = st.multiselect("⭐ Filtrar por lo que necesitas comprar hoy:", lista_productos)

    try:
        res = supabase.table("ofertas").select("id_oferta, precio_oferta, fecha_inicio, fecha_fin, id_producto, productos(nombre, marca, url_imagen, tamano, unidad), supermercados(nombre_supermercado), sucursales(nombre_sucursal)").execute()
    except: res = None

    if res and res.data:
        lista_limpia = []
        for o in res.data:
            prod, sup, suc = o.get("productos") or {}, o.get("supermercados") or {}, o.get("sucursales") or {}
            lista_limpia.append({
                "id_oferta": o.get("id_oferta"), "id_producto": o.get("id_producto"), "precio_oferta": float(o.get("precio_oferta", 0)),
                "fecha_inicio": o.get("fecha_inicio"), "fecha_fin": o.get("fecha_fin"), "prod_nombre": prod.get("nombre", "Desconocido"),
                "prod_marca": prod.get("marca", ""), "prod_imagen": prod.get("url_imagen"), "prod_tamano": prod.get("tamano", 0),
                "prod_unidad": prod.get("unidad", "ud"), "super_nombre": sup.get("nombre_supermercado", "Supermercado"), "suc_nombre": suc.get("nombre_sucursal", "Todas las sucursales")
            })
        df = pd.DataFrame(lista_limpia)
        if productos_interes and not df.empty: df = df[df['prod_nombre'].isin(productos_interes)]

        if not df.empty:
            df['fecha_dt'] = pd.to_datetime(df['fecha_fin'], errors='coerce')
            df = df.sort_values(by='fecha_dt')
            for prod_id, grupo in df.groupby('id_producto'):
                grp = grupo.sort_values(by='precio_oferta')
                with st.container(border=True):
                    c_img, c_info = st.columns(2)
                    with c_img: st.image(grp['prod_imagen'].iloc if grp['prod_imagen'].iloc and str(grp['prod_imagen'].iloc).strip() != "" else URL_DEFECTO, use_container_width=True)
                    with c_info:
                        st.subheader(f"{grp['prod_nombre'].iloc} - {grp['prod_marca'].iloc} ({grp['prod_tamano'].iloc} {grp['prod_unidad'].iloc})")
                        cols_tiendas = st.columns(len(grp))
                        for i, (_, f) in enumerate(grp.iterrows()):
                            hoy = date.today()
                            fecha_v = f['fecha_dt'].date() if pd.notna(f['fecha_dt']) else hoy
                            dias = (fecha_v - hoy).days
                            es_b = (i == 0)
                            try: f_ini = datetime.strptime(f['fecha_inicio'], '%Y-%m-%d').strftime('%d/%m/%Y')
                            except: f_ini = "N/A"
                            f_fin = fecha_v.strftime('%d/%m/%Y')
                            with cols_tiendas[i]:
                                st.markdown(f'<div style="border: 2px solid {"#2bc443" if es_b else "#ccc"}; border-radius: 8px; padding: 10px; text-align: center; background-color: {"#f0fff4" if es_b else "#fff"}; margin-bottom: 5px;"><b>{"🏆 MEJOR PRECIO" if es_b else "Opción Alternativa"}</b><h4>{f["super_nombre"]}</h4><p style="margin: 0; font-size: 0.75em; color: gray;">{f["suc_nombre"]}</p></div>', unsafe_allow_html=True)
                                st.metric(label="Precio", value=f"${f['precio_oferta']:.2f}")
                                st.caption(f"📅 **Inicio:** {f_ini}")
                                if 0 <= dias <= 2: st.error(f"🚨 ¡CORRE! Vence en {dias} día(s) ({f_fin})")
                                elif dias < 0: st.warning("⚠️ Oferta Caducada")
                                else: st.info(f"⏳ **Fin:** {f_fin}")
        else: st.warning("No hay ofertas para la búsqueda.")
    else: st.info("Aún no has registrado ninguna oferta.")

# --- SECCIÓN 2: REPORTES ESTADÍSTICOS ---
elif choice == "📊 Reportes Estadísticos":
    st.title("📊 Panel de Consultas Estadísticas")
    try:
        res = supabase.table("ofertas").select("precio_oferta, fecha_inicio, fecha_fin, productos(nombre, marca, id_cat), supermercados(nombre_supermercado), sucursales(nombre_sucursal)").execute()
        lista_limpia = []
        if res.data:
            for o in res.data:
                prod, sup, suc = o.get("productos") or {}, o.get("supermercados") or {}, o.get("sucursales") or {}
                lista_limpia.append({"nombre": prod.get("nombre", "N/A"), "marca": prod.get("marca", "Sin Marca"), "categoria": cat_inv_dict.get(prod.get("id_cat"), "Sin Categoría"), "supermercado": sup.get("nombre_supermercado", "N/A"), "sucursal": suc.get("nombre_sucursal") or "Todas", "precio_oferta": float(o.get("precio_oferta", 0)), "fecha_inicio": o.get("fecha_inicio", "N/A"), "fecha_fin": o.get("fecha_fin", "N/A")})
        df = pd.DataFrame(lista_limpia)
    except: df = pd.DataFrame()

    if not df.empty:
        rep = st.sidebar.radio("Filtrar Análisis por:", ["Por Producto", "Por Marca", "Por Supermercado", "Por Categoría"])
        if rep == "Por Producto":
            sel = st.selectbox("Selecciona un Producto:", sorted(list(df['nombre'].unique())))
            df_v = df[df['nombre'] == sel]
        elif rep == "Por Marca":
            sel = st.selectbox("Selecciona una Marca registrada:", lista_todas_marcas)
            df_v = df[df['marca'] == sel]
        elif rep == "Por Supermercado":
            sel = st.selectbox("Selecciona un Supermercado:", sorted(list(df['supermercado'].unique())))
            df_v = df[df['supermercado'] == sel]
        elif rep == "Por Categoría":
            sel = st.selectbox("Selecciona una Categoría:", sorted(list(df['categoria'].unique())))
            df_v = df[df['categoria'] == sel]

        st.subheader(f"🔍 Resultados para: {sel}")
        if not df_v.empty:
            df_mostrar = df_v.copy()
            df_mostrar['precio_oferta'] = df_mostrar['precio_oferta'].map(lambda x: f"${x:.2f}")
            st.dataframe(df_mostrar[['nombre', 'marca', 'categoria', 'supermercado', 'sucursal', 'precio_oferta', 'fecha_inicio', 'fecha_fin']], use_container_width=True)
        else: st.warning(f"El elemento '{sel}' no tiene ofertas vigentes.")
    else: st.info("No hay ofertas registradas para generar reportes.")

# --- SECCIÓN 3: GESTIÓN DE PRODUCTOS ---
elif choice == "📦 Gestión de Productos":
    st.title("📦 Administración de Productos")
    t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])
    
    with t1:
        if not df_p.empty:
            df_m = df_p.copy()
            if 'id_cat' in df_m.columns: df_m['categoria'] = df_m['id_cat'].map(cat_inv_dict)
            if 'id_subcat' in df_m.columns: df_m['subcategoria'] = df_m['id_subcat'].map(subcat_inv_dict)
            st.dataframe(df_m, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
        else: st.info("El catálogo está vacío.")
            
    with t2:
        st.subheader("Formulario de Carga Ágil")
        lista_autocompletar = ["➕ Registrar Producto Nuevo (Campos Vacíos)"]
        prod_mapeo = {}
        if not df_p.empty:
            for _, p in df_p.iterrows():
                label = f"{p['nombre']} - {p['marca'] or 'Sin Marca'} ({p['tamano'] or 0} {p['unidad'] or ''})"
                lista_autocompletar.append(label)
                prod_mapeo[label] = p
        seleccion_auto = st.selectbox("🔍 ¿El producto ya existe? Búscalo aquí para autorellenar:", lista_autocompletar, key="auto_p")
        es_nuevo = (seleccion_auto == "➕ Registrar Producto Nuevo (Campos Vacíos)")
        p_ref = prod_mapeo.get(seleccion_auto, {}) if not es_nuevo else {}
        
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre del Producto*", value=p_ref.get("nombre", ""), key="n_nom")
        marca = c2.text_input("Marca", value=p_ref.get("marca", ""), key="n_mar")
        barras = c1.text_input("Código de Barras", value=p_ref.get("codigo_barras", ""), key="n_bar").strip()
        tam = c2.number_input("Tamaño / Peso (Sube de 1 en 1)", min_value=0.0, step=1.0, value=float(p_ref["tamano"]) if "tamano" in p_ref and p_ref["tamano"] is not None else None, key="n_tam")
        uni = c1.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], index=["gr", "kg", "ml", "lt", "unidad"].index(p_ref["unidad"]) if "unidad" in p_ref and p_ref["unidad"] in ["gr", "kg", "ml", "lt", "unidad"] else 0, key="n_uni")
        foto = c2.file_uploader("Foto del Producto", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
        
        cat_actual_auto = cat_inv_dict.get(p_ref.get("id_cat"), "--- Seleccionar ---")
        l_cat_f = ["--- Seleccionar ---"] + lista_cat
        categoria_sel = c1.selectbox("Categoría Principal (Orden Numérico)", l_cat_f, index=l_cat_f.index(cat_actual_auto) if cat_actual_auto in l_cat_f else 0, key="n_cat")
        subcat_opciones = ["--- Seleccionar ---"]
        if categoria_sel != "--- Seleccionar ---":
            res_sub_filtradas = supabase.table("subcategorias").select("*").eq("id_cat", cat_dict[categoria_sel]).order("nombre").execute()
            if res_sub_filtradas.data: subcat_opciones += [s['nombre'] for s in res_sub_filtradas.data]
        subcat_actual_auto = subcat_inv_dict.get(p_ref.get("id_subcat"), "--- Seleccionar ---")
        subcategoria_sel = c2.selectbox("Subcategoría (Reactiva)", subcat_opciones, index=subcat_opciones.index(subcat_actual_auto) if subcat_actual_auto in subcat_opciones else 0, key="n_sub")
        
        forzar_guardado = st.checkbox("⚠️ Forzar el registro", key="n_forzar")
        if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
            if nombre:
                tipo_error, clon = validar_producto_existente(nombre, marca, barras, tam, uni)
                if tipo_error and not forzar_guardado: st.error(f"🚨 CLON DETECTADO: Coincide con {clon['nombre']}")
                else:
                    url_img = subir_a_storage(foto) if foto else (p_ref.get("url_imagen") if not es_nuevo else None)
                    id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                    id_subcat_val = None
                    if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                        sub_buscar = supabase.table("subcategorias").select("id_subcat").eq("nombre", subcategoria_sel).eq("id_cat", id_cat_val).execute()
                        if sub_buscar.data: id_subcat_val = sub_buscar.data['id_subcat']
                    supabase.table("productos").insert({"nombre": nombre, "marca": marca, "codigo_barras": barras if barras else None, "tamano": tam, "unidad": uni, "url_imagen": url_img, "id_cat": id_cat_val, "id_subcat": id_subcat_val}).execute()
                    st.success("¡Producto guardado exitosamente!"); st.rerun()
            else: st.warning("El nombre es obligatorio.")

    with t3:
        if not df_p.empty:
            prod_dict_e = {f"{p['nombre']} - {p['marca']} ({p['tamano']}{p['unidad']})": p for p in res_p.data}
            sel_e = st.selectbox("Selecciona el producto específico que deseas modificar o eliminar:", list(prod_dict_e.keys()), key="s_e_p")
            p_e = prod_dict_e[sel_e]
            ec1, ec2 = st.columns(2)
            en = ec1.text_input("Modificar Nombre", p_e['nombre'])
            em = ec2.text_input("Modificar Marca", p_e['marca'])
            eb = ec1.text_input("Modificar Código de Barras", p_e['codigo_barras'] or "").strip()
            et = ec2.number_input("Modificar Tamaño", value=float(p_e['tamano']) if p_e['tamano'] else 0.0, step=1.0)
            eu = ec1.selectbox("Modificar Unidad", ["gr", "kg", "ml", "lt", "unidad"], index=["gr", "kg", "ml", "lt", "unidad"].index(p_e['unidad']) if p_e['unidad'] in ["gr", "kg", "ml", "lt", "unidad"] else 0)
            ef = ec2.file_uploader("Cambiar Imagen", type=['jpg', 'png', 'jpeg', 'webp'])
            
            c_act = cat_inv_dict.get(p_e['id_cat'], "--- Seleccionar ---")
            l_cat_e = ["--- Seleccionar ---"] + lista_cat
            ecat = ec1.selectbox("Modificar Categoría Principal", l_cat_e, index=l_cat_e.index(c_act) if c_act in l_cat_e else 0, key="e_c")
            l_sub_e = ["--- Seleccionar ---"]
            if ecat != "--- Seleccionar ---":
                r_se = supabase.table("subcategorias").select("*").eq("id_cat", cat_dict[ecat]).order("nombre").execute()
                if r_se.data: l_sub_e += [s['nombre'] for s in r_se.data]
            s_act = subcat_inv_dict.get(p_e['id_subcat'], "--- Seleccionar ---")
            esub = ec2.selectbox("Modificar Subcategoría", l_sub_e, index=l_sub_e.index(s_act) if s_act in l_sub_e else 0, key="e_s")
            f_ed = st.checkbox("⚠️ Forzar cambios en edición", key="e_forzar")
            b_del, b_upd = st.columns(2)
            
            if b_upd.button("💾 Guardar Cambios del Producto", type="primary"):
                err, clon = validar_producto_existente(en, em, eb, et, eu, id_excluir=p_e['id_producto'])
                if err and not f_ed: st.error(f"🚨 DUPLICADO: Conflicto con {clon['nombre']}")
                else:
                    n_url = subir_a_storage(ef) if ef else p_e['url_imagen']
                    v_c = cat_dict[ecat] if ecat != "--- Seleccionar ---" else None
                    v_s = None
                    if esub != "--- Seleccionar ---" and v_c:
                        r_be = supabase.table("subcategorias").select("id_subcat").eq("nombre", esub).eq("id_cat", v_c).execute()
                        if r_be.data: v_s = r_be.data['id_subcat']
                    supabase.table("productos").update({"nombre": en, "marca": em, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": n_url, "id_cat": v_c, "id_subcat": v_s}).eq("id_producto", p_e['id_producto']).execute()
                    st.success("¡Cambios guardados!"); st.rerun()
            if b_del.button("🗑️ Eliminar Producto Definitivamente"):
                supabase.table("productos").delete().eq("id_producto", p_e['id_producto']).execute()
                st.warning("Producto eliminado."); st.rerun()

# --- SECCIÓN 4: ESTRUCTURA (CAT/SUBCAT) ---
elif choice == "🗂️ Estructura (Cat/Subcat)":
    st.title("📁 Estructura de Clasificación Jerárquica")
    t1, t2 = st.tabs(["📁 Categorías Principales", "🌿 Subcategorías (Hijos)"])
    try:
        res_c = supabase.table("categorias").select("*").order("id_cat").execute()
        df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
        res_sc = supabase.table("subcategorias").select("*, categorias(nombre, id_cat)").execute()
        df_sc = pd.json_normalize(res_sc.data) if res_sc.data else pd.DataFrame()
    except: df_c, df_sc = pd.DataFrame(), pd.DataFrame()

    with t1:
        st.subheader("Módulo de Categorías")
        tc1, tc2 = st.tabs(["📋 Ver Categorías", "➕ Nueva Categoría"])
        with tc1: st.dataframe(df_c[['id_cat', 'nombre']], use_container_width=True) if not df_c.empty else st.info("No hay categorías.")
        with tc2:
            with st.form("f_add_c", clear_on_submit=True):
                n_cat = st.text_input("Nombre de la Nueva Categoría Principal")
                if st.form_submit_button("🚀 Guardar Categoría"):
                    if n_cat: supabase.table("categorias").insert({"nombre": n_cat}).execute(); st.success("Guardada."); st.rerun()

    with t2:
        st.subheader("Módulo de Subcategorías")
        tsc1, tsc2 = st.tabs(["📋 Ver Subcategorías", "➕ Nueva Subcategoría"])
        with tsc1:
            if not df_sc.empty:
                df_ord = df_sc.sort_values(by='categorias.id_cat')
                st.dataframe(df_ord.rename(columns={'nombre': 'Subcategoría', 'categorias.nombre': 'Categoría Padre', 'categorias.id_cat': 'N° Cat'})[['N° Cat', 'Categoría Padre', 'Subcategoría']], use_container_width=True)
            else: st.info("No hay subcategorías.")
        with tsc2:
            if lista_cat:
                with st.form("f_add_sc", clear_on_submit=True):
                    c_padre = st.selectbox("Selecciona Categoría Padre:", lista_cat)
                    n_sub = st.text_input("Nombre de Subcategoría")
                    if st.form_submit_button("🚀 Guardar Subcategoría"):
                        if n_sub: supabase.table("subcategorias").insert({"nombre": n_sub, "id_cat": cat_dict[c_padre]}).execute(); st.success("Guardada."); st.rerun()

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
        with st.form("super_add", clear_on_submit=True):
            nom = st.text_input("Nombre de la Cadena")
            if st.form_submit_button("🚀 Guardar Cadena"):
                if nom: supabase.table("supermercados").insert({"nombre_supermercado": nom}).execute(); st.success("Registrado."); st.rerun()
        if not df_s.empty: st.dataframe(df_s[['nombre_supermercado']], use_container_width=True)

    with t2:
        if not df_s.empty:
            super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
            c_add, c_view = st.columns(2)
            with c_add:
                with st.form("suc_add", clear_on_submit=True):
                    s_sel = st.selectbox("Cadena perteneciente:", list(super_dict.keys()))
                    n_suc = st.text_input("Nombre de Sucursal")
                    ciu = st.text_input("Ciudad")
                    if st.form_submit_button("Guardar Sucursal"):
                        if n_suc and ciu: supabase.table("sucursales").insert({"id_super": super_dict[s_sel], "nombre_sucursal": n_suc, "ciudad": ciu}).execute(); st.success("Guardado."); st.rerun()
            with c_view:
                if not df_suc.empty: st.dataframe(df_suc.rename(columns={'nombre_sucursal': 'Sucursal', 'ciudad': 'Ciudad', 'supermercados.nombre_supermercado': 'Cadena'})[['Cadena', 'Sucursal', 'Ciudad']], use_container_width=True)

# --- SECCIÓN 6: REGISTRAR OFERTAS ---
elif choice == "🏷️ Registrar Ofertas":
    st.title("🏷️ Cargar Ofertas por Catálogo")
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
            p_df['cat_nombre'] = p_df['id_cat'].map(cat_inv_dict).fillna("Sin Categoría")
            p_df['label_visual'] = "[" + p_df['cat_nombre'] + "] " + p_df['nombre'] + " (" + p_df['marca'] + ")"
            p_dict = dict(zip(p_df['label_visual'], p_df['id_producto']))
            lista_prods_ordenada = sorted(list(p_dict.keys()))
            
            with st.form("form_of", clear_on_submit=True):
                p_sel = st.selectbox("Producto en oferta", lista_prods_ordenada)
                precio = st.number_input("Precio Oferta", min_value=0.0, format="%.2f")
                c_fecha1, c_fecha2 = st.columns(2)
                inicio = c_fecha1.date_input("Fecha de Inicio", format="DD/MM/YYYY")
                vence = c_fecha2.date_input("Fecha de Vencimiento", format="DD/MM/YYYY")
                if st.form_submit_button("🚀 Publicar Oferta"):
                    try:
                        supabase.table("ofertas").insert({"id_producto": p_dict[p_sel], "id_super": super_dict[super_sel], "id_sucursal": suc_dict[suc_sel], "precio_oferta": precio, "fecha_inicio": str(inicio), "fecha_fin": str(vence)}).execute()
                        st.success("¡Oferta publicada!"); st.balloons()
                    except Exception as e: st.error(f"Error: {e}")
