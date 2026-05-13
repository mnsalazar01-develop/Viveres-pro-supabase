import streamlit as st
import pandas as pd
from datetime import datetime

# 1. VERIFICACIÓN DE CONEXIÓN CENTRAL COMPARTIDA
if "supabase" not in st.session_state:
    st.error("Conexión central no encontrada. Por favor, regresa a la página de inicio.")
    st.stop()

supabase = st.session_state["supabase"]
st.title("🏷️ Registrar Ofertas por Catálogo")

# 2. CARGA DE DATOS MAESTROS DESDE EL SERVIDOR
try:
    res_c = supabase.table("categorias").select("id_cat, nombre").order("id_cat").execute()
    c_inv = {c['id_cat']: c['nombre'] for c in res_c.data} if res_c.data else {}
    supers = supabase.table("supermercados").select("*").order("nombre_supermercado").execute()
except: 
    supers, c_inv = None, {}

# 3. INTERFAZ DE REGISTRO EN CASCADA
if supers and supers.data:
    df_s = pd.DataFrame(supers.data)
    super_dict = dict(zip(df_s['nombre_supermercado'], df_s['id_super']))
    super_sel = st.selectbox("🏬 ¿De qué Supermercado es el volante/catálogo?", list(super_dict.keys()))
    
    # Buscamos las sucursales pertenecientes estrictamente a la cadena seleccionada
    try: 
        sucs = supabase.table("sucursales").select("*").eq("id_super", super_dict[super_sel]).execute()
    except: 
        sucs = None

    # Mapeo seguro: Si elige "TODAS", guardamos None (NULL en la base de datos)
    suc_dict = {"--- TODAS LAS SUCURSALES (Oferta Nacional) ---": None}
    if sucs and sucs.data:
        for s in sucs.data: 
            suc_dict[s['nombre_sucursal']] = s['id_sucursal']
            
    suc_sel = st.selectbox("📍 ¿Aplica a una sucursal específica o a todas?", list(suc_dict.keys()))
    
    try: 
        prods = supabase.table("productos").select("id_producto, nombre, marca, id_cat").execute()
    except: 
        prods = None

    if prods and prods.data:
        p_df = pd.DataFrame(prods.data)
        p_df['cat_nombre'] = p_df['id_cat'].map(c_inv).fillna("Sin Categoría")
        
        # Generamos la etiqueta limpia ordenando los víveres por el ID de su categoría principal
        p_df['label_visual'] = "[" + p_df['cat_nombre'] + "] " + p_df['nombre'] + " (" + p_df['marca'] + ")"
        p_dict = dict(zip(p_df['label_visual'], p_df['id_producto']))
        lista_prods_ordenada = sorted(list(p_dict.keys()))
        
        # Formulario de inserción de datos con autorefresco limpio al enviar
        with st.form("form_of_definitivo", clear_on_submit=True):
            p_sel = st.selectbox("📦 Selecciona el Producto en oferta:", lista_prods_ordenada)
            precio = st.number_input("💰 Digita el Precio de Oferta:", min_value=0.0, step=0.01, format="%.2f")
            
            c_fecha1, c_fecha2 = st.columns(2)
            inicio = c_fecha1.date_input("📅 Fecha de Inicio:", format="DD/MM/YYYY")
            vence = c_fecha2.date_input("⏳ Fecha de Vencimiento:", format="DD/MM/YYYY")
            
            if st.form_submit_button("🚀 Publicar Oferta en el Mercado"):
                if precio > 0:
                    # Construimos el paquete de datos asegurando nulos en sucursales globales
                    paquete_oferta = {
                        "id_producto": p_dict[p_sel], 
                        "id_super": super_dict[super_sel],
                        "id_sucursal": suc_dict[suc_sel], 
                        "precio_oferta": float(precio), 
                        "fecha_inicio": str(inicio),
                        "fecha_fin": str(vence)
                    }
                    
                    try:
                        # Mandamos la orden de inserción a Supabase
                        supabase.table("ofertas").insert(paquete_oferta).execute()
                        st.success(f"✅ ¡Oferta de '{p_sel}' publicada exitosamente!")
                        st.balloons()
                    except Exception as error_servidor:
                        # CAJA DE AUXILIO TÉCNICO: Si Supabase rechaza los datos, te dice la columna exacta aquí
                        st.error("🚨 Supabase rechazó el guardado debido al siguiente motivo:")
                        st.info(f"**Detalle del Servidor:** {error_servidor}")
                        with st.expander("Ver paquete de datos enviado"):
                            st.json(paquete_oferta)
                else:
                    st.warning("El precio de oferta debe ser mayor a 0.")
    else:
        st.warning("No hay productos registrados en el catálogo maestro. Ve a 'Gestión de Productos' para ingresar uno.")
else:
    st.warning("No hay supermercados registrados en el sistema. Ve a 'Tiendas y Sucursales' para ingresar la primera cadena.")
