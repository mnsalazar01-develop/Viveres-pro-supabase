import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONTROL DE VERSIONES OFICIAL DE ALTA VELOCIDAD ---
VERSION_MODULO = "v5.0.0 - Búsqueda Bajo Demanda por Letra"

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]

# Cabecera visual estricta para auditar el refresco en Streamlit Cloud
st.title("📦 Administración de Productos")
st.caption(f"Motor de Clasificación: **{VERSION_MODULO}**")

# 2. CARGA DE CATÁLOGOS BASE (Consultas estáticas ligeras para visualización)
try:
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
except:
    cat_dict, cat_inv_dict, lista_cat, subcat_inv_dict = {}, {}, [], {}

# --- FUNCIÓN PARA SUBIR IMÁGENES ---
def subir_a_storage(archivo):
    if archivo:
        try:
            nombre_archivo = f"img_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{archivo.name.replace(' ', '_')}"
            supabase.storage.from_("imagenes").upload(path=nombre_archivo, file=archivo.getvalue(), file_options={"content-type": archivo.type})
            return supabase.storage.from_("imagenes").get_public_url(nombre_archivo)
        except: return None
    return None

# --- FUNCIÓN DE VALIDACIÓN ANTI-DUPLICADOS EN EL BOTÓN ---
def validar_producto_existente(nombre, marca, barras, tamano, unidad):
    if barras and str(barras).strip() != "":
        res_barras = supabase.table("productos").select("*").eq("codigo_barras", barras).execute()
        if res_barras.data: return "barras", res_barras.data

    nom_norm = "".join((nombre or "").lower().split())
    mar_norm = "".join((marca or "").lower().split())
    tam_norm = float(tamano if tamano is not None else 0)
    uni_norm = (unidad or "").lower()
    
    res_textos = supabase.table("productos").select("*").execute()
    if res_textos.data:
        for p in res_textos.data:
            p_nom = "".join((p.get('nombre') or "").lower().split())
            p_mar = "".join((p.get('marca') or "").lower().split())
            p_tam = float(p.get('tamano') or 0)
            p_uni = (p.get('unidad') or "").lower()
            if nom_norm == p_nom and mar_norm == p_mar and tam_norm == p_tam and uni_norm == p_uni:
                return "atributos", p
    return None, None

# 3. INTERFAZ ORGANIZADA POR PESTAÑAS HOMOLOGADAS
t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])

