"""Motivos: estructura + acabado + proyección encima de una receta. No depende de Maya.

Un motivo es opcional y está apagado en todas las recetas. Se compone de:

- **Estructura** (ladrillo, sillería, baldosa, tablas...): solo forma. Sus mapas son
  ``altura`` y ``mascara`` (RGB sin alfa: R junta, G gris distinto por pieza, B desgaste),
  más ``zona2`` opcional (gris: dónde va el «color 2») y ``tono`` opcional (RGB alrededor
  de gris medio: matiz distinto por pieza, que tiñe el color de la receta y sigue al
  deslizador «Variación»). No llevan color propio: el color sale de la receta. La máscara nunca lleva alfa: Arnold premultiplica y un alfa vacío borraría
  las juntas.
- **Acabado** (cepillado, poro de naranja, piel de mejilla, veta de nogal...): el detalle
  fino de la superficie. Mapas ``color`` (variación alrededor de un gris medio, que
  tiñe el color de la receta), ``rugosidad`` (alrededor de 0,5), ``altura``.
- **Proyección**: cómo se pegan al objeto, siempre a tamaño real en centímetros.

El catálogo se lee de carpetas::

    <carpeta>/estructuras/<id>/motivo.json
    <carpeta>/estructuras/<id>/1k/altura.png, 1k/mascara.png, 2k/...
    <carpeta>/estructuras/<id>/miniatura.png
    <carpeta>/acabados/<id>/motivo.json, 1k/color.jpg, 1k/rugosidad.png, 1k/altura.png

``motivo.json`` (los que faltan toman su valor por defecto)::

    {"id": "ladrillo_soga", "nombre": "Ladrillo a soga", "familia": "Ladrillo y bloque",
     "tile_cm": [50, 12.5],      # medida real de la imagen entera
     "pieza_cm": 24,             # ancho de una pieza con esa medida (lo que ve el alumno)
     "relieve_cm": 1.0,          # profundidad de la junta o del relieve con relieve = 1
     "color2": false,            # usa el mapa zona2.png
     "junta": "#8f8a80",         # color de junta propuesto
     "recomendado_para": ["ladrill", "construccion"],   # trozos de nombre o familia de receta
     "etiquetas": ["fachada"], "licencia": "CC0"}

Lo que sale de aquí hacia Maya es un «plan» (:func:`plan`): rutas de los mapas elegidos
y los números que necesita la red de nodos.
"""

import copy
import hashlib
import json
import os
import re
import unicodedata

from materials import color as col

ESTRUCTURAS = "estructuras"
ACABADOS = "acabados"
TIPOS = (ESTRUCTURAS, ACABADOS)
MAPAS = {ESTRUCTURAS: ("altura", "mascara", "normal", "zona2", "tono"), ACABADOS: ("color", "rugosidad", "altura", "normal")}
OBLIGATORIOS = {ESTRUCTURAS: ("altura", "mascara"), ACABADOS: ("color", "rugosidad")}
EXTENSIONES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tx")
RESOLUCIONES = ("1k", "2k", "4k")

PROYECCIONES = ("caja", "uv", "triplanar", "planar", "cilindrica", "esferica")
PROYECCION_DEFECTO = "caja"
SOLO_RENDER = ("triplanar",)          # Arnold: no se ve en el visor ni viaja a un motor
ESCRIBEN_UV = ("caja", "planar", "cilindrica", "esferica")
ESPACIOS = ("objeto", "mundo")
EJES = ("y", "x", "z")
CONJUNTO_UV = "tt_motivo"

# Lo que cambia sin rehacer nada (conexiones vivas desde el nodo de control) y lo que
# obliga a reconstruir la red o a volver a proyectar.
EN_VIVO = ("pieza_cm", "repeticion_cm", "rotacion", "mezcla", "variacion", "relieve", "desgaste",
           "rugosidad_desgaste", "rugosidad_junta", "color2", "color_junta", "color_desgaste")
REHACER_RED = ("activo", "estructura", "acabado", "proyeccion")
REPROYECTAR = ("espacio", "eje", "azar")

