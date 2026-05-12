import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# 1. Conexión
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Viveres Pro", layout="wide", page_icon="🛒")

menu = ["📊 Dashboard de Ofertas", "📦 Gestión de Productos", "🏪 Tiendas y Sucursales", "🏷️ Registrar Oferta"]
choice = st.sidebar.selectbox("Menú Principal", menu)

# --- SECCIÓN: DASHBOARD (Con formato de fecha corregido) ---
if choice == "📊 Dashboard de Ofertas":
    st.title("🚀 Ofertas Activas")
    res = supabase.table("ofertas").select("""
        precio_oferta, fecha_fin,
        productos(nombre, marca, url_imagen),
        supermercados(nombre_supermercado, url_logo),
        sucursales(nombre_sucursal)
    """).execute()
    
    if res.data:
        for o in res.data:
            # --- TRUCO DE FECHA: De '2024-12-31' a '31/12/2024' ---
            fecha_dt = datetime.strptime(o['fecha_fin'], '%Y-%m-%d')
            fecha_formateada = fecha_dt.strftime('%d/%m/%Y')
            
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
                    st.warning(f"⌛ Vence: {fecha_formateada}")
    else:
        st.info("No hay ofertas activas por ahora.")

# --- SECCIÓN: REGISTRAR OFERTA ---
elif choice == "🏷️ Registrar Oferta":
    st.title("🏷️ Publicar Nueva Oferta")
    
    prods = supabase.table("productos").select("id_producto, nombre, marca").execute()
    supers = supabase.table("supermercados").select("id_super, nombre_supermercado").execute()
    
    if prods.data and supers.data:
        with st.form("form_oferta", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                df_p = pd.DataFrame(prods.data)
                prod_label = df_p['nombre'] + " - " + df_p['marca']
                dict_p = dict(zip(prod_label, df_p['id_producto']))
                producto_sel = st.selectbox("Producto", prod_label)
                
                df_s = pd.DataFrame(supers.data)
                dict_s = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
                super_sel = st.selectbox("Supermercado", list(dict_s.keys()))
                
            with col2:
                sucs = supabase.table("sucursales").select("*").eq("id_super", dict_s[super_sel]).execute()
                opciones_suc = {"--- TODAS LAS SUCURSALES ---": None}
                if sucs.data:
                    for s in sucs.data:
                        opciones_suc[s['nombre_sucursal']] = s['id_sucursal']
                
                sucursal_sel = st.selectbox("Sucursal", list(opciones_suc.keys()))
                precio = st.number_input("Precio Oferta", min_value=0.0, format="%.2f")
                # El selector de fecha siempre es amigable
                fecha_vence = st.date_input("Vence el día:", format="DD/MM/YYYY")

            if st.form_submit_button("🚀 Publicar Oferta"):
                nueva_oferta = {
                    "id_producto": dict_p[producto_sel],
                    "id_super": dict_s[super_sel],
                    "id_sucursal": opciones_suc[sucursal_sel],
                    "precio_oferta": precio,
                    "fecha_fin": str(fecha_vence) # Supabase lo recibe como string YYYY-MM-DD
                }
                supabase.table("ofertas").insert(nueva_oferta).execute()
                st.success(f"¡Oferta guardada! Vencimiento: {fecha_vence.strftime('%d/%m/%Y')}")
                st.balloons()
