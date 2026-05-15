import streamlit as st
import pandas as pd
from datetime import datetime

VERSION_MODULO = "v20.0.0 - Nueva Via"

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
UNIDADES = ["gr", "kg", "ml", "lt", "unidad"]
PLACEHOLDER_CAT = "--- Seleccionar ---"
IMG_TIPOS = ["jpg", "png", "jpeg", "webp"]


# ─────────────────────────────────────────────
# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL
# ─────────────────────────────────────────────
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa al inicio de la aplicación.")
    st.stop()

supabase = st.session_state["supabase"]

st.title("📦 Administración de Productos")
st.caption(f"Motor: **{VERSION_MODULO}**")

if "pos_form_counter" not in st.session_state:
    st.session_state["pos_form_counter"] = 0


# ─────────────────────────────────────────────
# 2. CARGA DE DATOS CON CACHÉ (evita re-queries en cada interacción)
# ─────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def cargar_datos():
    """Carga productos, categorías y subcategorías desde Supabase."""
    try:
        res_p  = supabase.table("productos").select("*").order("nombre").execute()
        res_c  = supabase.table("categorias").select("*").order("id_cat").execute()
        res_sc = supabase.table("subcategorias").select("*").order("nombre").execute()

        productos   = res_p.data  or []
        categorias  = res_c.data  or []
        subcat_list = res_sc.data or []

        cat_dict     = {c["nombre"]: c["id_cat"]  for c in categorias}
        cat_inv_dict = {c["id_cat"]: c["nombre"]  for c in categorias}
        lista_cat    = [c["nombre"]               for c in categorias]
        subcat_inv_dict = {sc["id_subcat"]: sc["nombre"] for sc in subcat_list}

        return productos, cat_dict, cat_inv_dict, lista_cat, subcat_list, subcat_inv_dict

    except Exception as e:
        st.warning(f"No se pudieron cargar los datos maestros: {e}")
        return [], {}, {}, [], [], {}


lista_productos_maestra, cat_dict, cat_inv_dict, lista_cat, lista_subcat_maestra, subcat_inv_dict = cargar_datos()


# ─────────────────────────────────────────────
# 3. UTILIDADES
# ─────────────────────────────────────────────
def subir_a_storage(archivo) -> str | None:
    """Sube un archivo de imagen a Supabase Storage y retorna su URL pública."""
    if not archivo:
        return None
    try:
        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_limpio = archivo.name.replace(" ", "_")
        nombre_archivo = f"img_{timestamp}_{nombre_limpio}"

        supabase.storage.from_("imagenes").upload(
            path=nombre_archivo,
            file=archivo.getvalue(),
            file_options={"content-type": archivo.type},
        )
        return supabase.storage.from_("imagenes").get_public_url(nombre_archivo)

    except Exception as e:
        st.warning(f"No se pudo subir la imagen: {e}")
        return None


def normalizar(texto) -> str:
    """Normaliza un texto para comparación: minúsculas sin espacios."""
    return "".join(str(texto or "").lower().split())


def validar_producto_existente(nombre, marca, barras, tamano, unidad, id_excluir=None):
    """
    Verifica si ya existe un producto igual (por código de barras o por atributos).

    Retorna:
        ("barras" | "atributos" | None, producto_clon | None)
    """
    # Validación por código de barras
    barras_str = str(barras).strip() if barras else ""
    if barras_str:
        res = supabase.table("productos").select("*").eq("codigo_barras", barras_str).execute()
        if res.data:
            clon = res.data[0]  # CORRECCIÓN: era res.data.get(...) lo cual es incorrecto
            if id_excluir and clon.get("id_producto") == id_excluir:
                pass  # Es el mismo producto, ignorar
            else:
                return "barras", clon

    # Validación por atributos combinados
    if not (lista_productos_maestra and str(nombre or "").strip()):
        return None, None

    nom_norm = normalizar(nombre)
    mar_norm = normalizar(marca)
    tam_norm = float(tamano or 0)
    uni_norm = str(unidad or "").lower()

    for p in lista_productos_maestra:
        if id_excluir and p.get("id_producto") == id_excluir:
            continue
        if (
            normalizar(p.get("nombre"))  == nom_norm
            and normalizar(p.get("marca")) == mar_norm
            and float(p.get("tamano") or 0) == tam_norm
            and str(p.get("unidad") or "").lower() == uni_norm
        ):
            return "atributos", p

    return None, None


