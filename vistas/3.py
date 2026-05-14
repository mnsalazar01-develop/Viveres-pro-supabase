import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONTROL DE VERSIONES ARQUITECTURA LIMPIA ---
VERSION_MODULO = "v3.5.0 - Control y Backend Aislados"

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]

# Encabezado con subnúmero de versión estricto para check visual
st.title("📦 Administración de Productos")
st.caption(f"Motor de Clasificación: **{VERSION_MODULO}**")

# 2. CAPA DE BACKEND AISLADA: CARGA PASIVA DE MEMORIA (DICCIONARIOS NATIVOS)
# No operamos sobre los widgets; extraemos los datos a estructuras de lectura estáticas
@st.cache_data(ttl=60)
def cargar_datos_maestros_aislados():
    try:
        res_p = supabase.table("productos").select("*").order("nombre").execute()
        lista_p = res_p.data if res_p.data else []
        
        res_c = supabase.table("categorias").select("*").order("id_cat").execute()
        c_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
        c_inv = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
        l_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

        res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
        sc_inv = {sc['id_subcat']: sc['nombre'] for sc in res_sc.data} if res_sc.data else {}
        
        return lista_p, c_dict, c_inv, l_cat, sc_inv
    except:
        return [], {}, {}, [], {}

# Ejecutamos la carga pasiva de backend en variables de trabajo independientes
lista_productos_maestra, cat_dict, cat_inv_dict, lista_cat, subcat_inv_dict = cargar_datos_maestros_aislados()

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
    print(f"\n[CHECK {VERSION_MODULO}] Ejecutando validación en capa lógica de backend...")
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

# 3. CAPA DE INTERFAZ (WIDGETS PASIVOS DE CAPTURA)
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

