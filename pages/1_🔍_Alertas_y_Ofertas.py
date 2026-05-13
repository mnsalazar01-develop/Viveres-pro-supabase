import streamlit as st
import pandas as pd
from datetime import datetime, date

# 1. RECUPERAR CONEXIÓN COMPARTIDA
if "supabase" not in st.session_state:
    st.error("No se encontró la conexión central. Por favor, ve al Inicio.")
    st.stop()

supabase = st.session_state["supabase"]
URL_DEFECTO = "flaticon.com"

st.title("🔔 Mis Alertas y Ofertas")

# 2. CARGAR DICCIONARIOS MAESTROS
try:
    res_cat = supabase.table("categorias").select("*").order("id_cat").execute()
    c_inv = {c['id_cat']: c['nombre'] for c in res_cat.data} if res_cat.data else {}
except:
    c_inv = {}

# 3. BUSCADOR INTERACTIVO POR INTERÉS
try:
    res_p = supabase.table("productos").select("nombre").execute()
    lista_productos = sorted(list(set([p['nombre'] for p in res_p.data]))) if res_p.data else []
except:
    lista_productos = []
    
productos_interes = st.multiselect("⭐ Filtrar por lo que necesitas comprar hoy:", lista_productos)

# 4. CONSULTA DE OFERTAS EN TIEMPO REAL
try:
    res = supabase.table("ofertas").select("""
        id_oferta, precio_oferta, fecha_inicio, fecha_fin, id_producto,
        productos(nombre, marca, url_imagen, tamano, unidad),
        supermercados(nombre_supermercado),
        sucursales(nombre_sucursal)
    """).execute()
except Exception as e:
    st.error(f"Error al conectar con las ofertas: {e}")
    res = None

if res and res.data:
    df = pd.json_normalize(res.data)
    
    # Blindaje contra campos vacíos
    cols_criticas = {
        'productos.nombre': 'Desconocido', 'productos.marca': '', 
        'productos.url_imagen': '', 'productos.tamano': 0, 'productos.unidad': 'ud', 
        'supermercados.nombre_supermercado': 'Supermercado', 'sucursales.nombre_sucursal': 'Todas las sucursales'
    }
    for col, def_val in cols_criticas.items():
        df[col] = df[col].fillna(def_val) if col in df.columns else def_val
        
    if productos_interes:
        df = df[df['productos.nombre'].isin(productos_interes)]

    if not df.empty:
        df['fecha_dt'] = pd.to_datetime(df['fecha_fin'])
        
        # COMPARADOR LADO A LADO POR PRODUCTO
        for prod_id, grupo in df.groupby('id_producto'):
            grp = grupo.sort_values(by='precio_oferta')
            
            with st.container(border=True):
                c_img, c_info = st.columns(2)
                with c_img:
                    st.image(grp['productos.url_imagen'].iloc or URL_DEFECTO, use_container_width=True)
                with c_info:
                    st.subheader(f"{grp['productos.nombre'].iloc} - {grp['productos.marca'].iloc} ({grp['productos.tamano'].iloc} {grp['productos.unidad'].iloc})")
                    st.write("🛒 **Opciones disponibles en el mercado:**")
                    
                    cols_t = st.columns(len(grp))
                    for i, (_, f) in enumerate(grp.iterrows()):
                        dias = (f['fecha_dt'].date() - date.today()).days
                        es_b = (i == 0)
                        
                        f_ini = datetime.strptime(f['fecha_inicio'], '%Y-%m-%d').strftime('%d/%m/%Y') if 'fecha_inicio' in f and pd.notna(f['fecha_inicio']) else "N/A"
                        f_fin = f['fecha_dt'].date().strftime('%d/%m/%Y')
                        
                        with cols_t[i]:
                            st.markdown(f"""
                                <div style="border: 2px solid {'#2bc443' if es_b else '#ccc'}; border-radius: 8px; padding: 10px; text-align: center; background-color: {'#f0fff4' if es_b else '#fff'}; margin-bottom: 10px;">
                                    <b>{"🏆 MEJOR PRECIO" if es_b else "Oferta"}</b>
                                    <h4>{f["supermercados.nombre_supermercado"]}</h4>
                                    <p style="font-size:0.8em; color:gray;">{f["sucursales.nombre_sucursal"]}</p>
                                </div>
                            """, unsafe_allow_html=True)
                            st.metric(label="Precio", value=f"${f['precio_oferta']:.2f}")
                            st.caption(f"📅 Inicio: {f_ini}")
                            
                            if 0 <= dias <= 2:
                                st.error(f"🚨 ¡CORRE! Vence en {dias} día(s) ({f_fin})")
                            elif dias < 0:
                                        st.warning(f"⚠️ Caducó ({f_fin})")
                            else:
                                st.info(f"⏳ Vence el: {f_fin}")
    else:
        st.warning("No hay ofertas para los productos seleccionados.")
else:
    st.info("Aún no has registrado ninguna oferta.")
