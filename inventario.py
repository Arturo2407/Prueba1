"""Gestor de inventario: productos organizados por categoría (Tkinter, 400x500)."""
import json
import math
import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

# Los datos se guardan junto a este script: { "Categoría": [ {nombre, caracteristicas, precio}, ... ] }
ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventario.json")


class FormularioProducto(tk.Toplevel):
    """Ventana modal para crear o modificar un producto. El resultado queda en `resultado`."""

    def __init__(self, master, titulo, producto=None):
        super().__init__(master)
        self.title(titulo)
        self.resizable(False, False)
        self.transient(master)
        self.resultado = None

        marco = ttk.Frame(self, padding=12)
        marco.pack(fill="both", expand=True)

        ttk.Label(marco, text="Nombre:").pack(anchor="w")
        self.entry_nombre = ttk.Entry(marco, width=42)
        self.entry_nombre.pack(fill="x", pady=(0, 8))

        ttk.Label(marco, text="Precio:").pack(anchor="w")
        self.entry_precio = ttk.Entry(marco, width=20)
        self.entry_precio.pack(anchor="w", pady=(0, 8))

        ttk.Label(marco, text="Características:").pack(anchor="w")
        self.texto_caract = tk.Text(marco, width=42, height=6, wrap="word")
        self.texto_caract.pack(fill="both", expand=True, pady=(0, 8))

        botones = ttk.Frame(marco)
        botones.pack(fill="x")
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(botones, text="Guardar", command=self.guardar).pack(side="right", padx=(0, 8))

        if producto:
            self.entry_nombre.insert(0, producto["nombre"])
            self.entry_precio.insert(0, f"{producto['precio']:.2f}")
            self.texto_caract.insert("1.0", producto["caracteristicas"])

        self.bind("<Escape>", lambda _evento: self.destroy())
        self.entry_nombre.focus_set()
        self.grab_set()
        self.wait_window()

    def guardar(self):
        nombre = self.entry_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Aviso", "Escribe el nombre del producto.", parent=self)
            return

        try:
            precio = float(self.entry_precio.get().replace(",", "").strip())
        except ValueError:
            precio = -1
        if not math.isfinite(precio) or precio < 0:
            messagebox.showwarning("Aviso", "Escribe un precio válido (número mayor o igual a 0).", parent=self)
            return

        self.resultado = {
            "nombre": nombre,
            "caracteristicas": self.texto_caract.get("1.0", "end").strip(),
            "precio": round(precio, 2),
        }
        self.destroy()


