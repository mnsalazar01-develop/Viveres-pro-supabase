import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONTROL DE VERSIONES OFICIAL ---
VERSION_MODULO = "v3.6.0 - Arquitectura Cajas Espejo POS"

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]

# Encabezado con versión visible para auditoría en tiempo real
st.title("📦 Administración de Productos")
st.caption(f"Motor de Clasificación: **{VERSION_MODULO}**")

# 2. CARGA SEGURA DE RECONOCIMIENTO DESDE EL SERVIDOR (BACKEND)
try:
    res_p = supabase.table("productos").select("*").order("nombre").execute()
    lista_productos_maestra = res_p.data if res_p.data else []
    
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
except:
    lista_productos_maestra = []
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
    print(f"\n[CHECK {VERSION_MODULO}] Evaluando duplicados en la capa lógica...")
    if barras and str(barras).strip() != "":
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir: query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
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

# --- PESTAÑA 2: NUEVO PRODUCTO (ARQUITECTURA CAJAS ESPEJO POS v3.6.0) ---
with t2:
    st.subheader("Formulario de Carga")
    
    lista_nombres_existentes = sorted(list(set([p['nombre'] for p in lista_productos_maestra if p.get('nombre')]))) if lista_productos_maestra else []
    lista_marcas_existentes = sorted(list(set([p['marca'] for p in lista_productos_maestra if p.get('marca') and p['marca'].strip() != ""]))) if lista_productos_maestra else []
    
    # --- FILA 1: NOMBRE (Buscador Predictivo + Caja de Trabajo Independiente) ---
    st.markdown("### 🛒 Identificación del Vívere")
    f1_c1, f1_c2 = st.columns(2)
    
    s_nom_scroll = f1_c1.selectbox("🔍 1. Buscar en Nombres existentes:", ["--- Es un Nombre Nuevo ---"] + lista_nombres_existentes, key="scroll_n")
    val_def_nombre = "" if s_nom_scroll == "--- Es un Nombre Nuevo ---" else s_nom_scroll
    # Esta es tu caja de trabajo real: es texto plano estático, nunca se borrará con TAB o ENTER
    nombre_final = f1_c1.text_input("✍️ Caja de Trabajo: Nombre del Producto*", value=val_def_nombre, key="w_nombre", placeholder="Escribe o edita el nombre aquí...")

    # --- FILA 2: MARCA (Buscador Predictivo + Caja de Trabajo Independiente) ---
    s_mar_scroll = f1_c2.selectbox("🔍 2. Buscar en Marcas existentes:", ["--- Es una Marca Nueva ---"] + lista_marcas_existentes, key="scroll_m")
    val_def_marca = "" if s_mar_scroll == "--- Es una Marca Nueva ---" else s_mar_scroll
    # Esta es tu caja de trabajo real para la marca
    marca_final = f1_c2.text_input("✍️ Caja de Trabajo: Marca del Producto", value=val_def_marca, key="w_marca", placeholder="Escribe o edita la marca aquí...")

    st.write("---")
    # --- FILA 3: TAMAÑO Y UNIDAD DE MEDIDA ---
    st.markdown("### 📏 Dimensiones y Contenido")
    f2_c1, f2_c2 = st.columns(2)
    tam = f2_c1.number_input("Tamaño / Peso (Sube de 1 en 1 con + y -)", min_value=0.0, step=1.0, value=0.0, key="n_tam")
    uni = f2_c2.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="n_uni")
    
    st.write("---")
    # --- FILA 4: CLASIFICACIÓN JERÁRQUICA COMERCIAL ---
    st.markdown("### 🗂️ Clasificación Comercial")
    f3_c1, f3_c2 = st.columns(2)
    categoria_sel = f3_c1.selectbox("Categoría Principal (Orden Numérico)", ["--- Seleccionar ---"] + lista_cat, key="n_cat")
    
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        id_cat_actual = cat_dict[categoria_sel]
        res_sub_filtradas = supabase.table("subcategorias").select("*").eq("id_cat", id_cat_actual).order("nombre").execute()
        if res_sub_filtradas.data: subcat_opciones += [s['nombre'] for s in res_sub_filtradas.data]
    subcategoria_sel = f3_c2.selectbox("Subcategoría (Reactiva)", subcat_opciones, key="n_sub")
    
    st.write("---")
    # --- FILA 5: CÓDIGO DE BARRAS (SKU) Y FOTO ---
    st.markdown("### 🏷️ Identificación Única y Multimedia")
    f4_c1, f4_c2 = st.columns(2)
    barras = f4_c1.text_input("Código de Barras (SKU)", key="n_bar", placeholder="Escribe o escanea el código aquí...").strip()
    foto = f4_c2.file_uploader("Foto del Producto (Formatos gráficos)", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
    
    if foto:
        f4_c2.image(foto, caption="Miniatura cargada", width=140)

    st.write("---")
    forzar_guardado = st.checkbox("⚠️ Forzar el registro (Ignorar alertas de similitud)", key="n_forzar")

    # --- PROCESAMIENTO EXCLUSIVO EN EL BOTÓN ---
    if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
        print(f"\n=== TERMINAL DE VERIFICACIÓN (Motor {VERSION_MODULO}) ===")
        print(f"-> Caja de Trabajo Nombre Leyendo: '{nombre_final}'")
        print(f"-> Caja de Trabajo Marca Leyendo: '{marca_final}'")
        print(f"-> Tamaño: {tam} | Unidad: {uni}")
        
        if nombre_final and str(nombre_final).strip() != "":
            tipo_error, clon = validar_producto_existente(nombre_final, marca_final, barras, tam, uni)
            
            if tipo_error and not forzar_guardado:
                print(f"[CHECK {VERSION_MODULO}] Registro bloqueado por similitud.")
                st.error(f"🚨 CLON DETECTADO EN EL BOTÓN: Ya existe un registro para '{clon['nombre']}' marca '{clon['marca']}'.")
            else:
                url_img = subir_a_storage(foto) if foto else None
                id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                
                id_subcat_val = None
                if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                    try:
                        res_id_sub = supabase.table("subcategorias").select("id_subcat").eq("nombre", subcategoria_sel).eq("id_cat", id_cat_val).execute()
                        if res_id_sub.data and len(res_id_sub.data) > 0:
                            # Extracción indexada posicional de backend pura
                            id_subcat_val = res_id_sub.data[0]['id_subcat']
                    except Exception as err_sub:
                        print(f"[CHECK {VERSION_MODULO}] Advertencia en subcategoría: {err_sub}")
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
                
                print(f"[CHECK {VERSION_MODULO}] Enviando paquete a base de datos: {paquete_datos}")

                try:
                    supabase.table("productos").insert(paquete_datos).execute()
                    print(f"[CHECK {VERSION_MODULO}] ¡Inserción completada con éxito!")
                    st.success(f"🎉 ¡Producto registrado exitosamente! (Procesado por Motor {VERSION_MODULO})")
                    st.rerun()
                except Exception as servidor_error:
                    print(f"[CHECK {VERSION_MODULO}] Error en Supabase: {servidor_error}")
                    st.error(f"🚨 Supabase rechazó el registro debido al siguiente motivo: {servidor_error}")
        else:
            st.warning("El campo 'Caja de Trabajo: Nombre del Producto' es obligatorio.")

# --- PESTAÑA 3: MODIFICAR / ELIMINAR ---
with t3:
    if not df_p.empty:
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
    else: st.info("El catálogo está vacío.")