def obtener_id_subcat(subcategoria_nombre, id_cat) -> int | None:
    """Busca el id_subcat dado el nombre y la categoría padre."""
    if subcategoria_nombre == PLACEHOLDER_CAT or id_cat is None:
        return None
    for sc in lista_subcat_maestra:
        if sc.get("nombre") == subcategoria_nombre and sc.get("id_cat") == id_cat:
            return sc.get("id_subcat")
    return None


def invalidar_cache():
    """Limpia la caché y recarga."""
    cargar_datos.clear()
    st.session_state["pos_form_counter"] += 1
    st.rerun()


# ─────────────────────────────────────────────
# 4. INTERFAZ POR PESTAÑAS
# ─────────────────────────────────────────────
t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar / Borrar"])


# ── PESTAÑA 1: VER CATÁLOGO ──────────────────
with t1:
    if not lista_productos_maestra:
        st.info("El catálogo de productos está vacío.")
    else:
        filas = [
            {
                "ID":           p.get("id_producto"),
                "Nombre":       p.get("nombre"),
                "Marca":        p.get("marca") or "Sin Marca",
                "Código Barras":p.get("codigo_barras") or "N/A",
                "Tamaño":       p.get("tamano"),
                "Unidad":       p.get("unidad"),
                "Categoría":    cat_inv_dict.get(p.get("id_cat"), "Sin Categoría"),
                "Subcategoría": subcat_inv_dict.get(p.get("id_subcat"), "Sin Subcategoría"),
                "url_imagen":   p.get("url_imagen") or "",
            }
            for p in lista_productos_maestra
        ]
        st.dataframe(
            pd.DataFrame(filas),
            column_config={"url_imagen": st.column_config.ImageColumn("Imagen")},
            use_container_width=True,
        )