# --- PESTAÑA 2: NUEVO PRODUCTO (SEPARACIÓN TOTAL CONTROL-BACKEND) ---
with t2:
    st.subheader("Formulario de Carga")
    
    # --- FILA 1: NOMBRE Y MARCA (CONTROLES PASIVOS, NO SE BORRAN CON TAB/ENTER) ---
    f1_c1, f1_c2 = st.columns(2)
    # Widgets de entrada independientes de la base de datos para retener el texto escrito libremente
    nombre_capturado = f1_c1.text_input("Nombre del Producto*", key="w_nombre", placeholder="Escribe el nombre del vívere...")
    marca_capturada = f1_c2.text_input("Marca del Producto", key="w_marca", placeholder="Escribe la marca comercial...")

    # --- FILA 2: TAMAÑO Y UNIDAD DE MEDIDA ---
    f2_c1, f2_c2 = st.columns(2)
    # Iniciamos en 0.0 para que el incremento de unidades esté habilitado de arranque en pasos enteras de 1.0
    tam_capturado = f2_c1.number_input("Tamaño / Peso (Botones de 1 en 1)", min_value=0.0, step=1.0, value=0.0, key="w_tamano")
    uni_capturada = f2_c2.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="w_unidad")
    
    # --- FILA 3: CLASIFICACIÓN JERÁRQUICA COMERCIAL ---
    f3_c1, f3_c2 = st.columns(2)
    categoria_sel = f3_c1.selectbox("Categoría Principal (Orden Numérico)", ["--- Seleccionar ---"] + lista_cat, key="w_categoria")
    
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        id_cat_actual = cat_dict.get(categoria_sel)
        if id_cat_actual is not None:
            # Buscamos de forma aislada en la memoria maestra cargada por el backend
            subcat_opciones += [s['nombre'] for s in subcat_inv_dict.values() if s == categoria_sel or any(p.get('id_cat') == id_cat_actual for p in lista_productos_maestra)]
            # Refrescamos las opciones basándonos en la relación jerárquica limpia de Supabase
            try:
                res_sub_filtradas = supabase.table("subcategorias").select("*").eq("id_cat", id_cat_actual).order("nombre").execute()
                if res_sub_filtradas.data:
                    subcat_opciones = ["--- Seleccionar ---"] + [s['nombre'] for s in res_sub_filtradas.data]
            except: pass
    subcategoria_sel = f3_c2.selectbox("Subcategoría", subcat_opciones, key="w_subcategoria")
    
    # --- FILA 4: IDENTIFICACIÓN (SKU) Y FOTO MULTIMEDIA ---
    f4_c1, f4_c2 = st.columns(2)
    barras_capturadas = f4_c1.text_input("Código de Barras (SKU)", key="w_barras", placeholder="Escribe o escanea el código de barras...").strip()
    foto_capturada = f4_c2.file_uploader("Foto del Producto (Formatos de imagen)", type=['jpg', 'png', 'jpeg', 'webp'], key="w_foto")
    
    # Miniatura pequeña y elegante (width=140) aislada en su columna multimedia
    if foto_capturada:
        f4_c2.image(foto_capturada, caption="Miniatura cargada", width=140)

    st.write("---")
    forzar_guardado = st.checkbox("⚠️ Forzar el registro (Ignorar alertas de similitud)", key="w_forzar")

    # --- PROCESAMIENTO EXCLUSIVO EN EL BOTÓN (BACKEND LÓGICO COMPLETO) ---
    if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
        # Impresiones de verificación en consola (Check de variables de trabajo aisladas)
        print(f"\n=== TERMINAL DE CONTROL (Motor {VERSION_MODULO}) ===")
        print(f"-> Control Visual Nombre: '{nombre_capturado}'")
        print(f"-> Control Visual Marca: '{marca_capturada}'")
        print(f"-> Tamaño: {tam_capturado} | Unidad: {uni_capturada}")
        
        if nombre_capturado and str(nombre_capturado).strip() != "":
            # El escudo procesa los textos estáticos recolectados
            tipo_error, clon = validar_producto_existente(nombre_capturado, marca_capturada, barras_capturadas, tam_capturado, uni_capturada)
            
            if tipo_error and not forzar_guardado:
                print(f"[CHECK {VERSION_MODULO}] Guardado rechazado: Conflicto de atributos detectado.")
                st.error(f"🚨 CLON DETECTADO EN EL BOTÓN: Ya existe un registro para '{clon['nombre']}' marca '{clon['marca']}'.")
            else:
                # El backend procesa las conversiones de IDs fuera de los controles gráficos
                url_img = subir_a_storage(foto_capturada) if foto_capturada else None
                id_cat_val = cat_dict.get(categoria_sel) if categoria_sel != "--- Seleccionar ---" else None
                
                id_subcat_val = None
                if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                    try:
                        res_id_sub = supabase.table("subcategorias").select("id_subcat").eq("nombre", subcategoria_sel).eq("id_cat", id_cat_val).execute()
                        if res_id_sub.data and len(res_id_sub.data) > 0:
                            id_subcat_val = res_id_sub.data[0].get('id_subcat')
                    except Exception as err_sub:
                        print(f"[CHECK {VERSION_MODULO}] Advertencia en subcategoría: {err_sub}")
                        id_subcat_val = None

                # Empaquetado final de variables de trabajo independientes
                paquete_datos = {
                    "nombre": str(nombre_capturado).strip(),
                    "marca": str(marca_capturada).strip() if marca_capturada and str(marca_capturada).strip() != "" else None,
                    "codigo_barras": barras_capturadas if barras_capturadas else None,
                    "tamano": float(tam_capturado),
                    "unidad": uni_capturada,
                    "url_imagen": url_img,
                    "id_cat": id_cat_val,
                    "id_subcat": id_subcat_val
                }
                
                print(f"[CHECK {VERSION_MODULO}] Enviando paquete de backend a Supabase: {paquete_datos}")

                try:
                    supabase.table("productos").insert(paquete_datos).execute()
                    print(f"[CHECK {VERSION_MODULO}] ¡Inserción completada de forma exitosa en el servidor!")
                    st.success(f"🎉 ¡Producto registrado exitosamente! (Procesado por Motor {VERSION_MODULO})")
                    st.rerun()
                except Exception as servidor_error:
                    print(f"[CHECK {VERSION_MODULO}] Error al insertar en Supabase: {servidor_error}")
                    st.error(f"🚨 Supabase rechazó el registro debido al siguiente motivo: {servidor_error}")
        else:
            st.warning("El campo 'Nombre del Producto' es obligatorio para procesar el guardado.")

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
            except Exception as e: st.error(f"No se pudo eliminar: {e}")
    else: st.info("El catálogo está vacío.")
