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
    """
    Busca coincidencias estrictas por código de barras o similitud por combinación
    de Nombre + Marca + Tamaño + Unidad (ignorando mayúsculas y espacios).
    """
    # 1. Validación por Código de Barras (Capa Dura)
    if barras:
        query_barras = supabase.table("productos").select("*").eq("codigo_barras", barras)
        if id_excluir:
            query_barras = query_barras.neq("id_producto", id_excluir)
        res_barras = query_barras.execute()
        if res_barras.data:
            return "barras", res_barras.data[0]

    # 2. Validación por Combinación de Atributos (Capa Inteligente)
    # Traemos los productos existentes para comparar en memoria de forma limpia
    query_textos = supabase.table("productos").select("*")
    if id_excluir:
        query_textos = query_textos.neq("id_producto", id_excluir)
    res_textos = query_textos.execute()
    
    if res_textos.data:
        # Normalizamos la entrada del usuario
        nom_norm = "".join(nombre.lower().split())
        mar_norm = "".join(marca.lower().split()) if marca else ""
        tam_norm = float(tamano)
        uni_norm = unidad.lower()

        for p in res_textos.data:
            p_nom = "".join(p['nombre'].lower().split())
            p_mar = "".join(p['marca'].lower().split()) if p['marca'] else ""
            p_tam = float(p['tamano']) if p['tamano'] else 0.0
            p_uni = p['unidad'].lower() if p['unidad'] else ""

            # Si coinciden los 4 atributos esenciales, es un duplicado semántico
            if nom_norm == p_nom and mar_norm == p_mar and tam_norm == p_tam and p_uni == uni_norm:
                return "atributos", p

    return None, None

# 2. MENÚ LATERAL DE NAVEGACIÓN
st.sidebar.title("Menú Principal")
menu = ["🔍 Alertas y Ofertas", "📦 Gestión de Productos", "🏪 Tiendas y Sucursales", "🏷️ Registrar Ofertas"]
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
    except Exception as e:
        st.error(f"Error al conectar con la tabla de ofertas: {e}")
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
                        st.image(p_img or "placeholder.com", use_container_width=True)
                    
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
                                
                                st.metric(label="Precio", value=f"${fila['precio_oferta']:.2f}")
                                
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

