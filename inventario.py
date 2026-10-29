"""Gestor de inventario: familia > subfamilia > categoría > almacén > artículo (Tkinter, 400x500)."""
import json
import math
import os
import shutil
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

# Los datos se guardan junto a este script.
# {
#   "almacenes": { "PV01": "Sucursal Centro", ... },
#   "familias": {
#     "Familia": { "subfamilias": { "Subfamilia": { "categorias": {
#         "Categoría": { "PV01": [ {nombre, precio, stock, unidad}, ... ] } } } } }
#   }
# }
ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventario.json")
UNIDADES = ["pza", "kg", "lt", "caja", "m", "par"]


def _fijar(combo, valores, seleccion=None):
    """Llena un combobox y deja seleccionado `seleccion` (o el primero si no existe)."""
    combo["values"] = valores
    if seleccion in valores:
        combo.set(seleccion)
    elif valores:
        combo.current(0)
    else:
        combo.set("")


def _contar(nodo):
    """Cuenta los artículos que cuelgan de un nodo del árbol."""
    if isinstance(nodo, list):
        return len(nodo)
    return sum(_contar(hijo) for hijo in nodo.values())


class FormularioArticulo(tk.Toplevel):
    """Ventana modal para crear o modificar un artículo. El resultado queda en `resultado`."""

    def __init__(self, master, titulo, articulo=None):
        super().__init__(master)
        self.title(titulo)
        self.resizable(False, False)
        self.transient(master)
        self.resultado = None

        marco = ttk.Frame(self, padding=12)
        marco.pack(fill="both", expand=True)

        ttk.Label(marco, text="Artículo:").pack(anchor="w")
        self.entry_nombre = ttk.Entry(marco, width=40)
        self.entry_nombre.pack(fill="x", pady=(0, 8))

        ttk.Label(marco, text="Ud. (precio por unidad):").pack(anchor="w")
        self.entry_precio = ttk.Entry(marco, width=20)
        self.entry_precio.pack(anchor="w", pady=(0, 8))

        ttk.Label(marco, text="Stock:").pack(anchor="w")
        self.entry_stock = ttk.Entry(marco, width=20)
        self.entry_stock.pack(anchor="w", pady=(0, 8))

        ttk.Label(marco, text="Unidad:").pack(anchor="w")
        self.cbo_unidad = ttk.Combobox(marco, values=UNIDADES, width=18)
        self.cbo_unidad.set("pza")
        self.cbo_unidad.pack(anchor="w", pady=(0, 12))

        botones = ttk.Frame(marco)
        botones.pack(fill="x")
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(botones, text="Guardar", command=self.guardar).pack(side="right", padx=(0, 8))

        if articulo:
            self.entry_nombre.insert(0, articulo["nombre"])
            self.entry_precio.insert(0, f"{articulo['precio']:.2f}")
            self.entry_stock.insert(0, str(articulo["stock"]))
            self.cbo_unidad.set(articulo["unidad"])

        self.bind("<Escape>", lambda _evento: self.destroy())
        self.entry_nombre.focus_set()
        self.grab_set()
        self.wait_window()

    def guardar(self):
        nombre = self.entry_nombre.get().strip()
        if not nombre:
            messagebox.showwarning("Aviso", "Escribe el nombre del artículo.", parent=self)
            return

        try:
            precio = float(self.entry_precio.get().replace(",", "").strip())
        except ValueError:
            precio = -1
        if not math.isfinite(precio) or precio < 0:
            messagebox.showwarning("Aviso", "Escribe un precio válido (número mayor o igual a 0).", parent=self)
            return

        try:
            stock = int(self.entry_stock.get().strip())
        except ValueError:
            stock = -1
        if stock < 0:
            messagebox.showwarning("Aviso", "Escribe un stock válido (número entero mayor o igual a 0).", parent=self)
            return

        unidad = self.cbo_unidad.get().strip()
        if not unidad:
            messagebox.showwarning("Aviso", "Escribe la unidad (por ejemplo: pza, kg).", parent=self)
            return

        self.resultado = {
            "nombre": nombre,
            "precio": round(precio, 2),
            "stock": stock,
            "unidad": unidad,
        }
        self.destroy()


