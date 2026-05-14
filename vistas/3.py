import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONTROL DE VERSIONES SUB-NUMÉRICO MAESTRO ---
VERSION_MODULO = "v3.8.2 - Caja Única Inteligente POS (Modo Híbrido)"

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]

# Desplegamos el título oficial
st.title("📦 Administración de Productos")
st.caption(f"Motor de Clasificación: **{VERSION_MODULO}**")

# 2. CARGA SEGURA DE DICCIONARIOS MAESTROS DESDE EL SERVIDOR
try:
    res_p = supabase.table("productos").select("*").order("nombre").execute()
    lista_productos_maestra = res_p.data if res_p.data else []
    
    res_c = supabase.table("categorias").select("*").order("id_cat").execute()
    cat_dict = {c['nombre']: c['id_cat'] for c in res_c.data} if res_c.data else {}
    cat_inv_dict = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    lista_cat = [c['nombre'] for c in res_c.data] if res_c.data else []

    # Cargamos subcategorías completas una sola vez para evitar consultas repetitivas
    res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()
    lista_subcat_maestra = res_sc.data if res_sc.data else []
    subcat_inv_dict = {sc['id_subcat']: sc['nombre'] for sc in lista_subcat_maestra} if lista_subcat_maestra else {}
except Exception as e:
    st.error(f"Error al conectar con la base de datos: {e}")
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
        except Exception as e: 
            st.warning(f"No se pudo subir la imagen al almacenamiento: {e}")
            return None
    return None

