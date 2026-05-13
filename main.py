import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, date

# 1. CONFIGURACIÓN DE PÁGINA E INICIALIZACIÓN
st.set_page_config(page_title="Control Víveres Pro", layout="wide", page_icon="🛒")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- ICONO POR DEFECTO PARA PRODUCTOS SIN FOTO ---
URL_FOTO_DEFECTO = "flaticon.com"

# --- CONFIGURACIÓN DE ESTADOS INTERNOS (Para refresco en cascada inmediato) ---
if "cat_crear" not in st.session_state:
    st.session_state["cat_crear"] = "--- Seleccionar ---"
if "cat_editar" not in st.session_state:
    st.session_state["cat_editar"] = "--- Seleccionar ---"

# --- FUNCIÓN PARA SUBIR IMÁGENES ---
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

# --- FUNCIÓN DE VALIDACIÓN ROBUSTA ANTI-DUPLICADOS ---
def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras:
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir:
            query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
        if res_barras.data:
            return "barras", res_barras.data

    query_textos = supabase.table("productos").select("*")
    if id_excluir:
        query_textos = query_textos.neq("id_producto", id_excluir)
    res_textos = query_textos.execute()
    
    if res_textos.data:
        nom_norm = "".join(nombre.lower().split())
        mar_norm = "".join(marca.lower().split()) if marca else ""
        tam_norm = float(tamano)
        uni_norm = unidad.lower()

        for p in res_textos.data:
            p_nom = "".join(p['nombre'].lower().split())
            p_mar = "".join(p['marca'].lower().split()) if p['marca'] else ""
            p_tam = float(p['tamano']) if p['tamano'] else 0.0
            p_uni = p['unidad'].lower() if p['unidad'] else ""

            if nom_norm == p_nom and mar_norm == p_mar and tam_norm == p_tam and p_uni == uni_norm:
                return "atributos", p

    return None, None

# 2. MENÚ LATERAL DE NAVEGACIÓN
st.sidebar.title("Menú Principal")
menu = ["🔍 Alertas y Ofertas", "📊 Reportes de Mercado", "📦 Gestión de Productos", "📁 Estructura (Cat/Subcat)", "🏪 Tiendas y Sucursales", "🏷️ Registrar Ofertas"]
choice = st.sidebar.selectbox("Ir a:", menu)

