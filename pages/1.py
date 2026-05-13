import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL
if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]
URL_DEFECTO = "flaticon.com"

st.title("🔔 Mis Alertas y Ofertas")

# 2. CARGAR PRODUCTOS DISPONIBLES PARA EL BUSCADOR
try:
    res_p = supabase.table("productos").select("nombre").execute()
    lista_productos = sorted(list(set([p['nombre'] for p in res_p.data]))) if res_p.data else []
except:
    lista_productos = []
    
productos_interes = st.multiselect("⭐ Filtrar por lo que necesitas comprar hoy:", lista_productos)

# 3. CONSULTA RELACIONAL LIMPIA
try:
    res = supabase.table("ofertas").select("""
        id_oferta, precio_oferta, fecha_inicio, fecha_fin, id_producto,
        productos(nombre, marca, url_imagen, tamano, unidad),
        supermercados(nombre_supermercado),
        sucursales(nombre_sucursal)
    """).execute()
except Exception as e:
    st.error(f"Error de conexión con la base de datos: {e}")
    res = None

# 4. PROCESAMIENTO EXPLICITO (Evita errores de nombres de columnas)
if res and res.data:
    lista_limpia = []
    
    # Procesamos fila por fila de forma manual para garantizar estabilidad total
    for o in res.data:
        prod = o.get("productos") or {}
        sup = o.get("supermercados") or {}
        suc = o.get("sucursales") or {}
        
        fila = {
            "id_oferta": o.get("id_oferta"),
            "id_producto": o.get("id_producto"),
            "precio_oferta": float(o.get("precio_oferta", 0)),
            "fecha_inicio": o.get("fecha_inicio"),
            "fecha_fin": o.get("fecha_fin"),
            "prod_nombre": prod.get("nombre", "Producto Desconocido"),
            "prod_marca": prod.get("marca", ""),
            "prod_imagen": prod.get("url_imagen"),
            "prod_tamano": prod.get("tamano", 0),
            "prod_unidad": prod.get("unidad", "ud"),
            "super_nombre": sup.get("nombre_supermercado", "Supermercado"),
            "suc_nombre": suc.get("nombre_sucursal", "Todas las sucursales")
        }
        lista_limpia.append(fila)
        
    df = pd.DataFrame(lista_limpia)

    # Aplicamos filtro de intereses si el usuario seleccionó alguno
    if productos_interes and not df.empty:
        df = df[df['prod_nombre'].isin(productos_interes)]

    # 5. RENDERIZADO VISUAL EN TARJETAS
    if not df.empty:
        # Convertimos fechas de texto a formato fecha real para ordenar cronológicamente
        df['fecha_dt'] = pd.to_datetime(df['fecha_fin'], errors='coerce')
        df = df.sort_values(by='fecha_dt')

        for prod_id, grupo in df.groupby('id_producto'):
            grp = grupo.sort_values(by='precio_oferta')
            
            # Datos principales de la tarjeta de producto
            p_nom = grp['prod_nombre'].iloc[0]
            p_mar = grp['prod_marca'].iloc[0]
            p_img = grp['prod_imagen'].iloc[0]
            p_tam = grp['prod_tamano'].iloc[0]
            p_uni = grp['prod_unidad'].iloc[0]
            
            with st.container(border=True):
                c_img, c_info = st.columns([1, 3])
                
                with c_img:
                    # Cargamos el link real o el icono por defecto de forma segura
                    st.image(p_img if p_img and str(p_img).strip() != "" else URL_DEFECTO, use_container_width=True)
                
                with c_info:
                    st.subheader(f"{p_nom} - {p_mar} ({p_tam} {p_uni})")
                    st.write("🛒 **Opciones disponibles en el mercado:**")
                    
                    # Generamos columnas para colocar las tiendas lado a lado (Comparador)
                    cols_tiendas = st.columns(len(grp))
                    for i, (_, f) in enumerate(grp.iterrows()):
                        hoy = date.today()
                        fecha_v = f['fecha_dt'].date() if pd.notna(f['fecha_dt']) else hoy
                        dias = (fecha_v - hoy).days
                        
                        es_b = (i == 0)
                        borde_color = "#2bc443" if es_b else "#cccccc"
                        bg_color = "#f0fff4" if es_b else "#ffffff"
                        badge = "🏆 MEJOR PRECIO" if es_b else "Oferta disponible"
                        
                        # Formatear fechas para el usuario
                        try:
                            f_ini = datetime.strptime(f['fecha_inicio'], '%Y-%m-%d').strftime('%d/%m/%Y')
                        except: f_ini = "N/A"
                        f_fin = secret_fecha = fecha_v.strftime('%d/%m/%Y')
                        
                        with cols_tiendas[i]:
                            st.markdown(f"""
                                <div style="border: 2px solid {borde_color}; border-radius: 8px; padding: 10px; text-align: center; background-color: {bg_color}; margin-bottom: 5px;">
                                    <b style="color: {'#2bc443' if es_b else '#555555'}; font-size: 0.85em;">{badge}</b>
                                    <h4 style="margin: 5px 0 0 0; color: #333333;">{f['super_nombre']}</h4>
                                    <p style="margin: 0; font-size: 0.75em; color: gray;">{f['suc_text'] if 'suc_text' in f else f['suc_name'] if 'suc_name' in f else f['suc_nombre']}</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            st.metric(label="Precio", value=f"${f['precio_oferta']:.2f}")
                            st.caption(f"📅 Inicio: {f_ini}")
                            
                            # SEMÁFORO DE URGENCIA CRONOLÓGICO (PRO)
                            if 0 <= dias <= 2:
                                st.error(f"🚨 ¡CORRE! Vence en {dias} día(s) ({f_fin})")
                            elif dias < 0:
                                st.warning(f"⚠️ Caducó ({f_fin})")
                            else:
                                st.info(f"⏳ Vence el: {f_fin}")
    else:
        st.warning("No se encontraron ofertas activas que coincidan con la búsqueda.")
else:
    st.info("Aún no has registrado ninguna oferta en el sistema.")