# --- SECCIÓN 2: GESTIÓN DE PRODUCTOS (VALIDACIÓN ROBUSTA) ---
elif choice == "📦 Gestión de Productos":
    st.title("📦 Administración de Productos")
    t1, t2, t3 = st.tabs(["📋 Ver Catálogo", "➕ Nuevo Producto", "✏️ Editar/Borrar"])
    
    try:
        res_p = supabase.table("productos").select("*").order("nombre").execute()
        df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()
    except:
        df_p = pd.DataFrame()

    with t1:
        if not df_p.empty:
            st.dataframe(df_p, column_config={"url_imagen": st.column_config.ImageColumn()}, use_container_width=True)
        else:
            st.info("El catálogo está vacío.")
            
    with t2:
        with st.form("nuevo_p", clear_on_submit=False):
            col1, col2 = st.columns(2)
            nombre = col1.text_input("Nombre*")
            marca = col2.text_input("Marca")
            barras = col1.text_input("Código de Barras (EAN / UPC)").strip()
            tam = col2.number_input("Tamaño/Peso", min_value=0.0, step=0.1)
            uni = col1.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"])
            foto = col2.file_uploader("Foto (WebP, JPG, PNG)", type=['jpg', 'png', 'jpeg', 'webp'])
            
            # Casilla de emergencia para omitir advertencias si el usuario insiste
            forzar_guardado = st.checkbox("⚠️ Forzar el registro (Usar solo si estás seguro de que no es un duplicado)")

            if st.form_submit_button("🚀 Guardar Producto"):
                if nombre:
                    tipo_error, clon = validar_producto_existente(nombre, marca, barras, tam, uni)
                    
                    if tipo_error and not forzar_guardado:
                        if tipo_error == "barras":
                            st.error(f"🚨 BLOQUEO CRÍTICO: El código de barras **{barras}** ya está registrado.")
                        else:
                            st.warning(f"⚠️ DETECCIÓN DE SIMILITUD: Ya existe un producto con características idénticas.")
                        
                        st.info(f"📦 **Producto en Base de Datos:** {clon['nombre']} ({clon['marca']}) - {clon['tamano']} {clon['unidad']} | Código: {clon['codigo_barras'] or 'Ninguno'}")
                    else:
                        url_img = subir_a_storage(foto)
                        try:
                            supabase.table("productos").insert({
                                "nombre": nombre, "marca": marca, "codigo_barras": barras if barras else None, 
                                "tamano": tam, "unidad": uni, "url_imagen": url_img
                            }).execute()
                            st.success("¡Producto guardado exitosamente!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                else:
                    st.warning("El campo 'Nombre' es obligatorio.")

    with t3:
        if not df_p.empty:
            prod_dict = {f"{p['nombre']} - {p['marca']} ({p['tamano']}{p['unidad']})": p for p in res_p.data}
            sel = st.selectbox("Selecciona producto para modificar:", list(prod_dict.keys()))
            p = prod_dict[sel]
            
            with st.form("edit_p"):
                en = st.text_input("Nombre", p['nombre'])
                em = st.text_input("Marca", p['marca'])
                eb = st.text_input("Código de Barras", p['codigo_barras'] or "").strip()
                et = st.number_input("Tamaño", value=float(p['tamano']) if p['tamano'] else 0.0)
                eu = st.selectbox("Unidad", ["gr", "kg", "ml", "lt", "unidad"], index=["gr", "kg", "ml", "lt", "unidad"].index(p['unidad']) if p['unidad'] in ["gr", "kg", "ml", "lt", "unidad"] else 0)
                ef = st.file_uploader("Cambiar Foto", type=['jpg', 'png', 'jpeg', 'webp'])
                
                forzar_edit = st.checkbox("⚠️ Forzar cambios")
                c_del, c_upd = st.columns(2)
                
                if c_upd.form_submit_button("💾 Guardar Cambios"):
                    tipo_error, clon = validar_producto_existente(en, em, eb, et, eu, id_excluir=p['id_producto'])
                    
                    if tipo_error and not forzar_edit:
                        st.error(f"🚨 OPERACIÓN RECHAZADA: Estos cambios generan un conflicto de duplicidad con el producto: {clon['nombre']} ({clon['marca']})")
                    else:
                        nueva_url = subir_a_storage(ef) if ef else p['url_imagen']
                        try:
                            supabase.table("productos").update({
                                "nombre": en, "marca": em, "codigo_barras": eb if eb else None, "tamano": et, "unidad": eu, "url_imagen": nueva_url
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

# --- SECCIÓN 3: TIENDAS Y SUCURSALES ---
elif choice == "🏪 Tiendas y Sucursales":
    st.title("🏪 Registro de Tiendas y Establecimientos")
    with st.form("super"):
        nom = st.text_input("Nombre de la Cadena de Supermercado")
        if st.form_submit_button("Guardar Cadena"):
            if nom:
                try:
                    supabase.table("supermercados").insert({"nombre_supermercado": nom}).execute()
                    st.success("Supermercado registrado."); st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar: {e}")
    
    st.divider()
    try:
        supers = supabase.table("supermercados").select("*").execute()
    except:
        supers = None

    if supers and supers.data:
        df_s = pd.DataFrame(supers.data)
        super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        
        with st.form("suc"):
            s_sel = st.selectbox("Selecciona a qué cadena pertenece:", list(super_dict.keys()))
            n_suc = st.text_input("Nombre de la Sucursal")
            ciu = st.text_input("Ciudad")
            if st.form_submit_button("Guardar Sucursal"):
                if n_suc and ciu:
                    try:
                        supabase.table("sucursales").insert({"id_super": super_dict[s_sel], "nombre_sucursal": n_suc, "ciudad": ciu}).execute()
                        st.success("Sucursal guardada con éxito."); st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar sucursal: {e}")

# --- SECCIÓN 4: REGISTRAR OFERTAS ---
elif choice == "🏷️ Registrar Ofertas":
    st.title("🏷️ Cargar Ofertas por Catálogo")
    try:
        supers = supabase.table("supermercados").select("*").execute()
    except:
        supers = None

    if supers and supers.data:
        df_s = pd.DataFrame(supers.data)
        super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
        super_sel = st.selectbox("¿De qué Supermercado es el volante?", list(super_dict.keys()))
        
        try:
            sucs = supabase.table("sucursales").select("*").eq("id_super", super_dict[super_sel]).execute()
        except:
            sucs = None

        suc_dict = {"--- TODAS LAS SUCURSALES ---": None}
        if sucs and sucs.data:
            for s in sucs.data: 
                suc_dict[s['nombre_sucursal']] = s['id_sucursal']
                
        suc_sel = st.selectbox("¿Aplica a una sucursal específica?", list(suc_dict.keys()))
        
        try:
            prods = supabase.table("productos").select("id_producto, nombre, marca").execute()
        except:
            prods = None

        if prods and prods.data:
            p_df = pd.DataFrame(prods.data)
            p_dict = dict(zip(p_df['nombre'] + " (" + p_df['marca'] + ")", p_df['id_producto']))
            
            with st.form("form_of"):
                p_sel = st.selectbox("Producto en oferta", list(p_dict.keys()))
                precio = st.number_input("Precio Oferta", min_value=0.0, format="%.2f")
                vence = st.date_input("¿Cuándo termina la promoción?", format="DD/MM/YYYY")
                
                if st.form_submit_button("Publicar Oferta"):
                    try:
                        supabase.table("ofertas").insert({
                            "id_producto": p_dict[p_sel], 
                            "id_super": super_dict[super_sel],
                            "id_sucursal": suc_dict[suc_sel],
                            "precio_oferta": precio, 
                            "fecha_fin": str(vence)
                        }).execute()
                        st.success("¡Oferta publicada exitosamente!"); st.balloons()
                    except Exception as e:
                        st.error(f"Error al publicar la oferta: {e}")