# ── PESTAÑA 2: NUEVO PRODUCTO ────────────────
with t2:
    f_idx = st.session_state["pos_form_counter"]

    nombres_existentes = sorted({p["nombre"] for p in lista_productos_maestra if p.get("nombre")})
    marcas_existentes  = sorted({p["marca"]  for p in lista_productos_maestra if p.get("marca") and p["marca"].strip()})

    st.markdown("### 🛒 Identificación del Producto")

    # Fila 1: Nombre y Marca
    c1, c2 = st.columns(2)
    with c1:
        lookup_nombre   = st.selectbox("🔍 Reusar nombre existente:", ["➕ Nombre nuevo"] + nombres_existentes, key=f"lk_nom_{f_idx}")
        val_nom_inicial = "" if lookup_nombre == "➕ Nombre nuevo" else lookup_nombre
        nombre_final    = st.text_input("Nombre del Producto *", value=val_nom_inicial, key=f"w_nombre_{f_idx}", placeholder="Ej: Arroz Blanco")

    with c2:
        lookup_marca   = st.selectbox("🔍 Reusar marca existente:", ["➕ Marca nueva"] + marcas_existentes, key=f"lk_mar_{f_idx}")
        val_mar_inicial = "" if lookup_marca == "➕ Marca nueva" else lookup_marca
        marca_final     = st.text_input("Marca del Producto", value=val_mar_inicial, key=f"w_marca_{f_idx}", placeholder="Ej: La Italiana")

    # Fila 2: Tamaño y Unidad
    c3, c4 = st.columns(2)
    tamano  = c3.number_input("Tamaño / Peso", min_value=0.0, step=1.0, key=f"n_tam_{f_idx}", value=None, placeholder="Ej: 500, 250, 1")
    unidad  = c4.selectbox("Unidad de Medida", UNIDADES, key=f"n_uni_{f_idx}")

    # Fila 3: Categoría y Subcategoría
    c5, c6 = st.columns(2)
    categoria_sel = c5.selectbox("Categoría Principal", [PLACEHOLDER_CAT] + lista_cat, key=f"n_cat_{f_idx}")
    subcats_disponibles = [PLACEHOLDER_CAT]
    if categoria_sel != PLACEHOLDER_CAT:
        id_cat_actual = cat_dict.get(categoria_sel)
        subcats_disponibles += [sc["nombre"] for sc in lista_subcat_maestra if sc.get("id_cat") == id_cat_actual]
    subcategoria_sel = c6.selectbox("Subcategoría", subcats_disponibles, key=f"n_sub_{f_idx}")

    # Fila 4: Código de barras y Foto
    c7, c8 = st.columns(2)
    barras = c7.text_input("Código de Barras (SKU)", key=f"n_bar_{f_idx}", placeholder="Escanea o escribe...").strip()
    foto   = c8.file_uploader("Foto del Producto", type=IMG_TIPOS, key=f"n_foto_{f_idx}")
    if foto:
        st.image(foto, caption="Vista previa", width=140)

    # Fila 5: Controles de guardado
    c9, c10 = st.columns(2)
    forzar_guardado = c9.checkbox("⚠️ Forzar registro (ignorar duplicados)", key=f"n_forzar_{f_idx}")
    guardar_btn     = c10.button("🚀 Guardar Producto", type="primary", use_container_width=True)

    if guardar_btn:
        nombre_str = str(nombre_final or "").strip()
        marca_str  = str(marca_final  or "").strip()
        tamano_f   = float(tamano) if tamano is not None else 0.0

        if not nombre_str:
            st.warning("⚠️ El campo Nombre es obligatorio.")
        else:
            tipo_error, clon = validar_producto_existente(nombre_str, marca_str, barras, tamano_f, unidad)
            if tipo_error and not forzar_guardado:
                razon = "código de barras" if tipo_error == "barras" else "nombre, marca, tamaño y unidad"
                st.error(f"🚨 Producto duplicado detectado por **{razon}**: '{clon['nombre']}' — '{clon.get('marca') or 'Sin Marca'}'. "
                         f"Activa '⚠️ Forzar registro' si deseas guardarlo de todas formas.")
            else:
                url_img    = subir_a_storage(foto) if foto else None
                id_cat_val = cat_dict.get(categoria_sel) if categoria_sel != PLACEHOLDER_CAT else None
                id_sub_val = obtener_id_subcat(subcategoria_sel, id_cat_val)

                payload = {
                    "nombre":        nombre_str,
                    "marca":         marca_str or None,
                    "codigo_barras": barras or None,
                    "tamano":        tamano_f,
                    "unidad":        unidad,
                    "url_imagen":    url_img,
                    "id_cat":        id_cat_val,
                    "id_subcat":     id_sub_val,
                }
                try:
                    supabase.table("productos").insert(payload).execute()
                    st.success("🎉 ¡Producto registrado exitosamente!")
                    invalidar_cache()
                except Exception as e:
                    st.error(f"🚨 Error al guardar en la base de datos: {e}")