DEFECTO = {
    "activo": False,            # apagado en todas las recetas: el motivo es un extra
    "estructura": "",           # "" = ninguna (solo acabado)
    "acabado": "",              # "" = el propuesto para la receta
    "proyeccion": PROYECCION_DEFECTO,
    "espacio": "objeto",
    "eje": "y",
    "azar": True,               # desfase al azar por objeto
    "pieza_cm": 0.0,            # 0 = la medida de la estructura
    "repeticion_cm": 0.0,       # 0 = la medida del acabado
    "rotacion": 0.0,            # grados
    "mezcla": 0.2,              # solo triplanar
    "variacion": 0.3,           # cuánto cambia el tono de una pieza a otra
    "relieve": 0.5,
    "desgaste": 0.15,
    "rugosidad_desgaste": 0.85,
    "rugosidad_junta": 0.9,
    "color2": "#7a6a58",
    "color_junta": "",          # "" = el propuesto por la estructura
    "color_desgaste": "#4a4036",
}
LIMITES = {
    "pieza_cm": (0.0, 10000.0), "repeticion_cm": (0.0, 10000.0), "rotacion": (-360.0, 360.0),
    "mezcla": (0.0, 1.0), "variacion": (0.0, 1.0), "relieve": (0.0, 1.0), "desgaste": (0.0, 1.0),
    "rugosidad_desgaste": (0.0, 1.0), "rugosidad_junta": (0.0, 1.0),
}
JUNTA_DEFECTO = "#8f8a80"
ALTURA_ACABADO = 0.35           # peso de la altura del acabado frente a la de la estructura

# Acabado propuesto según el nombre o la familia de la receta (el catálogo manda: si un
# acabado declara ``recomendado_para``, eso va primero). Trozos sin tildes, en minúsculas.
REGLAS_ACABADO = (
    (r"cepill|acero|inox|alumin|titanio", "cepillado"),
    (r"oro|plata|cromo|espejo|pulid|platino|mercurio|niquel", "pulido"),
    (r"oxid|envejec|herrumbre", "oxidado"),
    (r"cobre|laton|bronce", "patina_cobre"),
    (r"fundido|hierro", "fundido"),
    (r"nogal", "veta_nogal"), (r"pino|pale", "veta_pino"), (r"envejecida|quemada", "madera_envejecida"),
    (r"marmol", "marmol_veteado"), (r"granito|basalto", "granito"), (r"travertino|pomez", "travertino"),
    (r"pizarra", "pizarra"), (r"hormigon|cemento|mortero|yeso|escayola", "hormigon"),
    (r"piel clara|piel media|piel oscura|piel \(juego\)", "piel_mejilla"), (r"labios", "labios"),
    (r"\buna", "una"), (r"\bojo", "esclerotica"), (r"hoja", "venas_hoja"), (r"petalo", "petalo"),
    (r"naranja", "piel_naranja"), (r"limon", "piel_limon"), (r"manzana", "manzana"), (r"fresa", "fresa"),
    (r"platano", "platano"), (r"tomate", "tomate"), (r"corteza de pan", "corteza_pan"), (r"\bpan", "miga_pan"),
    (r"queso", "queso_curado"), (r"chocolate", "chocolate"), (r"carne", "carne_cruda"),
    (r"coche|metalizada|perlada", "piel_naranja_coche"), (r"gotele", "gotele"),
    (r"cuero|ante", "cuero_granulado"), (r"vaquero", "vaquero"), (r"lana|fieltro", "lana"),
    (r"terciopelo|pelo|piel sintetica", "terciopelo"), (r"fibra de carbono", "fibra_carbono"),
    (r"tierra|barro", "tierra_agrietada"), (r"arena|grava|ceniza", "arena"), (r"musgo|hierba", "musgo"),
    (r"corteza", "corteza"), (r"agua|hielo", "ondas_agua"), (r"vidrio|cristal|lente", "huellas"),
)
ACABADO_POR_FAMILIA = {
    "metales": "cepillado", "plasticos": "plastico_satinado", "maderas": "veta_pino", "piedra": "granito",
    "construccion": "hormigon", "terreno": "tierra_agrietada", "transparentes": "huellas", "telas": "lana",
    "organicos": "piel_mejilla", "comida": "miga_pan", "pinturas": "pintura_rodillo", "luces": "pulido",
    "arcilla": "hormigon",
}


def sin_tildes(texto):
    texto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower()


def _num(valor, defecto, bajo, alto):
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return defecto
    if valor != valor:  # NaN
        return defecto
    return min(alto, max(bajo, valor))


