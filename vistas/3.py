from nicegui import ui
import pandas as pd

# --- CONTROL DE VERSIONES NICEGUI PURO ---
VERSION_MODULO = "v1.0.1 - Parche de Propiedad Placeholder"

# Catálogo simulado de 4 registros para hacer la prueba física en caliente
nombres_existentes = ["Aceite Vegetal", "Arroz Blanco", "Harina Pan", "Mayonesa Mavesa"]
marcas_existentes = ["Diana", "Mavesa", "Nestlé", "Kraft"]

# --- DISEÑO DE LA INTERFAZ COMPACTA POS ---
ui.label("📦 Administración de Productos").classes("text-xl font-bold text-slate-800 m-0")
ui.label(f"Entorno de Prueba: {VERSION_MODULO}").classes("text-xs text-slate-500 m-0")

# Contenedor de carga ágil
with ui.card().classes("w-full max-w-4xl p-4 m-2 shadow-sm"):
    ui.label("Formulario de Carga").classes("text-sm font-semibold text-slate-600")
    
    # FILA 1: LAS DOS CAJAS INTELIGENTES REALES EN PRIMER PLANO
    with ui.row().classes("w-full gap-4"):
        # CORREGIDO v1.0.1: Pasamos el placeholder dentro de las propiedades .props() de Quasar
        nombre_input = ui.select(
            options=nombres_existentes,
            with_input=True,
            label="Nombre del Producto*"
        ).props('new-value-mode="add" clearable placeholder="Busca o escribe un nombre..."').classes("flex-1")
        
        marca_input = ui.select(
            options=marcas_existentes,
            with_input=True,
            label="Marca del Producto"
        ).props('new-value-mode="add" clearable placeholder="Busca o escribe una marca..."').classes("flex-1")

    # FILA 2: CONTENIDO NETO
    with ui.row().classes("w-full gap-4 mt-2"):
        # Pasamos el placeholder correcto también para el campo numérico
        tamano = ui.number(label="Tamaño / Peso").props("placeholder='Ej: 500'").classes("flex-1")
        unidad = ui.select(options=["gr", "kg", "ml", "lt", "unidad"], value="gr").classes("flex-1")

    # BOTÓN MAESTRO DE ACCIÓN POS
    ui.button(
        "🚀 Guardar Producto en Catálogo", 
        on_click=lambda: ui.notify(f"🎉 Capturado: {nombre_input.value} - {marca_input.value}")
    ).classes("w-full mt-4 bg-blue-600 text-white")

# El comando obligatorio que enciende el servidor web interno de NiceGUI
ui.run(native=False, port=8080, reload=False)
