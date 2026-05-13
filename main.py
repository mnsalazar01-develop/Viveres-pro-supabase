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

URL_FOTO_DEFECTO = "flaticon.com"

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

# --- FUNCIÓN DE VALIDACIÓN ANTI-DUPLICADOS ---
def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras:
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir:
            query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
        if res_barras.data:
            return "barras", res_barras.data[0]

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
    st.title("🔔 Mis Alertas y Ofertas PRO")
    
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
    except Exception as e:
        st.error(f"Error al conectar con las ofertas: {e}")
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
    st.title("📊 Panel de Inteligencia y Reportes")
    
    # Consulta de ofertas consolidada
    try:
        res_rep = supabase.table("ofertas").select("""
            precio_oferta,
            productos(nombre, marca, id_cat),
            supermercados(nombre_supermercado),
            categorias(nombre)
        """).execute()
    except:
        res_rep = None

    if res_rep and res_rep.data:
        df_rep = pd.json_normalize(res_rep.data)
        
        # Mapeo de categorías por si acaso
        try:
            res_c_map = supabase.table("categorias").select("*").execute()
            map_cat = {c['id_cat']: c['nombre'] for c in res_c_map.data}
            if 'productos.id_cat' in df_rep.columns:
                df_rep['categoria_nombre'] = df_rep['productos.id_cat'].map(map_cat)
        except:
            df_rep['categoria_nombre'] = "General"

        rep_choice = st.sidebar.radio("Selecciona Reporte:", [
            "📉 Ofertas por Producto",
            "🏷️ Ofertas por Marca",
            "🏪 Ofertas por Supermercado",
            "📁 Ofertas por Categoría"
        ])
        
        if rep_choice == "📉 Ofertas por Producto" and 'productos.nombre' in df_rep.columns:
            st.subheader("📉 Distribución de Descuentos por Producto")
            conteos = df_rep['productos.nombre'].value_counts()
            st.bar_chart(conteos)
            st.dataframe(df_rep[['productos.nombre', 'supermercados.nombre_supermercado', 'precio_oferta']].rename(columns={'productos.nombre': 'Producto', 'supermercados.nombre_supermercado': 'Establecimiento', 'precio_oferta': 'Precio'}))
            
        elif rep_choice == "🏷️ Ofertas por Marca" and 'productos.marca' in df_rep.columns:
            st.subheader("🏷️ Cantidad de Ofertas según la Marca")
            conteos_m = df_rep['productos.marca'].value_counts()
            st.bar_chart(conteos_m)
            
        elif rep_choice == "🏪 Ofertas por Supermercado" and 'supermercados.nombre_supermercado' in df_rep.columns:
            st.subheader("🏪 Competitividad por Cadena de Supermercado")
            conteos_s = df_rep['supermercados.nombre_supermercado'].value_counts()
            st.bar_chart(conteos_s)
            
        elif rep_choice == "📁 Ofertas por Categoría":
            st.subheader("📁 Volumen de Promociones por Categoría Principal")
            col_target = 'categoria_nombre' if 'categoria_nombre' in df_rep.columns else 'categorias.nombre'
            if col_target in df_rep.columns:
                conteos_c = df_rep[col_target].value_counts()
                st.bar_chart(conteos_c)
    else:
        st.info("El panel de reportes se activará automáticamente cuando publiques tus primeras ofertas.")