class Inventario(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de inventario")
        self.geometry("400x500")
        self.resizable(False, False)

        self.datos = self.cargar()
        self.almacenes_por_texto = {}
        self.crear_widgets()
        self.actualizar_almacenes()
        self.actualizar_familias()

    # ----- datos -----

    def cargar(self):
        if not os.path.exists(ARCHIVO):
            return {"almacenes": {}, "familias": {}}
        try:
            with open(ARCHIVO, "r", encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError):
            # Se sale sin sobrescribir el archivo, para no perder datos.
            messagebox.showerror("Error", f"No se pudo leer:\n{ARCHIVO}")
            raise SystemExit(1)

        if "familias" not in datos:
            return self.migrar(datos)
        return datos

    def migrar(self, viejo):
        """Convierte el formato anterior (categoría -> productos) al nuevo, guardando una copia."""
        if viejo:
            shutil.copy(ARCHIVO, ARCHIVO + ".bak")
        nuevo = {"almacenes": {"PV01": "General"}, "familias": {}}
        if viejo:
            categorias = {}
            for categoria, productos in viejo.items():
                categorias[categoria] = {"PV01": [
                    {"nombre": p["nombre"], "precio": p["precio"], "stock": 0, "unidad": "pza"}
                    for p in productos
                ]}
            nuevo["familias"]["General"] = {"subfamilias": {"General": {"categorias": categorias}}}
        return nuevo

    def guardar(self):
        try:
            with open(ARCHIVO, "w", encoding="utf-8") as archivo:
                json.dump(self.datos, archivo, ensure_ascii=False, indent=2)
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo guardar:\n{error}", parent=self)

    def familias(self):
        return self.datos["familias"]

    def ruta(self):
        """Devuelve (familia, subfamilia, categoría, código de almacén) o None si falta algún nivel."""
        fam, sub = self.cbo_fam.get(), self.cbo_sub.get()
        cat, alm = self.cbo_cat.get(), self.cbo_alm.get()
        if not (fam and sub and cat and alm):
            return None
        return fam, sub, cat, self.almacenes_por_texto[alm]

    def nodo_articulos(self, crear=False):
        ruta = self.ruta()
        if ruta is None:
            return None
        fam, sub, cat, codigo = ruta
        categorias = self.familias()[fam]["subfamilias"][sub]["categorias"][cat]
        if crear:
            return categorias.setdefault(codigo, [])
        return categorias.get(codigo, [])

    # ----- interfaz -----

    def crear_widgets(self):
        # Se empaquetan primero los elementos de abajo para que no se recorten al cambiar el tamaño.
        ttk.Button(self, text="Cerrar aplicación", command=self.destroy).pack(
            side="bottom", fill="x", padx=12, pady=(8, 12))

        self.resumen = ttk.Label(self, padding=(12, 6, 12, 0))
        self.resumen.pack(side="bottom", fill="x")

        botones = ttk.Frame(self, padding=(12, 8, 12, 0))
        botones.pack(side="bottom", fill="x")
        self.btn_agregar = ttk.Button(botones, text="Agregar", command=self.agregar)
        self.btn_modificar = ttk.Button(botones, text="Modificar", command=self.modificar)
        self.btn_eliminar = ttk.Button(botones, text="Eliminar", command=self.eliminar)
        for columna, boton in enumerate((self.btn_agregar, self.btn_modificar, self.btn_eliminar)):
            botones.columnconfigure(columna, weight=1, uniform="accion")
            boton.grid(row=0, column=columna, sticky="ew", padx=(0 if columna == 0 else 6, 0))

        self.superior = ttk.Frame(self, padding=(12, 10, 12, 0))
        self.superior.pack(side="top", fill="x")
        self.superior.columnconfigure(1, weight=1)

        self.cbo_fam = ttk.Combobox(self.superior, state="readonly")
        self.cbo_sub = ttk.Combobox(self.superior, state="readonly")
        self.cbo_cat = ttk.Combobox(self.superior, state="readonly")
        self.cbo_alm = ttk.Combobox(self.superior, state="readonly")
        self.cbo_fam.bind("<<ComboboxSelected>>", lambda _e: self.actualizar_subfamilias())
        self.cbo_sub.bind("<<ComboboxSelected>>", lambda _e: self.actualizar_categorias())
        self.cbo_cat.bind("<<ComboboxSelected>>", lambda _e: self.actualizar_lista())
        self.cbo_alm.bind("<<ComboboxSelected>>", lambda _e: self.actualizar_lista())

        self.fila_nivel("Familia:", 0, self.cbo_fam, self.nueva_familia, self.borrar_familia)
        self.fila_nivel("Subfamilia:", 1, self.cbo_sub, self.nueva_subfamilia, self.borrar_subfamilia)
        self.fila_nivel("Categoría:", 2, self.cbo_cat, self.nueva_categoria, self.borrar_categoria)
        self.fila_nivel("Almacén:", 3, self.cbo_alm, self.nuevo_almacen)

        medio = ttk.Frame(self, padding=(12, 8, 12, 0))
        medio.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(medio, columns=("articulo", "ud", "stock", "unidad"),
                                 show="headings", selectmode="browse", height=9)
        self.tree.heading("articulo", text="Artículo")
        self.tree.heading("ud", text="Ud.")
        self.tree.heading("stock", text="Stock")
        self.tree.heading("unidad", text="Unidad")
        self.tree.column("articulo", width=150, stretch=False)
        self.tree.column("ud", width=85, anchor="e", stretch=False)
        self.tree.column("stock", width=60, anchor="e", stretch=False)
        self.tree.column("unidad", width=60, stretch=False)
        barra = ttk.Scrollbar(medio, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.actualizar_botones())
        self.tree.bind("<Double-1>", lambda _e: self.modificar())

    def fila_nivel(self, texto, fila, combo, nuevo, borrar=None):
        ttk.Label(self.superior, text=texto, width=10).grid(row=fila, column=0, sticky="w", pady=3)
        combo.grid(row=fila, column=1, sticky="ew", padx=6, pady=3)
        ttk.Button(self.superior, text="Nuevo", width=7, command=nuevo).grid(row=fila, column=2, pady=3)
        if borrar:
            ttk.Button(self.superior, text="Borrar", width=7, command=borrar).grid(
                row=fila, column=3, padx=(6, 0), pady=3)

    @staticmethod
    def _habilitar(widget, activo):
        widget.state(["!disabled"] if activo else ["disabled"])

    def indice_seleccionado(self):
        seleccion = self.tree.selection()
        return int(seleccion[0]) if seleccion else None

    def actualizar_botones(self):
        hay_ruta = self.ruta() is not None
        hay_seleccion = self.indice_seleccionado() is not None
        self._habilitar(self.btn_agregar, hay_ruta)
        self._habilitar(self.btn_modificar, hay_seleccion)
        self._habilitar(self.btn_eliminar, hay_seleccion)

    def actualizar_familias(self, seleccion=None):
        _fijar(self.cbo_fam, list(self.familias()), seleccion)
        self.actualizar_subfamilias()

    def actualizar_subfamilias(self, seleccion=None):
        fam = self.cbo_fam.get()
        subs = list(self.familias()[fam]["subfamilias"]) if fam else []
        _fijar(self.cbo_sub, subs, seleccion)
        self.actualizar_categorias()

    def actualizar_categorias(self, seleccion=None):
        fam, sub = self.cbo_fam.get(), self.cbo_sub.get()
        cats = list(self.familias()[fam]["subfamilias"][sub]["categorias"]) if fam and sub else []
        _fijar(self.cbo_cat, cats, seleccion)
        self.actualizar_lista()

    def actualizar_almacenes(self, codigo=None):
        self.almacenes_por_texto = {f"{c} - {e}": c for c, e in self.datos["almacenes"].items()}
        texto = next((t for t, c in self.almacenes_por_texto.items() if c == codigo), None)
        _fijar(self.cbo_alm, list(self.almacenes_por_texto), texto)
        self.actualizar_lista()

    def actualizar_lista(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        articulos = self.nodo_articulos() or []
        valor = 0.0
        for indice, articulo in enumerate(articulos):
            self.tree.insert("", "end", iid=str(indice), values=(
                articulo["nombre"],
                f"${articulo['precio']:,.2f}",
                articulo["stock"],
                articulo["unidad"],
            ))
            valor += articulo["precio"] * articulo["stock"]

        if self.ruta() is None:
            self.resumen.config(text="Elige familia, subfamilia, categoría y almacén.")
        else:
            self.resumen.config(text=f"{len(articulos)} artículo(s) · Valor en stock: ${valor:,.2f}")
        self.actualizar_botones()

    # ----- niveles: familia, subfamilia, categoría y almacén -----

    def pedir_nombre(self, titulo, pregunta):
        return (simpledialog.askstring(titulo, pregunta, parent=self) or "").strip()

    def nueva_familia(self):
        nombre = self.pedir_nombre("Nueva familia", "Nombre de la familia:")
        if not nombre:
            return
        if nombre in self.familias():
            messagebox.showwarning("Aviso", "Ya existe esa familia.", parent=self)
            return
        self.familias()[nombre] = {"subfamilias": {}}
        self.guardar()
        self.actualizar_familias(nombre)

    def borrar_familia(self):
        fam = self.cbo_fam.get()
        if not fam:
            return
        cantidad = _contar(self.familias()[fam])
        if not messagebox.askyesno("Confirmar",
                                   f"¿Borrar la familia '{fam}' con todas sus subfamilias y {cantidad} artículo(s)?",
                                   parent=self):
            return
        del self.familias()[fam]
        self.guardar()
        self.actualizar_familias()

    def nueva_subfamilia(self):
        fam = self.cbo_fam.get()
        if not fam:
            messagebox.showinfo("Aviso", "Primero elige o crea una familia.", parent=self)
            return
        nombre = self.pedir_nombre("Nueva subfamilia", "Nombre de la subfamilia:")
        if not nombre:
            return
        subs = self.familias()[fam]["subfamilias"]
        if nombre in subs:
            messagebox.showwarning("Aviso", "Ya existe esa subfamilia.", parent=self)
            return
        subs[nombre] = {"categorias": {}}
        self.guardar()
        self.actualizar_subfamilias(nombre)

    def borrar_subfamilia(self):
        fam, sub = self.cbo_fam.get(), self.cbo_sub.get()
        if not sub:
            return
        cantidad = _contar(self.familias()[fam]["subfamilias"][sub])
        if not messagebox.askyesno("Confirmar",
                                   f"¿Borrar la subfamilia '{sub}' y sus {cantidad} artículo(s)?",
                                   parent=self):
            return
        del self.familias()[fam]["subfamilias"][sub]
        self.guardar()
        self.actualizar_subfamilias()

    def nueva_categoria(self):
        fam, sub = self.cbo_fam.get(), self.cbo_sub.get()
        if not sub:
            messagebox.showinfo("Aviso", "Primero elige o crea una subfamilia.", parent=self)
            return
        nombre = self.pedir_nombre("Nueva categoría", "Nombre de la categoría:")
        if not nombre:
            return
        cats = self.familias()[fam]["subfamilias"][sub]["categorias"]
        if nombre in cats:
            messagebox.showwarning("Aviso", "Ya existe esa categoría.", parent=self)
            return
        cats[nombre] = {}
        self.guardar()
        self.actualizar_categorias(nombre)

    def borrar_categoria(self):
        fam, sub, cat = self.cbo_fam.get(), self.cbo_sub.get(), self.cbo_cat.get()
        if not cat:
            return
        cantidad = _contar(self.familias()[fam]["subfamilias"][sub]["categorias"][cat])
        if not messagebox.askyesno("Confirmar",
                                   f"¿Borrar la categoría '{cat}' y sus {cantidad} artículo(s)?",
                                   parent=self):
            return
        del self.familias()[fam]["subfamilias"][sub]["categorias"][cat]
        self.guardar()
        self.actualizar_categorias()

    def nuevo_almacen(self):
        codigo = self.pedir_nombre("Nuevo almacén", "Código de punto de venta (ej. PV01):")
        if not codigo:
            return
        if codigo in self.datos["almacenes"]:
            messagebox.showwarning("Aviso", "Ya existe un almacén con ese código.", parent=self)
            return
        etiqueta = self.pedir_nombre("Nuevo almacén", "Etiqueta para identificarlo (ej. Sucursal Centro):") or codigo
        self.datos["almacenes"][codigo] = etiqueta
        self.guardar()
        self.actualizar_almacenes(codigo)

    # ----- artículos -----

    def agregar(self):
        if self.ruta() is None:
            return
        formulario = FormularioArticulo(self, "Nuevo artículo")
        if formulario.resultado:
            self.nodo_articulos(crear=True).append(formulario.resultado)
            self.guardar()
            self.actualizar_lista()

    def modificar(self):
        indice = self.indice_seleccionado()
        if indice is None:
            return
        articulos = self.nodo_articulos()
        formulario = FormularioArticulo(self, "Modificar artículo", articulos[indice])
        if formulario.resultado:
            articulos[indice] = formulario.resultado
            self.guardar()
            self.actualizar_lista()
            self.tree.selection_set(str(indice))

    def eliminar(self):
        indice = self.indice_seleccionado()
        if indice is None:
            return
        articulos = self.nodo_articulos()
        nombre = articulos[indice]["nombre"]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar el artículo '{nombre}'?", parent=self):
            return
        del articulos[indice]
        self.guardar()
        self.actualizar_lista()


if __name__ == "__main__":
    Inventario().mainloop()