def normalizar(motivo):
    """Copia con todos los campos y valores válidos. ``None`` o algo raro → motivo apagado."""
    m = copy.deepcopy(DEFECTO)
    if isinstance(motivo, dict):
        for clave, valor in motivo.items():
            if clave in DEFECTO:
                m[clave] = valor
    m["activo"] = bool(m["activo"])
    m["azar"] = bool(m["azar"])
    for clave in ("estructura", "acabado"):
        m[clave] = str(m[clave] or "")
    if m["proyeccion"] not in PROYECCIONES:
        m["proyeccion"] = PROYECCION_DEFECTO
    if m["espacio"] not in ESPACIOS:
        m["espacio"] = DEFECTO["espacio"]
    if m["eje"] not in EJES:
        m["eje"] = DEFECTO["eje"]
    for clave, (bajo, alto) in LIMITES.items():
        m[clave] = _num(m[clave], DEFECTO[clave], bajo, alto)
    for clave in ("color2", "color_desgaste"):
        m[clave] = m[clave].lower() if col.hex_valido(m[clave]) else DEFECTO[clave]
    m["color_junta"] = m["color_junta"].lower() if col.hex_valido(m["color_junta"]) else ""
    return m


def cambios(antes, despues):
    """Qué hay que hacer para pasar de un motivo a otro: "nada", "vivo", "reproyectar" o "red"."""
    a, b = normalizar(antes), normalizar(despues)
    distintas = [k for k in DEFECTO if a[k] != b[k]]
    if not distintas:
        return "nada"
    if any(k in REHACER_RED for k in distintas):
        return "red"
    if any(k in REPROYECTAR for k in distintas):
        return "reproyectar"
    return "vivo"


def proyeccion_valida(proyeccion, destino):
    """En videojuego no hay triplanar (no viaja al motor): se usa caja."""
    if destino == "juego" and proyeccion in SOLO_RENDER:
        return PROYECCION_DEFECTO
    return proyeccion


# --- Catálogo ---------------------------------------------------------------------------------


class Motivo(object):
    """Una estructura o un acabado del catálogo."""

    def __init__(self, tipo, carpeta, datos):
        self.tipo = tipo
        self.carpeta = carpeta
        self.datos = datos
        self.id = str(datos.get("id") or os.path.basename(carpeta))
        self.nombre = str(datos.get("nombre") or self.id.replace("_", " ").capitalize())
        self.familia = str(datos.get("familia") or "")
        tile = datos.get("tile_cm") or [100.0, 100.0]
        if not isinstance(tile, (list, tuple)):
            tile = [tile, tile]
        ancho = _num(tile[0], 100.0, 0.01, 1e6)
        alto = _num(tile[1] if len(tile) > 1 else ancho, ancho, 0.01, 1e6)
        self.tile_cm = (ancho, alto)
        self.pieza_cm = _num(datos.get("pieza_cm"), ancho, 0.01, 1e6)
        self.relieve_cm = _num(datos.get("relieve_cm"), 0.5, 0.0, 1000.0)
        self.color2 = bool(datos.get("color2", False))
        self.junta = datos.get("junta") if col.hex_valido(datos.get("junta")) else JUNTA_DEFECTO
        self.recomendado_para = [sin_tildes(x) for x in (datos.get("recomendado_para") or []) if x]
        self.etiquetas = [str(x) for x in (datos.get("etiquetas") or [])]
        self.licencia = str(datos.get("licencia") or "")
        self.prueba = bool(datos.get("prueba", False))

    def __repr__(self):
        return "Motivo({}, {})".format(self.tipo, self.id)

    def resoluciones(self):
        return [r for r in RESOLUCIONES if os.path.isdir(os.path.join(self.carpeta, r))]

    def mapa(self, nombre, resolucion="1k"):
        """Ruta del mapa en la resolución pedida, o en la más parecida que exista."""
        orden = [resolucion] + [r for r in RESOLUCIONES if r != resolucion]
        if resolucion in RESOLUCIONES:
            i = RESOLUCIONES.index(resolucion)
            # primero las menores (más ligeras), luego las mayores
            orden = [resolucion] + list(reversed(RESOLUCIONES[:i])) + list(RESOLUCIONES[i + 1:])
        for r in orden + [""]:
            for ext in EXTENSIONES:
                ruta = os.path.join(self.carpeta, r, nombre + ext)
                if os.path.isfile(ruta):
                    return ruta
        return None

    def miniatura(self):
        for ext in (".png", ".jpg", ".jpeg"):
            ruta = os.path.join(self.carpeta, "miniatura" + ext)
            if os.path.isfile(ruta):
                return ruta
        return None

    def completo(self):
        return all(self.mapa(n) for n in OBLIGATORIOS[self.tipo])

    def recomendado(self, receta):
        if not self.recomendado_para or not receta:
            return False
        texto = sin_tildes("{} {}".format(receta.get("nombre", ""), receta.get("familia", "")))
        return any(trozo in texto for trozo in self.recomendado_para)