# --- SECCIÓN 1: ALERTAS Y OFERTAS ---
if choice == "🔍 Alertas y Ofertas":
    st.title("🔔 Mis Alertas y Ofertas")
    
    try:
        res_p = supabase.table("productos").select("nombre").execute()
        lista_productos = sorted(list(set([p['nombre'] for p in res_p.data]))) if res_p.data else []
    except:
        lista_productos = []
        
    productos_interes = st.multiselect("⭐ Filtrar por lo que necesitas comprar hoy:", lista_productos)

    try:
        res = supabase.table("ofertas").select("""
            id_oferta, precio_oferta, fecha_fin, id_producto,
            productos(nombre, marca, url_imagen, tamano, unidad),
            supermercados(nombre_supermercado),
            sucursales(nombre_sucursal)
        """).execute()
    except:
        res = None

    if res and res.data:
        df = pd.json_normalize(res.data)
        
        columnas_criticas = {
            'productos.nombre': 'Producto Desconocido', 'productos.marca': '',
            'productos.url_imagen': '', 'productos.tamano': 0, 'productos.unidad': 'ud',
            'supermercados.nombre_supermercado': 'Supermercado', 'sucursales.nombre_sucursal': 'Todas las sucursales'
        }
        for col, defecto in columnas_criticas.items():
            if col not in df.columns:
                df[col] = defecto
            else:
                df[col] = df[col].fillna(defecto)

        if productos_interes:
            df = df[df['productos.nombre'].isin(productos_interes)]

        if not df.empty:
            df['fecha_dt'] = pd.to_datetime(df['fecha_fin'])
            
            for prod_id, grupo in df.groupby('id_producto'):
                grupo_ordenado = grupo.sort_values(by='precio_oferta')
                
                p_nombre = grupo_ordenado['productos.nombre'].iloc[0]
                p_marca = grupo_ordenado['productos.marca'].iloc[0]
                p_img = grupo_ordenado['productos.url_imagen'].iloc[0]
                p_tam = grupo_ordenado['productos.tamano'].iloc[0]
                p_uni = grupo_ordenado['productos.unidad'].iloc[0]
                
                with st.container(border=True):
                    c_img, c_info = st.columns([1, 3])
                    
                    with c_img:
                        st.image(p_img if p_img else URL_FOTO_DEFECTO, use_container_width=True)
                    
                    with c_info:
                        st.subheader(f"{p_nombre} - {p_marca} ({p_tam} {p_uni})")
                        st.write("🛒 **Opciones disponibles en el mercado:**")
                        
                        num_ofertas = len(grupo_ordenado)
                        columnas_tiendas = st.columns(num_ofertas)
                        
                        for i, (_, fila) in enumerate(grupo_ordenado.iterrows()):
                            fecha_v = fila['fecha_dt'].date()
                            dias = (fecha_v - date.today()).days
                            
                            es_el_mas_barato = (i == 0)
                            borde_color = "#2bc443" if es_el_mas_barato else "#cccccc"
                            badge_ganador = "🏆 MEJOR PRECIO" if es_el_mas_barato else "Oferta"
                            suc_texto = fila['sucursales.nombre_sucursal']
                            
                            with columnas_tiendas[i]:
                                st.markdown(f"""
                                    <div style="border: 2px solid {borde_color}; border-radius: 8px; padding: 10px; text-align: center; background-color: {'#f0fff4' if es_el_mas_barato else '#ffffff'}; margin-bottom: 10px;">
                                        <b style="color: {'#2bc443' if es_el_mas_barato else '#555555'}; font-size: 0.85em;">{badge_ganador}</b>
                                        <h4 style="margin: 5px 0 0 0; color: #333333;">{fila['supermercados.nombre_supermercado']}</h4>
                                        <p style="margin: 0; font-size: 0.75em; color: gray;">{suc_texto}</p>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                st.metric(label="Precio", value=f"\${fila['precio_oferta']:.2f}")
                                
                                if 0 <= dias <= 2:
                                    st.error(f"🚨 ¡CORRE! Vence en {dias} día(s)")
                                elif dias < 0:
                                    st.warning("⚠️ Caducó")
                                else:
                                    st.caption(f"⏳ Vence: {fecha_v.strftime('%d/%m/%Y')}")
        else:
            st.warning("No hay ofertas para los productos seleccionados.")
    else:
        st.info("Aún no has registrado ninguna oferta.")

# --- SECCIÓN 2: REPORTES DE MERCADO ---
elif choice == "📊 Reportes de Mercado":
    st.title("📊 Panorámica y Estadísticas de Ofertas")
    
    try:
        res = supabase.table("ofertas").select("""
            precio_oferta, id_producto,
            productos(nombre, marca, id_cat),
            supermercados(nombre_supermercado),
            categorias(nombre)
        """).execute()
    except:
        res = None

    if res and res.data:
        df_rep = pd.json_normalize(res.data)
        
        # Mapeo manual seguro de nombres de categorías
        try:
            res_c_map = supabase.table("categorias").select("*").execute()
            mapa_cat = {c['id_cat']: c['nombre'] for c in res_c_map.data} if res_c_map.data else {}
        except:
            mapa_cat = {}
            
        df_rep['categoria_nombre'] = df_rep['productos.id_cat'].map(mapa_cat).fillna("Sin Categoría")

        # BARRA LATERAL INTERNA CON SELECTOR DE REPORTE
        st.sidebar.markdown("---")
        st.sidebar.subheader("📈 Tipo de Reporte")
        tipo_reporte = st.sidebar.radio(
            "Selecciona gráfico para visualizar:",
            ["Ofertas por Producto", "Ofertas por Marca", "Ofertas por Supermercado", "Ofertas por Categoría"]
        )

        if tipo_reporte == "Ofertas por Producto":
            st.subheader("📦 Volumen de Ofertas por Producto")
            conteo = df_rep['productos.nombre'].value_counts().reset_index()
            conteo.columns = ['Producto', 'Cantidad de Ofertas']
            st.bar_chart(conteo.set_index('Producto'), color="#2bc443")
            st.dataframe(conteo, use_container_width=True)

        elif tipo_reporte == "Ofertas por Marca":
            st.subheader("🏷️ Volumen de Ofertas por Marca")
            df_rep['productos.marca'] = df_rep['productos.marca'].replace('', 'Genérico')
            conteo = df_rep['productos.marca'].value_counts().reset_index()
            conteo.columns = ['Marca', 'Cantidad de Ofertas']
            st.bar_chart(conteo.set_index('Marca'), color="#4b9fff")
            st.dataframe(conteo, use_container_width=True)

        elif tipo_reporte == "Ofertas por Supermercado":
            st.subheader("🏢 Distribución de Ofertas por Cadena")
            conteo = df_rep['supermercados.nombre_supermercado'].value_counts().reset_index()
            conteo.columns = ['Supermercado', 'Cantidad de Ofertas']
            st.bar_chart(conteo.set_index('Supermercado'), color="#ffbf00")
            st.dataframe(conteo, use_container_width=True)

        elif tipo_reporte == "Ofertas por Categoría":
            st.subheader("📁 Distribución de Ofertas por Categoría")
            conteo = df_rep['categoria_nombre'].value_counts().reset_index()
            conteo.columns = ['Categoría', 'Cantidad de Ofertas']
            st.bar_chart(conteo.set_index('Categoría'), color="#ff4b4b")
            st.dataframe(conteo, use_container_width=True)
    else:
        st.info("No hay datos suficientes para generar gráficos. Registre ofertas primero.")

# --- SECCIÓN 3: GESTIÓN DE PRODUCTOS ---
elif choice == "📦 Gestión de Productos":
    st.title("📦 Gestión de Catálogo de Productos")
    t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])
    
    try:
        res_p = supabase.table("productos").select("*").order("nombre").execute()
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
        
        res_c = supabase.table("categorias").select("*").order("id_cat").execute()
        cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
        cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
        lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

        res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
        subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
    except:
        df_p = pd.DataFrame()
        cat_dict, cat_inv_dict, subcat_inv_dict = {}, {}, {}
        lista_cat = []

    with t1:
        if not df_p.empty:
            df_m = df_p.copy()
            if 'id_cat' in df_m.columns: df_m['categoria'] = df_m['id_cat'].map(cat_inv_dict)
            if 'id_subcat' in df_m.columns: df_m['subcategoria'] = df_m['id_subcat'].map(subcat_inv_dict)
            st.dataframe(df_m, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
        else:
            st.info("El catálogo está vacío.")
            
    with t2:
        # PANTALLA DE CARGA RESTAURADA: Pide los datos arriba y Categoría/Subcategoría abajo de forma reactiva
        with st.form("nuevo_p_form", clear_on_submit=True):
            st.subheader("➕ Registrar Nuevo Vívere")
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre del Producto*")
            marca = col2.text_input("Marca")
            barras = col1.text_input("Código de Barras")
            tam = col2.number_input("Tamaño/Peso", min_value=0.0, step=0.1)
            uni = col1.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"])
            foto = col2.file_uploader("Foto", type=['jpg', 'png', 'jpeg', 'webp'])
            
            # Selectores al final del formulario mediante variables controladas por cambio de estado externo
            st.divider()
            c_sel = st.selectbox("Categoría Principal (Al final)", ["--- Seleccionar ---"] + lista_cat, key="cat_prod_crear")
            
            sub_ops = ["--- Seleccionar ---"]
            if c_sel != "--- Seleccionar ---":
                id_c_actual = cat_dict[c_sel]
                res_sub_fil = supabase.table("subcategorias").select("*").eq("id_cat", id_c_actual).order("nombre").execute()
                if res_sub_fil.data: sub_ops += [s['nombre'] for s in res_sub_fil.data]
            
            sc_sel = st.selectbox("Subcategoría (Al final)", sub_ops, key="subcat_prod_crear")
            forzar_g = st.checkbox("⚠️ Forzar el registro sin advertencias")

            if st.form_submit_button("🚀 Guardar Producto"):
                if nombre:
                    t_err, clon = validar_producto_existente(nombre, marca, barras, tam, uni)
                    if t_err and not forzar_g:
                        st.error(f"🚨 DUPLICADO DETECTADO: Coincide con {clon['nombre']}")
                    else:
                        url_img = subir_a_storage(foto)
                        id_c_val = cat_dict[c_sel] if c_sel != "--- Seleccionar ---" else None
                        id_sc_val = None
                        if sc_sel != "--- Seleccionar ---" and id_c_val is not None:
                            sub_b = supabase.table("subcategorias").select("id_subcat").eq("nombre", sc_sel).eq("id_cat", id_c_val).execute()
                            if sub_b.data: id_sc_val = sub_b.data[0]['id_subcat']

                        try:
                            supabase.table("productos").insert({
                                "nombre": nombre, "marca": marca, "codigo_barras": barras if barras else None, 
                                "tamano": tam, "unidad": uni, "url_imagen": url_img, "id_cat": id_c_val, "id_subcat": id_sc_val
                            }).execute()
                            st.success("¡Producto guardado!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    with t3:
        # CONTROL RESTRINGIDO: Solo permite modificar o eliminar el primer registro
        if not df_p.empty:
            st.subheader("✏️ Modificar / Eliminar Producto")
            # Forzamos la selección del primer producto del catálogo exclusivamente
            primer_producto = res_p.data[0]
            st.info(f"🔒 Modo Control: Solo está permitido editar/eliminar el primer producto en base de datos: **{primer_producto['nombre']}**")
            
            cat_act_db = cat_inv_dict.get(primer_producto['id_cat'], "--- Seleccionar ---")
            cat_list_ed = ["--- Seleccionar ---"] + lista_cat
            idx_c_def = cat_list_ed.index(cat_act_db) if cat_act_db in cat_list_ed else 0
            
            ecat = st.selectbox("Categoría Principal (Al final)", cat_list_ed, index=idx_c_def, key="cat_prod_edit")
            
            subcat_act_db = subcat_inv_dict.get(primer_producto['id_subcat'], "--- Seleccionar ---")
            subcat_list_ed = ["--- Seleccionar ---"]
            if ecat != "--- Seleccionar ---":
                res_sub_ed = supabase.table("subcategorias").select("*").eq("id_cat", cat_dict[ecat]).order("nombre").execute()
                if res_sub_ed.data: subcat_list_ed += [s['nombre'] for s in res_sub_ed.data]
            
            idx_sc_def = subcat_list_ed.index(subcat_act_db) if subcat_act_db in subcat_list_ed else 0
            esubcat = st.selectbox("Subcategoría (Al final)", subcat_list_ed, index=idx_sc_def, key="subcat_prod_edit")

            with st.form("edit_p_form"):
                en = st.text_input("Nombre del Producto", primer_producto['nombre'])
                em = st.text_input("Marca", primer_producto['marca'])
                eb = st.text_input("Código de Barras", primer_producto['codigo_barras'] or "")
                et = st.number_input("Tamaño", value=float(primer_producto['tamano']) if primer_producto['tamano'] else 0.0)
                eu = st.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"], index=["gr", "kg", "ml", "lt", "unidad"].index(primer_producto['unidad']) if primer_producto['unidad'] in ["gr", "kg", "ml", "lt", "unidad"] else 0)
                ef = st.file_uploader("Cambiar Foto", type=['jpg', 'png', 'jpeg', 'webp'])
                
                c_del, c_upd = st.columns(2)
                if c_upd.form_submit_button("💾 Guardar Cambios"):
                    nueva_url = subir_a_storage(ef) if ef else primer_producto['url_imagen']
                    id_c_val = cat_dict[ecat] if ecat != "--- Seleccionar ---" else None
                    id_sc_val = None
                    if esubcat != "--- Seleccionar ---" and id_c_val is not None:
                        sub_b = supabase.table("subcategorias").select("id_subcat").eq("nombre", esubcat).eq("id_cat", id_c_val).execute()
                        if sub_b.data: id_sc_val = sub_b.data[0]['id_subcat']

                    supabase.table("productos").update({
                        "nombre": en, "marca": em, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": nueva_url, "id_cat": id_c_val, "id_subcat": id_sc_val
                    }).eq("id_producto", primer_producto['id_producto']).execute()
                    st.success("Cambios guardados."); st.rerun()
                    
                if c_del.form_submit_button("🗑️ Eliminar Producto"):
                    supabase.table("productos").delete().eq("id_producto", primer_producto['id_producto']).execute()
                    st.warning("Registro base eliminado."); st.rerun()

# --- SECCIÓN 4: ESTRUCTURA (CAT/SUBCAT) ---
elif choice == "📁 Estructura (Cat/Subcat)":
    st.title("📁 Estructura de Clasificación")
    t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Registro", "✏️ Editar/Borrar"])
    
    try:
        res_c = supabase.table("categorias").select("*").order("id_cat").execute()
        df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
        cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
        cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
        
        res_sc = supabase.table("subcategorias").select("*, categorias(nombre, id_cat)").execute()
        df_sc = pd.json_normalize(res_sc.data) if res_sc.data else pd.DataFrame()
    except:
        df_c, df_sc, cat_dict, cat_inv_dict = pd.DataFrame(), pd.DataFrame(), {}, {}

    with t1:
        st.subheader("📋 Catálogo Jerárquico")
        if not df_sc.empty:
            df_sc_ord = df_sc.sort_values(by='categorias.id_cat')
            df_sc_l = df_sc_ord.rename(columns={'nombre': 'Subcategoría', 'categorias.nombre': 'Categoría Padre', 'categorias.id_cat': 'N° Cat'})
            st.dataframe(df_sc_l[['N° Cat', 'Categoría Padre', 'Subcategoría']], use_container_width=True)
        else:
            st.info("No hay clasificaciones cargadas.")

    with t2:
        st.subheader("➕ Añadir Nueva Clasificación")
        col_c, col_sc = st.columns(2)
        with col_c:
            with st.form("new_cat_form", clear_on_submit=True):
                st.write("📁 Crear Categoría Padre")
                n_cat = st.text_input("Nombre")
                if st.form_submit_button("Guardar Categoría"):
                    if n_cat:
                        supabase.table("categorias").insert({"nombre": n_cat}).execute()
                        st.success("Guardada."); st.rerun()
        with col_sc:
            if not df_c.empty:
                with st.form("new_subcat_form", clear_on_submit=True):
                    st.write("🌿 Crear Subcategoría")
                    c_padre = st.selectbox("Categoría Padre:", list(cat_dict.keys()))
                    n_subcat = st.text_input("Nombre de Subcategoría")
                    if st.form_submit_button("Guardar Subcategoría"):
                        if n_subcat:
                            supabase.table("subcategorias").insert({"nombre": n_subcat, "id_cat": cat_dict[c_padre]}).execute()
                            st.success("Subcategoría guardada."); st.rerun()

    with t3:
        st.subheader("✏️ Modificar Estructuras")
        sub_tab_c, sub_tab_sc = st.columns(2)
        with sub_tab_c:
            if not df_c.empty:
                st.write("🔧 Modificar Categorías")
                sel_c = st.selectbox("Selecciona Categoría:", list(cat_dict.keys()), key="sel_cat_est")
                with st.form("edit_cat_f"):
                    unom = st.text_input("Nombre", value=sel_c)
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Actualizar"):
                        supabase.table("categorias").update({"nombre": unom}).eq("id_cat", cat_dict[sel_c]).execute()
                        st.success("Modificado."); st.rerun()
                    if b2.form_submit_button("🗑️ Eliminar"):
                        supabase.table("categorias").delete().eq("id_cat", cat_dict[sel_c]).execute()
                        st.warning("Eliminado."); st.rerun()
        with sub_tab_sc:
            if not df_sc.empty:
                st.write("🔧 Modificar Subcategorías")
                subcat_map = {f"[{r['categorias.nombre']}] {r['nombre']}": r for _, r in df_sc.iterrows()}
                sel_sc = st.selectbox("Selecciona Subcategoría:", list(subcat_map.keys()), key="sel_subcat_est")
                sc_d = subcat_map[sel_sc]
                with st.form("edit_subcat_f"):
                    uscnom = st.text_input("Nombre", value=sc_d['nombre'])
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Actualizar"):
                        supabase.table("subcategorias").update({"nombre": uscnom}).eq("id_subcat", sc_d['id_subcat']).execute()
                        st.success("Modificado."); st.rerun()
                    if b2.form_submit_button("🗑️ Borrar"):
                        supabase.table("subcategorias").delete().eq("id_subcat", sc_d['id_subcat']).execute()
                        st.warning("Borrado."); st.rerun()

# --- SECCIÓN 5: TIENDAS Y SUCURSALES ---
elif choice == "🏪 Tiendas y Sucursales":
    st.title("🏪 Administración de Tiendas")
    t1, t2 = st.tabs(["🏢 Cadenas (Supermercados)", "📍 Sucursales"])
    
    try:
        supers = supabase.table("supermercados").select("*").order("nombre_supermercado").execute()
        df_s = pd.DataFrame(supers.data) if supers.data else pd.DataFrame()
        sucs = supabase.table("sucursales").select("*, supermercados(nombre_supermercado)").execute()
        df_suc = pd.json_normalize(sucs.data) if sucs.data else pd.DataFrame()
    except:
        df_s, df_suc = pd.DataFrame(), pd.DataFrame()

    with t1:
        sub_t1, sub_t2 = st.columns(2)
        with sub_t1:
            with st.form("super_add", clear_on_submit=True):
                nom = st.text_input("Nombre de la Cadena")
                if st.form_submit_button("Guardar Cadena"):
                    if nom:
                        supabase.table("supermercados").insert({"nombre_supermercado": nom}).execute()
                        st.success("Registrado."); st.rerun()
        with sub_t2:
            if not df_s.empty:
                super_map = {r['nombre_supermercado']: r for r in supers.data}
                sel_super = st.selectbox("Modificar Cadena:", list(super_map.keys()))
                s_data = super_map[sel_super]
                with st.form("super_edit"):
                    enom = st.text_input("Editar Nombre", value=s_data['nombre_supermercado'])
                    b1, b2 = st.columns(2)
                    if b1.form_submit_button("💾 Guardar"):
                        supabase.table("supermercados").update({"nombre_supermercado": enom}).eq("id_super", s_data['id_super']).execute()
                        st.success("Actualizado."); st.rerun()
                    if b2.form_submit_button("🗑️ Eliminar"):
                        supabase.table("supermercados").delete().eq("id_super", s_data['id_super']).execute()
                        st.warning("Eliminado."); st.rerun()

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
                        if n_suc and ciu:
                            supabase.table("sucursales").insert({"id_super": super_dict[s_sel], "nombre_sucursal": n_suc, "ciudad": ciu}).execute()
                            st.success("Guardado."); st.rerun()
            with c_edit:
                if not df_suc.empty:
                    suc_map = {f"{r['supermercados.nombre_supermercado']} - {r['nombre_sucursal']}": r for _, r in df_suc.iterrows()}
                    sel_suc_edit = st.selectbox("Selecciona Sucursal:", list(suc_map.keys()))
                    suc_data = suc_map[sel_suc_edit]
                    with st.form("suc_edit_form"):
                        esuc_name = st.text_input("Nombre", value=suc_data['nombre_sucursal'] if 'nombre_sucursal' in suc_data else "")
                        eciu = st.text_input("Ciudad", value=suc_data['ciudad'] if 'ciudad' in suc_data else "")
                        b1, b2 = st.columns(2)
                        if b1.form_submit_button("💾 Actualizar"):
                            supabase.table("sucursales").update({"nombre_sucursal": esuc_name, "ciudad": eciu}).eq("id_sucursal", suc_data['id_sucursal']).execute()
                            st.success("Actualizado."); st.rerun()
                        if b2.form_submit_button("🗑️ Borrar"):
                            supabase.table("sucursales").delete().eq("id_sucursal", suc_data['id_sucursal']).execute()
                            st.warning("Borrado."); st.rerun()

# --- SECCIÓN 6: REGISTRAR OFERTAS ---
elif choice == "🏷️ Registrar Ofertas":
    st.title("🏷️ Cargar Ofertas por Catálogo")
    try:
        res_c_of = supabase.table("categorias").select("id_cat, nombre").order("id_cat").execute()
        cat_inv_of = {c['id_cat']: c['nombre'] for c in res_c_of.data} if res_c_of.data else {}
        supers = supabase.table("supermercados").select("*").order("nombre_supermercado").execute()
    except:
        supers, cat_inv_of = None, {}

    if supers and supers.data:
        df_s = pd.DataFrame(supers.