# --- PESTAÑA 1: VER CATÁLOGO ---
with t1:
    try:
        res_p = supabase.table("productos").select("*").order("nombre").execute()
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
    except: df_p = pd.DataFrame()

    if not df_p.empty:
        df_mostrar = df_p.copy()
        if 'id_cat' in df_mostrar.columns: df_mostrar['categoria'] = df_mostrar['id_cat'].map(cat_inv_dict)
        if 'id_subcat' in df_mostrar.columns: df_mostrar['subcategoria'] = df_mostrar['id_subcat'].map(subcat_inv_dict)
        st.dataframe(df_mostrar, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
    else: st.info("El catálogo de productos está vacío.")

# --- PESTAÑA 2: NUEVO PRODUCTO (ESTRATEGIA BAJO DEMANDA v5.0.0) ---
with t2:
    st.subheader("Formulario de Carga")
    
    # --- FILA 1: NOMBRE Y MARCA (ENTRADA LIBRE CON CONSULTA POR LETRA OPCIONAL) ---
    st.markdown("<p style='color: #2bc443; font-weight: bold; margin-bottom: 2px;'>Fila 1: Datos de Identificación</p>", unsafe_allow_html=True)
    f1_c1, f1_c2 = st.columns(2)
    
    with f1_c1:
        # Tu caja de trabajo real: texto plano que nunca se borra con TAB o ENTER
        nombre_final = st.text_input("Nombre del Producto*", key="w_nombre", placeholder="Escribe el nombre aquí...")
        # Consultor bajo demanda: si el usuario escribe una letra, jala las coincidencias en caliente de Supabase
        if nombre_final and len(nombre_final) == 1:
            try:
                res_filtro_n = supabase.table("productos").select("nombre").ilike("nombre", f"{nombre_final}%").execute()
                sug_n = sorted(list(set([p['nombre'] for p in res_filtro_n.data]))) if res_filtro_n.data else []
                if sug_n: st.caption(f"📝 Registrados con '{nombre_final.upper()}': " + ", ".join(sug_n[:10]))
            except: pass

    with f1_c2:
        marca_final = st.text_input("Marca del Producto", key="w_marca", placeholder="Escribe la marca aquí...")
        if marca_final and len(marca_final) == 1:
            try:
                res_filtro_m = supabase.table("productos").select("marca").ilike("marca", f"{marca_final}%").execute()
                sug_m = sorted(list(set([p['marca'] for p in res_filtro_m.data if p.get('marca')]))) if res_filtro_m.data else []
                if sug_m: st.caption(f"🏷️ Marcas con '{marca_final.upper()}': " + ", ".join(sug_m[:10]))
            except: pass

    # --- FILA 2: TAMAÑO Y UNIDAD DE MEDIDA ---
    st.markdown("<p style='color: #2bc443; font-weight: bold; margin-top: 10px; margin-bottom: 2px;'>Fila 2: Contenido Neto</p>", unsafe_allow_html=True)
    f2_c1, f2_c2 = st.columns(2)
    tam = f2_c1.number_input("Tamaño / Peso (Sube de 1 en 1 con + y -)", min_value=0.0, step=1.0, value=0.0, key="n_tam")
    uni = f2_c2.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="n_uni")
    
    # --- FILA 3: CLASIFICACIÓN COMERCIAL JERÁRQUICA ---
    st.markdown("<p style='color: #2bc443; font-weight: bold; margin-top: 10px; margin-bottom: 2px;'>Fila 3: Ubicación en Catálogo</p>", unsafe_allow_html=True)
    f3_c1, f3_c2 = st.columns(2)
    categoria_sel = f3_c1.selectbox("Categoría Principal (Orden Numérico)", ["--- Seleccionar ---"] + lista_cat, key="n_cat")
    
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        id_cat_actual = cat_dict[categoria_sel]
        res_sub_filtradas = supabase.table("subcategorias").select("*").eq("id_cat", id_cat_actual).order("nombre").execute()
        if res_sub_filtradas.data: subcat_opciones += [s['nombre'] for s in res_sub_filtradas.data]
    subcategoria_sel = f3_c2.selectbox("Subcategoría (Reactiva)", subcat_opciones, key="n_sub")
    
    # --- FILA 4: SKU (CÓDIGO DE BARRAS) Y FOTO ---
    st.markdown("<p style='color: #2bc443; font-weight: bold; margin-top: 10px; margin-bottom: 2px;'>Fila 4: Parámetros de Control</p>", unsafe_allow_html=True)
    f4_c1, f4_c2 = st.columns(2)
    barras = f4_c1.text_input("Código de Barras (SKU)", key="n_bar", value="", placeholder="Escribe o escanea el código...").strip()
    foto = f4_c2.file_uploader("Foto del Producto", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
    
    if foto:
        f4_c2.image(foto, caption="Miniatura cargada", width=140)

    st.write("---")
    forzar_guardado = st.checkbox("⚠️ Forzar el registro (Omitir alertas de similitud)", key="n_forzar")

    if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
        print(f"\n=== TERMINAL DE VERIFICACIÓN {VERSION_MODULO} ===")
        print(f"-> Nombre en variable de trabajo: '{nombre_final}' | Marca: '{marca_final}'")
        
        if nombre_final and str(nombre_final).strip() != "":
            tipo_error, clon = validar_producto_existente(nombre_final, marca_final, barras, tam, uni)
            
            if tipo_error and not forzar_guardado:
                st.error(f"🚨 CLON DETECTADO EN EL BOTÓN: Ya existe un registro para '{clon['nombre']}' marca '{clon['marca']}' de ({clon['tamano']} {clon['unidad']}).")
            else:
                url_img = subir_a_storage(foto) if foto else None
                id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                
                id_subcat_val = None
                if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                    try:
                        res_id_sub = supabase.table("subcategorias").select("id_subcat").eq("nombre", subcategoria_sel).eq("id_cat", id_cat_val).execute()
                        if res_id_sub.data and len(res_id_sub.data) > 0:
                            id_subcat_val = res_id_sub.data[0]['id_subcat']
                    except Exception as err_sub:
                        print(f"Advertencia en subcategoría: {err_sub}")
                        id_subcat_val = None

                paquete_datos = {
                    "nombre": str(nombre_final).strip(),
                    "marca": str(marca_final).strip() if marca_final and str(marca_final).strip() != "" else None,
                    "codigo_barras": barras if barras else None,
                    "tamano": float(tam),
                    "unidad": uni,
                    "url_imagen": url_img,
                    "id_cat": id_cat_val,
                    "id_subcat": id_subcat_val
                }
                
                try:
                    supabase.table("productos").insert(paquete_datos).execute()
                    st.success(f"🎉 ¡Producto registrado exitosamente! (Procesado por Motor {VERSION_MODULO})")
                    st.rerun()
                except Exception as servidor_error:
                    st.error(f"🚨 Supabase rechazó el registro debido al siguiente motivo: {servidor_error}")
        else:
            st.warning("El campo 'Nombre del Producto' es obligatorio.")

# --- PESTAÑA 3: MODIFICAR / ELIMINAR ---
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
            err, clon = validar_producto_existente(en, em, eb, et, eu)
            if err and err != "barras" and clon['id_producto'] != p_e['id_producto'] and not f_ed: 
                st.error(f"🚨 DUPLICADO: Conflicto con {clon['nombre']}")
            else:
                n_url = subir_a_storage(ef) if ef else p_e['url_imagen']
                v_c = cat_dict.get(ecat) if ecat != "--- Seleccionar ---" else None
                v_s = None
                if esub != "--- Seleccionar ---" and v_c is not None:
                    try:
                        res_id_sub_e = supabase.table("subcategorias").select("id_subcat").eq("nombre", esub).eq("id_cat", v_c).execute()
                        if res_id_sub_e.data and len(res_id_sub_e.data) > 0:
                            v_s = res_id_sub_e.data[0]['id_subcat']
                    except: v_s = None
                        
                try:
                    supabase.table("productos").update({"nombre": en, "marca": em if em else None, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": n_url, "id_cat": v_c, "id_subcat": v_s}).eq("id_producto", p_e['id_producto']).execute()
                    st.success("¡Cambios guardados!"); st.rerun()
                except Exception as e: st.error(f"Error al actualizar: {e}")
                
        if b_del.button("🗑️ Eliminar Producto Definitivamente"):
            try:
                supabase.table("productos").delete().eq("id_producto", p_e['id_producto']).execute()
                st.warning("Producto eliminado de la base de datos."); st.rerun()
            except Exception as e: st.error(f"No se pudo elminar: {e}")