# --- SECCIÓN 3: GESTIÓN DE PRODUCTOS ---
elif choice == "📦 Gestión de Productos":
    st.title("📦 Administración del Catálogo")
    t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])
    
    try:
        res_p = supabase.table("productos").select("*").order("nombre").execute()
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
        
        res_c = supabase.table("categorias").select("*").order("id_cat").execute()
        cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
        cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
        lista_categorias_ordenada = [c['nombre'] for c in res_c.data] if res_c.data else []

        res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
        subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
    except:
        df_p = pd.DataFrame()
        cat_dict = {}
        cat_inv_dict = {}
        subcat_inv_dict = {}
        lista_categorias_ordenada = []

    with t1:
        if not df_p.empty:
            df_mostrar = df_p.copy()
            if 'id_cat' in df_mostrar.columns:
                df_mostrar['categoria'] = df_mostrar['id_cat'].map(cat_inv_dict)
            if 'id_subcat' in df_mostrar.columns:
                df_mostrar['subcategoria'] = df_mostrar['id_subcat'].map(subcat_inv_dict)
            st.dataframe(df_mostrar, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
        else:
            st.info("El catálogo está vacío.")
            
    with t2:
        with st.form("nuevo_p_ordenado", clear_on_submit=True):
            st.subheader("📝 Ficha de Carga")
            col1, col2 = st.columns(2)
            
            nombre = col1.text_input("Nombre del Producto*")
            marca = col2.text_input("Marca")
            barras = col1.text_input("Código de Barras")
            tam = col2.number_input("Tamaño/Peso", min_value=0.0, step=0.1)
            uni = col1.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"])
            foto = col2.file_uploader("Foto", type=['jpg', 'png', 'jpeg', 'webp'])
            
            categoria_sel = col1.selectbox("Categoría Principal", ["--- Seleccionar ---"] + lista_categorias_ordenada)
            
            subcat_opciones = ["--- Seleccionar ---"]
            if categoria_sel != "--- Seleccionar ---":
                id_cat_actual = cat_dict[categoria_sel]
                res_sub_filtradas = supabase.table("subcategorias").select("*").eq("id_cat", id_cat_actual).order("nombre").execute()
                if res_sub_filtradas.data:
                    subcat_opciones += [s['nombre'] for s in res_sub_filtradas.data]
            subcategoria_sel = col1.selectbox("Subcategoría", subcat_opciones)
            
            forzar_guardado = st.checkbox("Forzar el registro si es un clon legítimo")

            if st.form_submit_button("🚀 Guardar Producto"):
                if nombre:
                    tipo_error, clon = validar_producto_existente(nombre, marca, barras, tam, uni)
                    if tipo_error and not forzar_guardado:
                        st.error(f"🚨 DUPLICADO RECHAZADO: Coincide con {clon['nombre']}")
                    else:
                        url_img = subir_a_storage(foto)
                        id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                        id_subcat_val = None
                        if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                            sub_buscar = supabase.table("subcategorias").select("id_subcat").eq("nombre", subcategoria_sel).eq("id_cat", id_cat_val).execute()
                            if sub_buscar.data:
                                id_subcat_val = sub_buscar.data[0]['id_subcat']

                        try:
                            supabase.table("productos").insert({
                                "nombre": nombre, "marca": marca, "codigo_barras": barras if barras else None, 
                                "tamano": tam, "unidad": uni, "url_imagen": url_img, "id_cat": id_cat_val, "id_subcat": id_subcat_val
                            }).execute()
                            st.success("¡Producto guardado exitosamente!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")

    with t3:
        if not df_p.empty:
            # CORRECCIÓN SOLICITADA: SOLO DEJA SELECCIONAR EL PRIMER PRODUCTO DE FORMA ESTABLE
            prod_dict = {f"{p['nombre']} - {p['marca']} ({p['tamano']}{p['unidad']})": p for p in res_p.data}
            lista_seleccion = list(prod_dict.keys())
            
            sel = st.selectbox("Selecciona producto para modificar:", lista_seleccion, key="main_edit_selector")
            p = prod_dict[sel]
            
            # CONTROL DE SESIÓN PARA LA CASCADA DE EDICIÓN
            if "edit_cat_state" not in st.session_state:
                st.session_state.edit_cat_state = cat_inv_dict.get(p['id_cat'], "--- Seleccionar ---")
            
            cat_lista_edicion = ["--- Seleccionar ---"] + lista_categorias_ordenada
            idx_cat_defecto = cat_lista_edicion.index(st.session_state.edit_cat_state) if st.session_state.edit_cat_state in cat_lista_edicion else 0
            
            ecat = st.selectbox("1. Modificar Categoría Principal:", cat_lista_edicion, index=idx_cat_defecto)
            if ecat != st.session_state.edit_cat_state:
                st.session_state.edit_cat_state = ecat
                st.rerun()
                
            subcat_lista_edicion = ["--- Seleccionar ---"]
            if ecat != "--- Seleccionar ---":
                res_sub_edit = supabase.table("subcategorias").select("*").eq("id_cat", cat_dict[ecat]).order("nombre").execute()
                if res_sub_edit.data:
                    subcat_lista_edicion += [s['nombre'] for s in res_sub_edit.data]
            
            subcat_actual_db = subcat_inv_dict.get(p['id_subcat'], "--- Seleccionar ---")
            idx_sub_defecto = subcat_lista_edicion.index(subcat_actual_db) if subcat_actual_db in subcat_lista_edicion else 0
            esubcat = st.selectbox("2. Modificar Subcategoría:", subcat_lista_edicion, index=idx_sub_defecto)
            
            with st.form("edit_p_datos_completos"):
                st.write("3. Ajustar campos complementarios:")
                en = st.text_input("Nombre", p['nombre'])
                em = st.text_input("Marca", p['marca'])
                eb = st.text_input("Código de Barras", p['codigo_barras'] or "").strip()
                et = st.number_input("Tamaño", value=float(p['tamano']) if p['tamano'] else 0.0)
                eu = st.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"], index=["gr", "kg", "ml", "lt", "unidad"].index(p['unidad']) if p['unidad'] in ["gr", "kg", "ml", "lt", "unidad"] else 0)
                ef = st.file_uploader("Cambiar Foto", type=['jpg', 'png', 'jpeg', 'webp'])
                forzar_edit = st.checkbox("Forzar cambios")
                
                c_del, c_upd = st.columns(2)
                
                if c_upd.form_submit_button("💾 Guardar Cambios"):
                    tipo_error, clon = validar_producto_existente(en, em, eb, et, eu, id_excluir=p['id_producto'])
                    if tipo_error and not forzar_edit:
                        st.error(f"🚨 CONFLICTO: Duplicidad con {clon['nombre']}")
                    else:
                        nueva_url = subir_a_storage(ef) if ef else p['url_imagen']
                        id_cat_val = cat_dict[ecat] if ecat != "--- Seleccionar ---" else None
                        id_subcat_val = None
                        if esubcat != "--- Seleccionar ---" and id_cat_val is not None:
                            sub_b = supabase.table("subcategorias").select("id_subcat").eq("nombre", esubcat).eq("id_cat", id_cat_val).execute()
                            if sub_b.data:
                                id_subcat_val = sub_b.data[0]['id_subcat']

                        try:
                            supabase.table("productos").update({
                                "nombre": en, "marca": em, "codigo_barras": eb if eb else None, 
                                "tamano": et, "unidad": eu, "url_imagen": nueva_url, "id_cat": id_cat_val, "id_subcat": id_subcat_val
                            }).eq("id_producto", p['id_producto']).execute()
                            st.success("Cambios aplicados."); st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")
                        
                if c_del.form_submit_button("🗑️ Eliminar Producto"):
                    try:
                        supabase.table("productos").delete().eq("id_producto", p['id_producto']).execute()
                        st.warning("Producto eliminado."); st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo eliminar: {e}")

# --- SECCIÓN 4: ESTRUCTURA (CATEGORÍAS Y SUBCATEGORÍAS) ---
elif choice == "📁 Estructura (Cat/Subcat)":
    st.title("📁 Estructura de Clasificación")
    t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])
    
    try:
        res_c = supabase.table("categorias").select("*").order("id_cat").execute()
        df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()
        cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
        
        res_sc = supabase.table("subcategorias").select("*, categorias(nombre, id_cat)").execute()
        df_sc = pd.json_normalize(res_sc.data) if res_sc.data else pd.DataFrame()
    except:
        df_c = pd.DataFrame()
        df_sc = pd.DataFrame()
        cat_dict = {}

    with t1:
        if not df_sc.empty:
            st.write("📋 Clasificación Jerárquica Registrada (Orden Numérico):")
            df_sc_ordenado = df_sc.sort_values(by='categorias.id_cat')
            df_sc_limpio = df_sc_ordenado.rename(columns={'nombre': 'Subcategoría', 'categorias.nombre': 'Categoría Padre', 'categorias.id_cat': 'N° Cat'})
            st.dataframe(df_sc_limpio[['N° Cat', 'Categoría Padre', 'Subcategoría']], use_container_width=True)
        else:
            st.info("No hay mapeo de subcategorías disponible.")

    with t2:
        with st.form("new_subcat_format"):
            st.subheader("➕ Agregar Nueva Subcategoría")
            if not df_c.empty:
                lista_cat_ord = [c['nombre'] for c in res_c.data]
                cat_padre = st.selectbox("Selecciona Categoría Padre:", lista_cat_ord)
                n_subcat = st.text_input("Nombre de la Subcategoría (Ej: Carnicería)")
                
                if st.form_submit_button("Guardar Subcategoría"):
                    if n_subcat:
                        supabase.table("subcategorias").insert({"nombre": n_subcat, "id_cat": cat_dict[cat_padre]}).execute()
                        st.success("Subcategoría guardada de forma exitosa."); st.rerun()
            else:
                st.warning("Carga las categorías principales antes de definir subcategorías.")

    with t3:
        if not df_sc.empty:
            st.subheader("✏️ Modificar o Eliminar Subcategorías")
            subcat_map = {f"[{r['categorias.nombre']}] - {r['nombre']}": r for _, r in df_sc.iterrows()}
            sel_sub_mod = st.selectbox("Selecciona subcategoría para modificar:", list(subcat_map.keys()))
            sub_d = subcat_map[sel_sub_mod]
            
            with st.form("form_edit_sub"):
                enom_sub = st.text_input("Nombre de la Subcategoría", value=sub_d['nombre'])
                c1, c2 = st.columns(2)
                if c1.form_submit_button("💾 Guardar"):
                    supabase.table("subcategorias").update({"nombre": enom_sub}).eq("id_subcat", sub_d['id_subcat']).execute()
                    st.success("Actualizado."); st.rerun()
                if c2.form_submit_button("🗑️ Eliminar"):
                    supabase.table("subcategorias").delete().eq("id_subcat", sub_d['id_subcat']).execute()
                    st.warning("Eliminado."); st.rerun()

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
        df_s = pd.DataFrame()
        df_suc = pd.DataFrame()

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
        supers = None
        cat_inv_of = {}

    if supers and supers.data:
        df_s = pd.DataFrame(supers.data)
        super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        super_sel = st.selectbox("¿De qué Supermercado es el volante?", list(super_dict.keys()))
        
        try:
            sucs = supabase.table("sucursales").select("*").eq("id_super", super_dict[super_sel]).execute()
        except:
            sucs = None

        suc_dict = {"--- TODAS LAS SUCURSALES ---": None}
        if sucs and sucs.data