# ── PESTAÑA 3: EDITAR / BORRAR ───────────────
with t3:
    if not lista_productos_maestra:
        st.info("El catálogo está vacío.")
    else:
        st.subheader("Gestión de un Producto Individual")

        prod_dict_e = {
            f"{p['nombre']} — {p.get('marca') or 'Sin Marca'} ({p.get('tamano') or 0}{p.get('unidad') or ''})": p
            for p in lista_productos_maestra
        }
        sel_e = st.selectbox("Selecciona el producto:", list(prod_dict_e.keys()), key="s_e_p")
        p_e   = prod_dict_e[sel_e]

        ec1, ec2 = st.columns(2)
        en = ec1.text_input("Nombre",          value=p_e["nombre"])
        em = ec2.text_input("Marca",           value=p_e.get("marca") or "")
        eb = ec1.text_input("Código de Barras",value=p_e.get("codigo_barras") or "").strip()
        et = ec2.number_input("Tamaño",        value=float(p_e["tamano"]) if p_e.get("tamano") else 0.0, step=1.0)

        idx_uni = UNIDADES.index(p_e["unidad"]) if p_e.get("unidad") in UNIDADES else 0
        eu = ec1.selectbox("Unidad", UNIDADES, index=idx_uni)
        ef = ec2.file_uploader("Cambiar Imagen", type=IMG_TIPOS, key="e_foto")

        # Categoría (pre-seleccionada)
        cat_actual  = cat_inv_dict.get(p_e.get("id_cat"), PLACEHOLDER_CAT)
        lista_cat_e = [PLACEHOLDER_CAT] + lista_cat
        ecat = ec1.selectbox("Categoría", lista_cat_e,
                             index=lista_cat_e.index(cat_actual) if cat_actual in lista_cat_e else 0,
                             key="e_c")

        # Subcategoría reactiva a la categoría seleccionada
        subcats_e = [PLACEHOLDER_CAT]
        if ecat != PLACEHOLDER_CAT:
            id_cat_mod = cat_dict.get(ecat)
            subcats_e += [sc["nombre"] for sc in lista_subcat_maestra if sc.get("id_cat") == id_cat_mod]
        sub_actual = subcat_inv_dict.get(p_e.get("id_subcat"), PLACEHOLDER_CAT)
        esub = ec2.selectbox("Subcategoría", subcats_e,
                             index=subcats_e.index(sub_actual) if sub_actual in subcats_e else 0,
                             key="e_s")

        forzar_edicion = st.checkbox("⚠️ Forzar cambios (ignorar duplicados)", key="e_forzar")

        col_del, col_upd = st.columns(2)

        # Botón: Guardar cambios
        if col_upd.button("💾 Guardar Cambios", type="primary", use_container_width=True):
            tipo_err, clon = validar_producto_existente(en, em, eb, et, eu, id_excluir=p_e["id_producto"])
            if tipo_err and not forzar_edicion:
                razon = "código de barras" if tipo_err == "barras" else "atributos"
                st.error(f"🚨 Los cambios generarían un duplicado por **{razon}** con '{clon['nombre']}'. "
                         "Activa '⚠️ Forzar cambios' para continuar.")
            else:
                nueva_url = subir_a_storage(ef) if ef else p_e.get("url_imagen")
                v_cat     = cat_dict.get(ecat) if ecat != PLACEHOLDER_CAT else None
                v_sub     = obtener_id_subcat(esub, v_cat)
                try:
                    supabase.table("productos").update({
                        "nombre":        en,
                        "marca":         em or None,
                        "codigo_barras": eb or None,
                        "tamano":        et,
                        "unidad":        eu,
                        "url_imagen":    nueva_url,
                        "id_cat":        v_cat,
                        "id_subcat":     v_sub,
                    }).eq("id_producto", p_e["id_producto"]).execute()
                    st.success("✅ ¡Cambios guardados correctamente!")
                    invalidar_cache()
                except Exception as e:
                    st.error(f"🚨 Error al actualizar: {e}")

        # Botón: Eliminar
        if col_del.button("🗑️ Eliminar Producto", use_container_width=True):
            try:
                supabase.table("productos").delete().eq("id_producto", p_e["id_producto"]).execute()
                st.warning(f"🗑️ Producto '{p_e['nombre']}' eliminado.")
                invalidar_cache()
            except Exception as e:
                st.error(f"🚨 Error al eliminar: {e}")
