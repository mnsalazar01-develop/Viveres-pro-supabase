import tkinter as tk
from tkinter import ttk

# Tu arreglo estático acotado en la memoria RAM del equipo
arreglo_100_nombres = ["Aceite Vegetal", "Arroz Blanco", "Azúcar Refinada", "Harina Pan", "Mayonesa Mavesa"]

def filtrar_nombres_teclado(event):
    """
    Se ejecuta letra por letra. Captura lo tipeado, busca coincidencias 
    en el arreglo y despliega el scroll nativo sin borrar tu texto.
    """
    # 1. Capturamos el texto crudo de la Caja de Trabajo en el primer plano
    texto_tipeado = combo_nombre.get()
    
    # Si la caja está vacía, restablecemos las 100 opciones originales
    if texto_tipeado == "":
        combo_nombre['values'] = arreglo_100_nombres
    else:
        # 2. Filtramos el arreglo de control en microsegundos
        coincidencias = []
        for nombre in arreglo_100_nombres:
            if texto_tipeado.lower() in nombre.lower():
                coincidencias.append(nombre)
        
        # 3. Inyectamos las sugerencias filtradas al desplegable
        combo_nombre['values'] = coincidencias
        
        # Si hay opciones válidas, abrimos el scroll flotante de forma automática
        if coincidencias:
            combo_nombre.event_generate("<Down>")

# --- CONFIGURACIÓN DEL WIDGET EN LA VENTANA ---
ventana = tk.Tk()
ventana.geometry("400x200")
ventana.configure(bg="#1e1e1e")

combo_nombre = ttk.Combobox(ventana, width=40)
combo_nombre.pack(pady=20)

# Cargamos el arreglo inicial de control
combo_nombre['values'] = arreglo_100_nombres

# EL ESCUDO INTELIGENTE: Vinculamos la lectura letra por letra al widget
combo_nombre.bind("<KeyRelease>", filtrar_nombres_teclado)

# ventana.mainloop()
