"""Biblioteca de recetas: las que trae el plugin, las tuyas y las de la carpeta de clase.

No depende de Maya.
- Recetas del plugin: ``muestrario/biblioteca/NN_familia.json`` (una familia por archivo).
- Mis recetas: ``<preferencias>/recetas/*.json`` (una receta por archivo, se crean
  con «Guardar receta»).
- Recetas de clase: una carpeta que elige el profesor (por ejemplo en una unidad
  compartida). Cada archivo .json puede ser una receta o una familia entera.
"""

import json
import os
import unicodedata

from muestrario import receta as rc

CARPETA_PLUGIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biblioteca")
MIS_RECETAS = "mis_recetas"
CLASE = "clase"


class Familia(object):
    def __init__(self, clave, nombre, recetas, editable=False):
        self.clave = clave
        self.nombre = nombre
        self.recetas = recetas
        self.editable = editable


def _sin_tildes(texto):
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _recetas_de(datos, familia, origen, ruta=None):
    """Acepta un archivo de familia ({"recetas": [...]}) o una receta suelta."""
    salida = []
    if isinstance(datos, dict) and isinstance(datos.get("recetas"), list):
        lista = datos["recetas"]
    elif isinstance(datos, dict) and "nombre" in datos:
        lista = [datos]
    else:
        return salida
    for d in lista:
        if not isinstance(d, dict):
            continue
        r = rc.normalizar(d)
        r["familia"] = familia
        r["origen"] = origen
        if ruta and len(lista) == 1:
            r["id"] = ruta
        salida.append(r)
    return salida


def familias_del_plugin(carpeta=CARPETA_PLUGIN):
    familias = []
    if not os.path.isdir(carpeta):
        return familias
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith(".json"):
            continue
        datos = _leer(os.path.join(carpeta, nombre))
        if not isinstance(datos, dict):
            continue
        clave = datos.get("familia") or os.path.splitext(nombre)[0]
        familias.append(Familia(clave, datos.get("nombre", clave), _recetas_de(datos, clave, "plugin")))
    return familias


def familia_de_carpeta(carpeta, clave, nombre, editable):
    recetas = []
    if carpeta and os.path.isdir(carpeta):
        for archivo in sorted(os.listdir(carpeta)):
            if archivo.endswith(".json"):
                ruta = os.path.join(carpeta, archivo)
                recetas.extend(_recetas_de(_leer(ruta), clave, clave, ruta))
    recetas.sort(key=lambda r: _sin_tildes(r["nombre"]))
    return Familia(clave, nombre, recetas, editable)


class Biblioteca(object):
    def __init__(self, carpeta_mias=None, carpeta_clase=None, carpeta_plugin=CARPETA_PLUGIN):
        self.carpeta_mias = carpeta_mias
        self.carpeta_clase = carpeta_clase
        self.carpeta_plugin = carpeta_plugin
        self.familias = []
        self.recargar()

    def recargar(self):
        from muestrario.i18n import t
        self.familias = familias_del_plugin(self.carpeta_plugin)
        self.familias.append(familia_de_carpeta(self.carpeta_mias, MIS_RECETAS, t("familia_mias"), True))
        if self.carpeta_clase:
            self.familias.append(familia_de_carpeta(self.carpeta_clase, CLASE, t("familia_clase"), False))

    def familia(self, clave):
        for f in self.familias:
            if f.clave == clave:
                return f
        return None

    def todas(self):
        for f in self.familias:
            for r in f.recetas:
                yield r

    def total(self):
        return sum(len(f.recetas) for f in self.familias)

    def buscar(self, texto="", familia=None, destino=None):
        """Recetas que contienen todas las palabras de ``texto`` (sin tildes) en nombre, familia o nota."""
        palabras = _sin_tildes(texto).split()
        salida = []
        for f in self.familias:
            if familia and f.clave != familia:
                continue
            for r in f.recetas:
                if destino and not rc.sirve_para(r, destino):
                    continue
                donde = _sin_tildes(" ".join((r["nombre"], f.nombre, r.get("nota", ""))))
                if all(p in donde for p in palabras):
                    salida.append(r)
        return salida

    def receta(self, nombre):
        for r in self.todas():
            if r["nombre"] == nombre:
                return r
        return None

    def guardar_mia(self, receta):
        """Guarda una receta propia (sobrescribe si ya hay una con ese nombre). Devuelve la ruta."""
        if not self.carpeta_mias:
            raise OSError("sin carpeta de recetas")
        os.makedirs(self.carpeta_mias, exist_ok=True)
        r = rc.normalizar(receta)
        r["familia"] = MIS_RECETAS
        nombre_archivo = rc.nombre_material(r["nombre"])[2:] + ".json"
        ruta = os.path.join(self.carpeta_mias, nombre_archivo)
        datos = {k: r[k] for k in rc.DEFECTO}
        temporal = ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        os.replace(temporal, ruta)
        self.recargar()
        return ruta

    def borrar_mia(self, receta):
        ruta = receta.get("id")
        if ruta and self.carpeta_mias and os.path.dirname(os.path.abspath(ruta)) == os.path.abspath(self.carpeta_mias):
            try:
                os.remove(ruta)
            except OSError:
                return False
            self.recargar()
            return True
        return False
