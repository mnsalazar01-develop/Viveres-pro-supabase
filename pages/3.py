import streamlit as st
import pandas as pd
from datetime import datetime

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]
st.title("📦 Administración de Productos")

# 2. CARGA SEGURO DE DICCIONARIOS MAESTROS (Con validación de nulos)
try:
    res_p = supabase.table("productos").select("*").order("nombre").execute()
    df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
    
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    # Guardamos mapeo bidireccional estricto de subcategorías vinculadas a su categoría padre
    subcat_dict = {f"{s['nombre']} (Cat {s['id_cat']})": s['id_subcat'] for s in res_sc.data} if res_sc.data else {}
    subcat_inv_dict = {s['id_subcat']: s['nombre'] for s in res_sc.data} if res_sc.data else {}
except Exception as e:
    st.error(f"Error al cargar datos maestros desde Supabase: {e}")
    df_p = pd.DataFrame()
    cat_dict, cat_inv_dict, lista_cat, subcat_dict, subcat_inv_dict = {}, {}, [], {}, {}

# --- FUNCIÓN PARA SUBIR IMÁGENES ---
def subir_a_storage(archivo):
    if archivo:
        try:
            nombre_archivo = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name.replace(' ', '_')}"
            supabase.storage.from_("imagenes").upload(path=nombre_archivo, file=archivo.getvalue(), file_options={"content-type": archivo.type})
            return supabase.storage.from_("imagenes").get_public_url(nombre_archivo)
        except: return None
    return None

# --- FUNCIÓN DE VALIDACIÓN ANTI-DUPLICADOS ---
def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras:
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir: query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
        if res_barras.data: return "barras", res_barras.data

    query_textos = supabase.table("productos").select("*")
    if id_excluir: query_textos = query_textos.neq("id_producto", id_excluir)
    res_textos = query_textos.execute()
    
    if res_textos.data:
        nom_norm = "".join(nombre.lower().split())
        mar_norm = "".join((marca or "").lower().split())
        tam_norm = float(tamano if tamano is not None else 0)
        uni_norm = unidad.lower()
        for p in res_textos.data:
            if nom_norm == "".join(p['nombre'].lower().split()) and mar_norm == "".join((p['marca'] or "").lower().split()) and tam_norm == float(p['tamano'] or 0) and uni_norm == (p['unidad'] or "").lower():
                return "atributos", p
    return None, None

# 3. INTERFAZ ORGANIZADA POR PESTAÑAS
t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])