# --- FUNCIÓN DE VALIDACIÓN ANTI-DUPLICADOS ---
def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    if barras and str(barras).strip() != "":
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir: 
            query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
        if res_barras.data: 
            return "barras", res_barras.data

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
                "ID": p.get("id_producto"), 
                "Nombre": p.get("nombre"), 
                "Marca": p.get("marca") or "Sin Marca",
                "Código Barras": p.get("codigo_barras") or "N/A", 
                "Tamaño": p.get("tamano"), 
                "Unidad": p.get("unidad"),
                "Categoría": cat_inv_dict.get(p.get("id_cat"), "Sin Categoría"),
                "Subcategoría": subcat_inv_dict.get(p.get("id_subcat"), "Sin Subcategoría"), 
                "url_imagen": p.get("url_imagen") or ""
            })
        df_mostrar = pd.DataFrame(lista_tabla_limpia)
        st.dataframe(df_mostrar, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
    else: 
        st.info("El catálogo de productos está vacío.")
        
# --- PESTAÑA 2: NUEVO PRODUCTO ---
with t2:
    st.subheader("Formulario de Carga")
    
    # Listas para sugerencias basadas en datos reales de la BD
    lista_nombres_existentes = sorted(list(set([p['nombre'] for p in lista_productos_maestra if p.get('nombre')]))) if lista_productos_maestra else []
    lista_marcas_existentes = sorted(list(set([p['marca'] for p in lista_productos_maestra if p.get('marca') and p['marca'].strip() != ""]))) if lista_productos_maestra else []
    
    # --- FILA DE CONTROL DE ENTRADA INTELIGENTE (HÍBRIDO) ---
    f1_toggle_1, f1_toggle_2 = st.columns(2)
    nuevo_nombre = f1_toggle_1.toggle("📝 ¿Es un Nombre de producto NUEVO?", key="t_new_nom")
    nueva_marca = f1_toggle_2.toggle("🏷️ ¿Es una Marca NUEVA?", key="t_new_mar")

    # --- FILA 1: ASIGNACIÓN DE ENTRADAS DE DATOS ---
    f1_c1, f1_c2 = st.columns(2)
    
    # Lógica inteligente para Nombre
    if nuevo_nombre:
        nombre_final = f1_c1.text_input(
            "Escribe el NUEVO Nombre*", 
            placeholder="Ej: Harina de Trigo Leudante", 
            key="w_nombre_input"
        ).strip()
    else:
        nombre_final = f1_c1.selectbox(
            "Selecciona Nombre del Producto*", 
            options=lista_nombres_existentes, 
            index=None, 
            placeholder="Busca o selecciona el vívere...", 
            key="w_nombre_select"
        )

    # Lógica inteligente para Marca
    if nueva_marca:
        marca_final = f1_c2.text_input(
            "Escribe la NUEVA Marca", 
            placeholder="Ej: Juana", 
            key="w_marca_input"
        ).strip()
    else:
        marca_final = f1_c2.selectbox(
            "Selecciona Marca del Producto", 
            options=lista_marcas_existentes, 
            index=None, 
            placeholder="Busca o selecciona la marca...", 
            key="w_marca_select"
        )

    # --- FILA 2: TAMAÑO Y UNIDAD DE MEDIDA ---
    f2_c1, f2_c2 = st.columns(2)
    tam = f2_c1.number_input("Tamaño / Peso (Sube de 1 en 1 con + y -)", min_value=0.0, step=1.0, value=0.0, key="n_tam")
    uni = f2_c2.selectbox("Unidad de Medida", ["gr", "kg", "ml", "lt", "unidad"], key="n_uni")
    
    # --- FILA 3: CLASIFICACIÓN COMERCIAL JERÁRQUICA ---
    f3_c1, f3_c2 = st.columns(2)
    categoria_sel = f3_c1.selectbox("Categoría Principal (Orden Numérico)", ["--- Seleccionar ---"] + lista_cat, key="n_cat")
    
    # Filtrado local inmediato en memoria basado en la caché inicial
    subcat_opciones = ["--- Seleccionar ---"]
    if categoria_sel != "--- Seleccionar ---":
        id_cat_actual = cat_dict[categoria_sel]
        subcat_opciones += [s['nombre'] for s in lista_subcat_maestra if s.get('id_cat') == id_cat_actual]
        
    subcategoria_sel = f3_c2.selectbox("Subcategoría (Reactiva)", subcat_opciones, key="n_sub")
    
    # --- FILA 4: SKU (CÓDIGO DE BARRAS) Y FOTO ---
    f4_c1, f4_c2 = st.columns(2)
    barras = f4_c1.text_input("Código de Barras (SKU)", key="n_bar", value="", placeholder="Escribe o escanea el código...").strip()
    foto = f4_c2.file_uploader("Foto del Producto (Formatos gráficos)", type=['jpg', 'png', 'jpeg', 'webp'], key="n_foto")
    
    if foto:
        f4_c2.image(foto, caption="Miniatura cargada", width=140)

    st.write("---")
    forzar_guardado = st.checkbox("⚠️ Forzar el registro (Omitir alertas de similitud)", key="n_forzar")

    if st.button("🚀 Guardar Producto en Catálogo", type="primary"):
        if not nombre_final or str(nombre_final).strip() == "":
            st.error("🚨 El campo **Nombre del Producto** es obligatorio.")
        else:
            tipo_error, clon = validar_producto_existente(nombre_final, marca_final, barras, tam, uni)
            
            if tipo_error and not forzar_guardado:
                st.error(f"🚨 CLON DETECTADO: Ya existe un registro para '{clon['nombre']}' marca '{clon['marca']}'.")
            else:
                with st.spinner("Subiendo archivos y registrando producto..."):
                    # 1. Almacenamiento de imagen
                    url_img = subir_a_storage(foto) if foto else None
                    
                    # 2. Obtención de ID de Categoría
                    id_cat_val = cat_dict[categoria_sel] if categoria_sel != "--- Seleccionar ---" else None
                    
                    # 3. Obtención de ID de Subcategoría (Corregida la lectura del arreglo)
                    id_subcat_val = None
                    if subcategoria_sel != "--- Seleccionar ---" and id_cat_val is not None:
                        subcat_encontrada = next((s for s in lista_subcat_maestra if s['nombre'] == subcategoria_sel and s['id_cat'] == id_cat_val), None)
                        if subcat_encontrada:
                            id_subcat_val = subcat_encontrada['id_subcat']

                    # 4. Construcción del Payload final
                    nuevo_producto = {
                        "nombre": nombre_final.strip(),
                        "marca": marca_final.strip() if (marca_final and str(marca_final).strip() != "") else None,
                        "codigo_barras": barras if barras != "" else None,
                        "tamano": float(tam),
                        "unidad": uni,
                        "id_cat": id_cat_val,
                        "id_subcat": id_subcat_val,
                        "url_imagen": url_img
                    }
                    
                    try:
                        res_insert = supabase.table("productos").insert(nuevo_producto).execute()
                        if res_insert.data:
                            st.success(f"🎉 ¡Producto '{nombre_final}' registrado exitosamente!")
                            # Refresco instantáneo de estados para actualizar Pestaña 1
                            st.rerun()
                        else:
                            st.error("No se recibieron datos de validación desde el servidor de base de datos.")
                    except Exception as err_insert:
                        st.error(f"Error crítico de red/inserción en Supabase: {err_insert}")

# --- PESTAÑA 3: EDITAR/BORRAR ---
with t3:
    st.subheader("Modificación de Productos")
    if lista_productos_maestra:
        prod_opciones = {f"{p.get('nombre')} ({p.get('marca') or 'Sin Marca'}) - ID: {p.get('id_producto')}": p for p in lista_productos_maestra}
        prod_seleccionado = st.selectbox("Selecciona el producto a gestionar", options=list(prod_opciones.keys()), index=None)
        
        if prod_seleccionado:
            datos_prod = prod_opciones[prod_seleccionado]
            st.info(f"Registro cargado correctamente. ID del servidor: **{datos_prod.get('id_producto')}**")
    else:
        st.info("No hay productos disponibles en la base de datos para editar.")
