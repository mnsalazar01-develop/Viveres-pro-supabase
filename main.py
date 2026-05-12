import streamlit as st
from supabase import create_client
import pandas as pd

# Conexión
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Viveres Pro", layout="wide", page_icon="🛒")

menu = ["📊 Dashboard de Ofertas", "📦 Gestión de Productos", "🏪 Tiendas y Sucursales", "🏷️ Registrar Oferta"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- SECCIÓN: REGISTRAR OFERTA (La nueva lógica) ---
if choice == "🏷️ Registrar Oferta":
    st.title("🏷️ Publicar Nueva Oferta")
    
    # 1. Traemos datos para los desplegables
    prods = supabase.table("productos").select("id_producto, nombre, marca").execute()
    supers = supabase.table("supermercados").select("id_super, nombre_supermercado").execute()
    
    if prods.data and supers.data:
        with st.form("form_oferta", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                # Elegir Producto
                df_p = pd.DataFrame(prods.data)
                prod_label = df_p['nombre'] + " - " + df_p['marca']
                dict_p = dict(zip(prod_label, df_p['id_producto']))
                producto_sel = st.selectbox("¿Qué producto está en oferta?", prod_label)
                
                # Elegir Supermercado
                df_s = pd.DataFrame(supers.data)
                dict_s = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
                super_sel = st.selectbox("¿En qué cadena?", list(dict_s.keys()))
                
            with col2:
                # Elegir Sucursal (OPCIONAL)
                sucs = supabase.table("sucursales").select("*").eq("id_super", dict_s[super_sel]).execute()
                opciones_suc = {"--- TODAS LAS SUCURSALES ---": None}
                if sucs.data:
                    for s in sucs.data:
                        opciones_suc[s['nombre_sucursal']] = s['id_sucursal']
                
                sucursal_sel = st.selectbox("¿Sucursal específica? (Opcional)", list(opciones_suc.keys()))
                precio = st.number_input("Precio de Oferta", min_value=0.0, step=0.01)
                fecha_vence = st.date_input("Fecha de Vencimiento")

            if st.form_submit_button("🚀 Publicar Oferta"):
                nueva_oferta = {
                    "id_producto": dict_p[producto_sel],
                    "id_super": dict_s[super_sel],
                    "id_sucursal": opciones_suc[sucursal_sel],
                    "precio_oferta": precio,
                    "fecha_fin": str(fecha_vence)
                }
                supabase.table("ofertas").insert(nueva_oferta).execute()
                st.success(f"¡Oferta de {producto_sel} publicada!")
                st.balloons()
    else:
        st.warning("Asegúrate de tener al menos un Producto y un Supermercado registrados.")

# --- SECCIÓN: DASHBOARD (Para ver los resultados) ---
elif choice == "📊 Dashboard de Ofertas":
    st.title("🚀 Ofertas Activas")
    # Join Pro: Traemos nombre de producto, marca, logo de super y nombre de sucursal
    res = supabase.table("ofertas").select("""
        precio_oferta, fecha_fin,
        productos(nombre, marca, url_imagen),
        supermercados(nombre_supermercado, url_logo),
        sucursales(nombre_sucursal)
    """).execute()
    
    if res.data:
        for o in res.data:
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.image(o['productos']['url_imagen'] or "https://placeholder.com", width=100)
                with c2:
                    st.subheader(f"{o['productos']['nombre']} ({o['productos']['marca']})")
                    suc_name = o['sucursales']['nombre_sucursal'] if o['sucursales'] else "Todas las Sucursales"
                    st.write(f"🏢 {o['supermercados']['nombre_supermercado']} - 📍 {suc_name}")
                with c3:
                    st.metric("OFERTA", f"${o['precio_oferta']}")
                    st.caption(f"Vence: {o['fecha_fin']}")
    else:
        st.info("No hay ofertas activas por ahora.")