class Inventario(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de inventario")
        self.geometry("400x500")
        self.resizable(False, False)

        self.datos = self.cargar()
        self.crear_widgets()
        self.actualizar_categorias()

    # ----- datos -----

    def cargar(self):
        if not os.path.exists(ARCHIVO):
            return {}
        try:
            with open(ARCHIVO, "r", encoding="utf-8") as archivo:
                return json.load(archivo)
        except (OSError, json.JSONDecodeError):
            # Se sale sin sobrescribir el archivo, para no perder datos.
            messagebox.showerror("Error", f"No se pudo leer:\n{ARCHIVO}")
            raise SystemExit(1)

    def guardar(self):
        try:
            with open(ARCHIVO, "w", encoding="utf-8") as archivo:
                json.dump(self.datos, archivo, ensure_ascii=False, indent=2)
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo guardar:\n{error}", parent=self)

    # ----- interfaz -----

    def crear_widgets(self):
        # Se empaquetan primero los elementos de abajo para que no se recorten al cambiar el tamaño.
        ttk.Button(self, text="Cerrar aplicación", command=self.destroy).pack(
            side="bottom", fill="x", padx=12, pady=(10, 12))

        self.resumen = ttk.Label(self, padding=(12, 8, 12, 0))
        self.resumen.pack(side="bottom", fill="x")

        botones = ttk.Frame(self, padding=(12, 10, 12, 0))
        botones.pack(side="bottom", fill="x")
        self.btn_agregar = ttk.Button(botones, text="Agregar", command=self.agregar)
        self.btn_modificar = ttk.Button(botones, text="Modificar", command=self.modificar)
        self.btn_eliminar = ttk.Button(botones, text="Eliminar", command=self.eliminar)
        for columna, boton in enumerate((self.btn_agregar, self.btn_modificar, self.btn_eliminar)):
            botones.columnconfigure(columna, weight=1, uniform="accion")
            boton.grid(row=0, column=columna, sticky="ew", padx=(0 if columna == 0 else 6, 0))

        superior = ttk.Frame(self, padding=(12, 12, 12, 0))
        superior.pack(side="top", fill="x")
        ttk.Label(superior, text="Categoría:").pack(side="left")
        self.cbo_categorias = ttk.Combobox(superior, state="readonly", width=22)
        self.cbo_categorias.pack(side="left", padx=6)
        self.cbo_categorias.bind("<<ComboboxSelected>>", lambda _evento: self.actualizar_lista())
        self.btn_borrar_cat = ttk.Button(superior, text="Borrar", width=7, command=self.borrar_categoria)
        self.btn_borrar_cat.pack(side="right")
        ttk.Button(superior, text="Nueva", width=7, command=self.nueva_categoria).pack(side="right", padx=(0, 6))

        medio = ttk.Frame(self, padding=(12, 10, 12, 0))
        medio.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(medio, columns=("nombre", "precio", "caracteristicas"),
                                 show="headings", selectmode="browse", height=13)
        self.tree.heading("nombre", text="Producto")
        self.tree.heading("precio", text="Precio")
        self.tree.heading("caracteristicas", text="Características")
        self.tree.column("nombre", width=120, stretch=False)
        self.tree.column("precio", width=80, anchor="e", stretch=False)
        self.tree.column("caracteristicas", width=150, stretch=False)
        barra = ttk.Scrollbar(medio, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda _evento: self.actualizar_botones())
        self.tree.bind("<Double-1>", lambda _evento: self.modificar())

    def categoria_actual(self):
        return self.cbo_categorias.get() or None

    def indice_seleccionado(self):
        seleccion = self.tree.selection()
        return int(seleccion[0]) if seleccion else None

    @staticmethod
    def _habilitar(widget, activo):
        widget.state(["!disabled"] if activo else ["disabled"])

    def actualizar_botones(self):
        hay_categoria = self.categoria_actual() is not None
        hay_seleccion = self.indice_seleccionado() is not None
        self._habilitar(self.btn_borrar_cat, hay_categoria)
        self._habilitar(self.btn_agregar, hay_categoria)
        self._habilitar(self.btn_modificar, hay_seleccion)
        self._habilitar(self.btn_eliminar, hay_seleccion)

    def actualizar_categorias(self, seleccionar=None):
        nombres = list(self.datos.keys())
        self.cbo_categorias["values"] = nombres
        if seleccionar in nombres:
            self.cbo_categorias.set(seleccionar)
        elif nombres:
            self.cbo_categorias.current(0)
        else:
            self.cbo_categorias.set("")
        self.actualizar_lista()

    def actualizar_lista(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        categoria = self.categoria_actual()
        if categoria is None:
            self.resumen.config(text="Crea una categoría para empezar.")
        else:
            total = 0.0
            productos = self.datos[categoria]
            for indice, producto in enumerate(productos):
                self.tree.insert("", "end", iid=str(indice), values=(
                    producto["nombre"],
                    f"${producto['precio']:,.2f}",
                    producto["caracteristicas"].replace("\n", " / "),
                ))
                total += producto["precio"]
            self.resumen.config(text=f"{len(productos)} producto(s) · Total: ${total:,.2f}")

        self.actualizar_botones()

    def nueva_categoria(self):
        nombre = (simpledialog.askstring("Nueva categoría", "Nombre de la categoría:", parent=self) or "").strip()
        if not nombre:
            return
        if nombre in self.datos:
            messagebox.showwarning("Aviso", "Ya existe una categoría con ese nombre.", parent=self)
            return
        self.datos[nombre] = []
        self.guardar()
        self.actualizar_categorias(nombre)

    def borrar_categoria(self):
        categoria = self.categoria_actual()
        if categoria is None:
            return
        cantidad = len(self.datos[categoria])
        if not messagebox.askyesno("Confirmar",
                                   f"¿Borrar la categoría '{categoria}' y sus {cantidad} producto(s)?",
                                   parent=self):
            return
        del self.datos[categoria]
        self.guardar()
        self.actualizar_categorias()

    def agregar(self):
        categoria = self.categoria_actual()
        if categoria is None:
            return
        formulario = FormularioProducto(self, "Nuevo producto")
        if formulario.resultado:
            self.datos[categoria].append(formulario.resultado)
            self.guardar()
            self.actualizar_lista()

    def modificar(self):
        categoria = self.categoria_actual()
        indice = self.indice_seleccionado()
        if categoria is None or indice is None:
            return
        formulario = FormularioProducto(self, "Modificar producto", self.datos[categoria][indice])
        if formulario.resultado:
            self.datos[categoria][indice] = formulario.resultado
            self.guardar()
            self.actualizar_lista()
            self.tree.selection_set(str(indice))

    def eliminar(self):
        categoria = self.categoria_actual()
        indice = self.indice_seleccionado()
        if categoria is None or indice is None:
            return
        nombre = self.datos[categoria][indice]["nombre"]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el producto '{nombre}'?", parent=self):
            return
        del self.datos[categoria][indice]
        self.guardar()
        self.actualizar_lista()


if __name__ == "__main__":
    Inventario().mainloop()