def _leer_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else None
    except (OSError, ValueError):
        return None


class Catalogo(object):
    """Estructuras y acabados de una o varias carpetas (la primera manda si se repite un id)."""

    def __init__(self, carpetas=()):
        if isinstance(carpetas, str):
            carpetas = [carpetas]
        self.carpetas = [c for c in carpetas if c]
        self.recargar()

    def recargar(self):
        self._items = {ESTRUCTURAS: {}, ACABADOS: {}}
        for carpeta in self.carpetas:
            for tipo in TIPOS:
                base = os.path.join(carpeta, tipo)
                if not os.path.isdir(base):
                    continue
                for nombre in sorted(os.listdir(base)):
                    sub = os.path.join(base, nombre)
                    datos = _leer_json(os.path.join(sub, "motivo.json"))
                    if datos is None:
                        continue
                    item = Motivo(tipo, sub, datos)
                    if item.id not in self._items[tipo] and item.completo():
                        self._items[tipo][item.id] = item

    def __len__(self):
        return len(self._items[ESTRUCTURAS]) + len(self._items[ACABADOS])

    def estructuras(self):
        return list(self._items[ESTRUCTURAS].values())

    def acabados(self):
        return list(self._items[ACABADOS].values())

    def estructura(self, ident):
        return self._items[ESTRUCTURAS].get(ident)

    def acabado(self, ident):
        return self._items[ACABADOS].get(ident)

    def ordenados(self, tipo, receta=None):
        """Recomendados para la receta primero (★); luego por familia y nombre."""
        items = list(self._items[tipo].values())
        propuesto = acabado_propuesto(receta, self) if tipo == ACABADOS and receta else ""
        return sorted(items, key=lambda m: (0 if m.id == propuesto else 1 if m.recomendado(receta) else 2,
                                            sin_tildes(m.familia), sin_tildes(m.nombre)))

    def familias(self, tipo):
        vistas = []
        for m in self._items[tipo].values():
            if m.familia not in vistas:
                vistas.append(m.familia)
        return vistas


def acabado_propuesto(receta, catalogo):
    """Id del acabado que se propone (★) para una receta. Cualquiera se puede elegir."""
    if not receta or catalogo is None:
        return ""
    for m in catalogo.acabados():
        if m.recomendado(receta):
            return m.id
    texto = sin_tildes(receta.get("nombre", ""))
    for patron, ident in REGLAS_ACABADO:
        if re.search(patron, texto) and catalogo.acabado(ident):
            return ident
    ident = ACABADO_POR_FAMILIA.get(receta.get("familia", ""), "")
    if catalogo.acabado(ident):
        return ident
    return ""


def estructuras_recomendadas(receta, catalogo):
    return [m.id for m in catalogo.estructuras() if m.recomendado(receta)] if catalogo else []


# --- Números para la red de nodos -------------------------------------------------------------


def pieza_efectiva(motivo, estructura):
    m = normalizar(motivo)
    if estructura is None:
        return 0.0
    return m["pieza_cm"] if m["pieza_cm"] > 0 else estructura.pieza_cm


def repeticion_efectiva(motivo, acabado):
    m = normalizar(motivo)
    if acabado is None:
        return 0.0
    return m["repeticion_cm"] if m["repeticion_cm"] > 0 else acabado.tile_cm[0]


def factores(estructura, acabado, escala_uv=100.0):
    """Constantes de repetición. ``escala_uv``: centímetros que mide una unidad de UV.

    La repetición de la estructura es ``kU / pieza`` y ``kV / pieza`` (con la pieza en cm);
    la del acabado, ``aU / repeticion`` y ``aV / repeticion``. Así el deslizador de la
    pieza (en cm) se conecta en vivo a una división, sin rehacer nada.
    """
    salida = {"kU": 1.0, "kV": 1.0, "aU": 1.0, "aV": 1.0}
    if estructura is not None:
        ancho, alto = estructura.tile_cm
        salida["kU"] = escala_uv * estructura.pieza_cm / ancho
        salida["kV"] = escala_uv * estructura.pieza_cm / alto
    if acabado is not None:
        ancho, alto = acabado.tile_cm
        salida["aU"] = escala_uv
        salida["aV"] = escala_uv * ancho / alto
    return salida


def repeticiones(motivo, estructura, acabado, escala_uv=100.0):
    """Repeticiones de cada capa con los valores actuales (para pruebas y para la vista)."""
    f = factores(estructura, acabado, escala_uv)
    pieza = pieza_efectiva(motivo, estructura)
    rep = repeticion_efectiva(motivo, acabado)
    return {
        "estructura": (f["kU"] / pieza, f["kV"] / pieza) if pieza else (0.0, 0.0),
        "acabado": (f["aU"] / rep, f["aV"] / rep) if rep else (0.0, 0.0),
    }


