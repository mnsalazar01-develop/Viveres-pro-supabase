import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONTROL DE VERSIONES ARQUITECTURA POS PROFESIONAL ---
VERSION_MODULO = "v10.2.0 - Limpieza Absoluta Post-Guardado"

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]

# Cabecera oficial para verificar la actualización visual en pantalla
st.title("📦 Administración de Productos")
st.caption(f"Motor de Clasificación: **{VERSION_MODULO}**")

# 2. CARGA DE BASE DE DATOS MAESTRA (BACKEND LIGERO)
try:
    res_p = supabase.table("productos").select("*").order("nombre").execute()
    lista_productos_maestra = res_p.data if res_p.data else []
    
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    lista_subcat_maestra = res_sc.data if res_sc.data else []
    subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
except:
    lista_productos_maestra = []
    lista_subcat_maestra = []
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

# --- FUNCIÓN DE VALIDACIÓN ANTI-DUPLICADOS ---
def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras and str(barras).strip() != "":
        res_barras = supabase.table("productos").select("*").eq("codigo_barras", barras).execute()
        if res_barras.data: return "barras", res_barras.data

    if lista_productos_maestra:
        nom_norm = "".join((nombre or "").lower().split())
        mar_norm = "".join((marca or "").lower().split())
        tam_norm = float(tamano if tamano is not None else 0)
        uni_norm = (unidad or "").lower()
        
        for p in lista_productos_maestra:
            if id_excluir and p.get('id_producto') == id_excluir:
                continue
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
    if lista_productos_maestra:
        lista_tabla_limpia = []
        for p in lista_productos_maestra:
            lista_tabla_limpia.append({
                "ID": p.get("id_producto"), "Nombre": p.get("nombre"), "Marca": p.get("marca") or "Sin Marca",
                "Código Barras": p.get("codigo_barras") or "N/A", "Tamaño": p.get("tamano"), "Unidad": p.get("unidad"),
                "Categoría": cat_inv_dict.get(p.get("id_cat"), "Sin Categoría"),
                "Subcategoría": subcat_inv_dict.get(p.get("id_subcat"), "Sin Subcategoría"), "url_imagen": p.get("url_imagen") or ""
            })
        df_mostrar = pd.DataFrame(lista_tabla_limpia)
        st.dataframe(df_mostrar, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
    else: st.info("El catálogo de productos está vacío.")

# --- PESTAÑA 2: NUEVO PRODUCTO (SISTEMA ASISTIDO POS v10.2.0) ---
with t2:
    st.subheader("Formulario de Carga Ágil")
    
    lista_nombres_existentes = sorted(list(set([p['nombre'] for p in lista_productos_maestra if p.get('nombre')]))) if lista_productos_maestra else []
    lista_marcas_existentes = sorted(list(set([p['marca'] for p in lista_productos_maestra if p.get('marca') and p['marca'].strip() != ""]))) if lista_productos_maestra else []
    
    # --- FILA 1: NOMBRE DEL PRODUCTO ---
    st.markdown("### 🛒 1. Nombre del Artículo")
    f1_c1, f1_c2 = st.columns(2)
    
    with f1_c1:
        s_nom_lookup = f1_c1.selectbox("🔍 Buscar Nombre registrado (Opcional):", ["--- Es un Nombre Nuevo ---"] + lista_nombres_existentes, key="lk_nom")
        val_def_nombre = "" if s_nom_lookup == "--- Es un Nombre Nuevo ---" else s_nom_lookup
    with f1_c2:
        nombre_final = f1_c2.text_input("✍️ Caja de Trabajo: Digita o edita el Nombre*", value=val_def_nombre, key="w_nombre", placeholder="Escribe el nombre aquí...")

    st.write("---")
    # --- FILA 2: MARCA DEL PRODUCTO ---
    st.markdown("### 🏷️ 2. Marca Comercial")
    f2_c1, f2_c2 = st.columns(2)
    
    with f2_c1:
        s_mar_lookup = f2_c1.selectbox("🔍 Buscar Marca registrada (Opcional):", ["--- Es una Marca Nueva ---"] + lista_marcas_existentes, key="lk_mar")
        val_def_marca = "" if s_mar_lookup == "--- Es una Marca Nueva ---" else s_mar_lookup
    with f2_c2:
        marca_final = f2_c2.text_input("✍️ Caja de Trabajo: Digita o edita la Marca", value=val_def_marca, key="w_marca", placeholder="Escribe la marca aquí...")

    st.write("---")
    # --- FILA 3: TAMAÑO Y UNIDAD DE MEDIDA ---
    st.markdown("### 📏 3. Contenido Neto")
    f3_c1, f3_c2 = st.columns(2)
    tam = f3_c1.number_input("Tamaño / Peso (Sube de 1 en 1 con + y -)", min_value=0.0, step=1.0, value=0.0, key="n_tam")
    uni = f3_c2.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="n_uni")
    
    st.write("---")
    # --- FILA 4: CLASIFICACIÓN COMERCIAL JERÁRQUICA ---
    st.markdown("### 🗂️ 4. Clasificación Jerárquica")
    f4_c1, f4_c2 = st.columns(2)
    categoria_sel = f4_c1.selectbox("Categoría Principal (Orden Numérico)", ["--- Seleccionar ---"] + lista_cat, key="n_cat")
    
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        id_cat_actual = cat_dict[categoria_sel]
        subcat_opciones += [sc['nombre'] for sc in lista_subcat_maestra if sc.get('id_cat') == id_cat_actual]
    subcategoria_sel = f4_c2.selectbox("Subcategoría (Reactiva)", subcat_opciones, key="n_sub")
    
    st.write("---")
    # --- FILA 5: SKU (CÓDIGO DE BARRAS) Y FOTO MULTIMEDIA ---
    st.markdown("### 🔍 5. Parámetros de Control")
    f5_c1, f5_c2 = st.columns(2)
    barras = f5_c1.text_input("Código de Barras (SKU)", key="n_bar", value="", placeholder="Escribe o escanea el código...").strip()
    foto = f5_c2.file_uploader("Foto del Producto", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
    
    if foto:
        st.image(foto, caption="Miniatura cargada", width=140)

    st.write("---")
    forzar_guardado = st.checkbox("⚠️ Forzar el registro (Omitir alertas de similitud)", key="n_forzar")

    # --- CAPA DE PROCESAMIENTO INTERNO EN EL BOTÓN ---
    if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
        str_nombre = str(nombre_final).strip() if nombre_final is not None else ""
        str_marca = str(marca_final).strip() if marca_final is not None else ""
        
        if str_nombre != "":
            tipo_error, clon = validar_producto_existente(str_nombre, str_marca, barras, tam, uni)
            
            if tipo_error and not forzar_guardado:
                st.error(f"🚨 CLON DETECTADO EN EL BOTÓN: Ya existe un registro para '{clon['nombre']}' marca '{clon['marca']}'.")
            else:
                url_img = subir_a_storage(foto) if foto else None
                id_cat_val = cat_dict.get(categoria_sel) if categoria_sel != "--- Seleccionar ---" else None
                
                id_subcat_val = None
                if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                    for sc in lista_subcat_maestra:
                        if sc.get('nombre') == subcategoria_sel and sc.get('id_cat') == id_cat_val:
                            id_subcat_val = sc.get('id_subcat')
                            break

                paquete_datos = {
                    "nombre": str_nombre, "marca": str_marca if str_marca != "" else None, "codigo_barras": barras if barras else None,
                    "tamano": float(tam), "unidad": uni, "url_imagen": url_img, "id_cat": id_cat_val, "id_subcat": id_subcat_val
                }

                try:
                    supabase.table("productos").insert(paquete_datos).execute()
                    
                    # --- CORRECCIÓN INTEGRADA v10.2.0: VACIADO FORZADO DE MEMORIA DE INTERFAZ ---
                    # Eliminamos los estados guardados de los widgets para que arranquen limpios en blanco en la recarga
                    claves_a_limpiar = ["lk_nom", "w_nombre", "lk_mar", "w_marca", "n_tam", "n_uni", "n_cat", "n_sub", "n_bar", "n_foto"]
                    for k in claves_a_limpiar:
                        if k in st.session_state:
                            del st.session_state[k]
                            
                    st.success(f"🎉 ¡Producto registrado exitosamente! (Procesado por Motor {VERSION_MODULO})")
                    st.rerun()
                except Exception as servidor_error:
                    st.error(f"🚨 Supabase rechazó el registro debido al siguiente motivo: {servidor_error}")
        else:
            st.warning("El campo 'Caja de Trabajo: Nombre del Producto' es obligatorio.")

# --- PESTAÑA 3: MODIFICAR / ELIMINAR ---
with t3:
    if lista_productos_maestra:
        st.subheader("Gestión de un Producto Individual")
        prod_dict_e = {f"{p['nombre']} - {p['marca'] or 'Sin Marca'} ({p['tamano'] or 0}{p['unidad'] or ''})": p for p in lista_productos_maestra}
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
            id_cat_mod = cat_dict.get(ecat)
            l_sub_e += [sc['nombre'] for sc in lista_subcat_maestra if sc.get('id_cat') == id_cat_mod]
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
                    for sc in lista_subcat_maestra:
                        if sc.get('nombre') == esub and sc.get('id_cat') == v_c:
                            v_s = sc.get('id_subcat')
                            break
                        
                try:
                    supabase.table("productos").update({"nombre": en, "marca": em if em else None, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": n_url, "id_cat": v_c, "id_subcat": v_s}).eq("id_producto", p_e['id_producto']).execute()
                    st.success("¡Cambios guardados!"); st.rerun()
                except Exception as e: st.error(f"Error al actualizar: {e}")
                
        if b_del.button("🗑️ Eliminar Producto Definitivamente"):
            try:
                supabase.table("productos").delete().eq("id_producto", p_e['id_producto']).execute()
                st.warning("Producto eliminado de la base de datos."); st.rerun()
            except Exception as e: st.error(f"No se pudo elminar: {e}")
    else: st.info("El catálogo está vacío.")