# --- PESTAÑA 1: VER CATÁLOGO ---
with t1:
    if not df_p.empty:
        df_mostrar = df_p.copy()
        if 'id_cat' in df_mostrar.columns: df_mostrar['categoria'] = df_mostrar['id_cat'].map(cat_inv_dict)
        if 'id_subcat' in df_mostrar.columns: df_mostrar['subcategoria'] = df_mostrar['id_subcat'].map(subcat_inv_dict)
        st.dataframe(df_mostrar, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
    else: st.info("El catálogo de productos está vacío.")
        
# --- PESTAÑA 2: NUEVO PRODUCTO (CARGA ÁGIL Y CONTROLADA) ---
with t2:
    st.subheader("Formulario de Carga Ágil")
    
    # Selector de autocompletar superior
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
    
    # Precarga controlada de campos básicos
    val_nombre = p_ref.get("nombre", "")
    val_marca = p_ref.get("marca", "")
    val_barras = p_ref.get("codigo_barras", "")
    val_tamano = float(p_ref["tamano"]) if "tamano" in p_ref and p_ref["tamano"] is not None else None
    idx_unidad = ["gr", "kg", "ml", "lt", "unidad"].index(p_ref["unidad"]) if "unidad" in p_ref and p_ref["unidad"] in ["gr", "kg", "ml", "lt", "unidad"] else 0
    
    # Renderizado secuencial solicitado
    c1, c2 = st.columns(2)
    nombre = c1.text_input("Nombre del Producto*", value=val_nombre, key="n_nom")
    marca = c2.text_input("Marca", value=val_marca, key="n_mar")
    barras = c1.text_input("Código de Barras", value=val_barras, key="n_bar").strip()
    tam = c2.number_input("Tamaño / Peso (Sube de 1 en 1)", min_value=0.0, step=1.0, value=val_tamano, key="n_tam")
    uni = c1.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], index=idx_unidad, key="n_uni")
    foto = c2.file_uploader("Foto del Producto", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
    
    # Selectores jerárquicos colocados estrictamente al final
    cat_actual_auto = cat_inv_dict.get(p_ref.get("id_cat"), "--- Seleccionar ---")
    l_cat_f = ["--- Seleccionar ---"] + lista_cat
    idx_c_f = l_cat_f.index(cat_actual_auto) if cat_actual_auto in l_cat_f else 0
    categoria_sel = c1.selectbox("Categoría Principal", l_cat_f, index=idx_c_f, key="n_cat")
    
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        id_cat_actual = cat_dict[categoria_sel]
        res_sub_filtradas = supabase.table("subcategorias").select("*").eq("id_cat", id_cat_actual).order("nombre").execute()
        if res_sub_filtradas.data: subcat_opciones += [s['nombre'] for s in res_sub_filtradas.data]
        
    subcat_actual_auto = subcat_inv_dict.get(p_ref.get("id_subcat"), "--- Seleccionar ---")
    idx_sc_f = subcat_opciones.index(subcat_actual_auto) if subcat_actual_auto in subcat_opciones else 0
    subcategoria_sel = c2.selectbox("Subcategoría", subcat_opciones, index=idx_sc_f, key="n_sub")
    
    forzar_guardado = st.checkbox("⚠️ Forzar el registro (Ignorar alertas de similitud)", key="n_forzar")

    if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
        if nombre:
            tipo_error, clon = validar_producto_existente(nombre, marca, barras, tam, uni)
            if tipo_error and not forzar_guardado:
                st.error(f"🚨 CLON DETECTADO: Coincide con '{clon['nombre']}' de la marca '{clon['marca']}'.")
            else:
                url_img = subir_a_storage(foto) if foto else (p_ref.get("url_imagen") if not es_nuevo else None)
                id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                
                # EXTRACCIÓN MAESTRA DEL ID DE SUBCATEGORÍA (Mapeo numérico estricto)
                id_subcat_val = None
                if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                    res_id_sub = supabase.table("subcategorias").select("id_subcat").eq("nombre", subcategoria_sel).eq("id_cat", id_cat_val).execute()
                    if res_id_sub.data:
                        id_subcat_val = res_id_sub.data[0]['id_subcat']

                # Estructuramos el diccionario final limpiando campos vacíos
                paquete_datos = {
                    "nombre": nombre,
                    "marca": marca if marca else None,
                    "codigo_barras": barras if barras else None,
                    "tamano": float(tam) if tam is not None else None,
                    "unidad": uni,
                    "url_imagen": url_img,
                    "id_cat": id_cat_val,
                    "id_subcat": id_subcat_val
                }

                try:
                    supabase.table("productos").insert(paquete_datos).execute()
                    st.success("🎉 ¡Producto registrado exitosamente en la base de datos!")
                    st.rerun()
                except Exception as servidor_error:
                    st.error("🚨 Supabase rechazó el registro debido al siguiente error de base de datos:")
                    st.info(f"**Mensaje del Servidor:** {servidor_error}")
                    with st.expander("Ver estructura de datos enviada"):
                        st.json(paquete_datos)
        else: st.warning("El campo 'Nombre' es obligatorio.")

# --- PESTAÑA 3: MODIFICAR / ELIMINAR (UN PRODUCTO A LA VEZ) ---
with t3:
    if not df_p.empty:
        st.subheader("Gestión de un Producto Individual")
        prod_dict_e = {f"{p['nombre']} - {p['marca'] or 'Sin Marca'} ({p['tamano'] or 0}{p['unidad'] or ''})": p for p in res_p.data}
        sel_e = st.selectbox("Selecciona el producto específico que deseas modificar o eliminar:", list(prod_dict_e.keys()), key="s_e_p")
        p_e = prod_dict_e[sel_e]
        
        st.write("---")
        ec1, ec2 = st.columns(2)
        en = ec1.text_input("Modificar Nombre", p_e['nombre'])
        em = ec2.text_input("Modificar Marca", p_e['marca'] or "")
        eb = ec1.text_input("Modificar Código de Barras", p_e['codigo_barras'] or "").strip()
        et = ec2.number_input("Modificar Tamaño (Paso entero)", value=float(p_e['tamano']) if p_e['tamano'] else 0.0, step=1.0)
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
                if esub != "--- Seleccionar ---" and v_c is not None:
                    res_id_sub_e = supabase.table("subcategorias").select("id_subcat").eq("nombre", esub).eq("id_cat", v_c).execute()
                    if res_id_sub_e.data:
                        v_s = res_id_sub_e.data[0]['id_subcat']
                        
                try:
                    supabase.table("productos").update({"nombre": en, "marca": em if em else None, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": n_url, "id_cat": v_c, "id_subcat": v_s}).eq("id_producto", p_e['id_producto']).execute()
                    st.success("¡Cambios guardados!"); st.rerun()
                except Exception as e: st.error(f"Error al actualizar: {e}")
                
        if b_del.button("🗑️ Eliminar Producto Definitivamente"):
            try:
                supabase.table("productos").delete().eq("id_producto", p_e['id_producto']).execute()
                st.warning("Producto eliminado de la base de datos."); st.rerun()
            except Exception as e: st.error(f"No se pudo eliminar: {e}")
    else: st.info("El catálogo está vacío.")