def tamano_tile(motivo, estructura):
    """Medida real (cm) que ocupa la imagen de la estructura con la pieza elegida."""
    if estructura is None:
        return (0.0, 0.0)
    factor = pieza_efectiva(motivo, estructura) / estructura.pieza_cm
    return (estructura.tile_cm[0] * factor, estructura.tile_cm[1] * factor)


def desfase(nombre, activo=True):
    """Desfase de UV (0-1, 0-1) fijo para cada objeto: el mismo nombre da siempre el mismo."""
    if not activo:
        return (0.0, 0.0)
    h = hashlib.md5(str(nombre).encode("utf-8")).digest()
    return (h[0] / 255.0, h[1] / 255.0)


def vuelta_cerrada(circunferencia_cm, tile_cm):
    """Escala de U de una proyección cilíndrica para que la costura cierre con piezas enteras."""
    if tile_cm <= 0 or circunferencia_cm <= 0:
        return circunferencia_cm / 100.0
    vueltas = max(1, int(round(circunferencia_cm / tile_cm)))
    return vueltas * tile_cm / 100.0


def plan(motivo, catalogo, receta=None, resolucion="1k", destino="render"):
    """Todo lo que necesita Maya para montar el motivo, o None si no hay nada que montar.

    Devuelve rutas de mapas, ids y medidas. Si la estructura o el acabado no están en el
    catálogo, esa capa no se monta (y ``faltan`` lo dice).
    """
    m = normalizar(motivo)
    if not m["activo"] or catalogo is None:
        return None
    m["proyeccion"] = proyeccion_valida(m["proyeccion"], destino)
    faltan = []
    estructura = catalogo.estructura(m["estructura"]) if m["estructura"] else None
    if m["estructura"] and estructura is None:
        faltan.append(m["estructura"])
    ident_acabado = m["acabado"] or acabado_propuesto(receta, catalogo)
    acabado = catalogo.acabado(ident_acabado) if ident_acabado else None
    if m["acabado"] and acabado is None:
        faltan.append(m["acabado"])
    if estructura is None and acabado is None:
        return None
    if acabado is not None:
        m["acabado"] = acabado.id
    capas = {}
    if estructura is not None:
        capas["estructura"] = {
            "id": estructura.id, "nombre": estructura.nombre, "tile_cm": list(estructura.tile_cm),
            "pieza_cm": estructura.pieza_cm, "relieve_cm": estructura.relieve_cm, "color2": estructura.color2,
            "junta": estructura.junta,
            "mapas": {n: estructura.mapa(n, resolucion) for n in MAPAS[ESTRUCTURAS] if estructura.mapa(n, resolucion)},
        }
        if not m["pieza_cm"]:
            m["pieza_cm"] = estructura.pieza_cm
        if not m["color_junta"]:
            m["color_junta"] = estructura.junta.lower()
    if acabado is not None:
        capas["acabado"] = {
            "id": acabado.id, "nombre": acabado.nombre, "tile_cm": list(acabado.tile_cm),
            "relieve_cm": acabado.relieve_cm,
            "mapas": {n: acabado.mapa(n, resolucion) for n in MAPAS[ACABADOS] if acabado.mapa(n, resolucion)},
        }
        if not m["repeticion_cm"]:
            m["repeticion_cm"] = acabado.tile_cm[0]
    if not m["color_junta"]:
        m["color_junta"] = JUNTA_DEFECTO
    tile_u = tamano_tile(m, estructura)[0] if estructura is not None else m["repeticion_cm"]
    return {"motivo": m, "capas": capas, "faltan": faltan, "tile_u_cm": tile_u,
            "factores": factores(estructura, acabado), "resolucion": resolucion}


def resumen(motivo, catalogo):
    """Texto corto: «Ladrillo a soga · Hormigón · caja» (para la pestaña Escena)."""
    m = normalizar(motivo)
    if not m["activo"]:
        return ""
    partes = []
    e = catalogo.estructura(m["estructura"]) if catalogo and m["estructura"] else None
    a = catalogo.acabado(m["acabado"]) if catalogo and m["acabado"] else None
    if m["estructura"]:
        partes.append(e.nombre if e else m["estructura"])
    if m["acabado"]:
        partes.append(a.nombre if a else m["acabado"])
    partes.append(m["proyeccion"])
    return " · ".join(partes)
