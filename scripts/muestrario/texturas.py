"""Reconoce mapas de textura por su nombre y decide cómo conectarlos.

No depende de Maya. Sirve para cualquier origen: Substance Painter (con o sin la
plantilla de Muestrario), Poly Haven, Quixel, Substance Sampler o texturas hechas
a mano, siempre que el nombre diga qué mapa es («silla_Madera_BaseColor.png»,
«rock_wall_diff_2k.jpg», «T_Caja_ORM.png»...).

Resultado de :func:`analizar`: un diccionario ``juego -> Juego``, donde un juego
de texturas es el grupo de mapas que comparten prefijo (en Painter, el nombre
del juego de texturas, que coincide con el material).
"""

import os
import re
import struct

EXTENSIONES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga", ".hdr", ".bmp")

# Tipos de mapa. Cada clave es una «entrada» de Muestrario.
# Los nombres se comparan sin separadores ni mayúsculas.
PALABRAS = [
    # (palabras, tipo)
    (("basecolor", "albedo", "diffuse", "diff", "col", "color", "colour", "basemap", "base", "dif", "alb"), "color"),
    (("roughness", "rough", "rgh"), "rugosidad"),
    (("glossiness", "gloss", "smoothness"), "brillo"),
    (("metallic", "metalness", "metal", "mtl", "met"), "metal"),
    (("normalgl", "normalopengl", "norgl", "nrmgl", "normaldx", "normaldirectx", "nordx", "nrmdx",
      "normal", "nrm", "nor", "norm", "normalmap"), "normal"),
    (("height", "displacement", "disp", "displace", "heightmap", "bump"), "altura"),
    (("ambientocclusion", "occlusion", "ao", "mixedao"), "ao"),
    (("emissive", "emission", "emit", "emissivecolor", "glow"), "emision"),
    (("opacity", "alpha", "transparency", "cutout"), "opacidad"),
    (("orm", "occlusionroughnessmetallic", "arm"), "orm"),
    (("maskmap",), "mascara_unity"),
    (("metallicsmoothness",), "metal_suavidad"),
    (("transmission", "transmissive"), "transmision"),
    (("subsurface", "sss", "scattering"), "subsuperficie"),
    (("specular", "spec", "specularlevel"), "especular"),
]
_TIPO = {}
for _palabras, _tipo in PALABRAS:
    for _p in _palabras:
        _TIPO[_p] = _tipo
_MAX_TOKENS = 3

# Entradas finales que conoce el material.
ENTRADAS = ("color", "rugosidad", "metal", "normal", "altura", "emision", "opacidad", "transmision",
            "subsuperficie", "ao")
DATOS = ("rugosidad", "metal", "normal", "altura", "opacidad", "transmision", "subsuperficie", "ao")

RE_UDIM = re.compile(r"(?:(?<=[._])|^)(1\d{3})(?=[._]|$)")
RE_UDIM_TOKEN = re.compile(r"<udim>|%\(udim\)d|\$udim|_MAPID_|\[udim\]", re.IGNORECASE)
RE_RESOLUCION = re.compile(r"^(\d+k|\d{3,5}(px)?|\d{3,5}x\d{3,5})$", re.IGNORECASE)


class Mapa(object):
    """Un archivo reconocido (o el primero de una serie UDIM)."""

    def __init__(self, ruta, tipo, prefijo, convencion=None, udim=False, patron=None):
        self.ruta = ruta
        self.nombre = os.path.basename(ruta)
        self.tipo = tipo
        self.prefijo = prefijo
        self.convencion = convencion
        self.udim = udim
        self.patron = patron or ruta
        self.tiles = []

    def __repr__(self):  # pragma: no cover
        return "Mapa({!r}, {!r})".format(self.nombre, self.tipo)


class Conexion(object):
    """Cómo se conecta un mapa a una entrada del material."""

    def __init__(self, entrada, mapa, canal=None, invertir=False, dividir_alfa=False):
        self.entrada = entrada
        self.mapa = mapa
        self.canal = canal          # None = color completo; "R", "G", "B", "A" = un canal
        self.invertir = invertir    # brillo/suavidad -> rugosidad
        # Maya lee los PNG RGBA premultiplicados: en la MaskMap de Unity el metal (R) llega
        # multiplicado por la suavidad (A). Se divide por A para recuperarlo.
        self.dividir_alfa = dividir_alfa

    @property
    def espacio(self):
        return "sRGB" if self.entrada in ("color", "emision") and self.canal is None else "Raw"

    def como_dict(self):
        return {"entrada": self.entrada, "ruta": self.mapa.patron, "nombre": self.mapa.nombre, "canal": self.canal,
                "invertir": self.invertir, "dividir_alfa": self.dividir_alfa, "espacio": self.espacio, "convencion": self.mapa.convencion,
                "udim": self.mapa.udim}


class Juego(object):
    def __init__(self, clave, nombre):
        self.clave = clave
        self.nombre = nombre
        self.mapas = {}
        self.conexiones = {}
        self.ignorados = []   # (nombre, motivo)

    def como_dict(self):
        return {"nombre": self.nombre, "conexiones": {k: c.como_dict() for k, c in self.conexiones.items()},
                "ignorados": list(self.ignorados)}


def _tokens(texto):
    partes = re.split(r"[\s_\-.]+", texto)
    return [p for p in partes if p]


def _sin_separadores(tokens):
    return "".join(tokens).lower()


def reconocer(nombre_archivo):
    """Devuelve ``(tipo, prefijo, convencion, udim, patron_nombre)`` o ``None`` si no se reconoce."""
    base, ext = os.path.splitext(nombre_archivo)
    if ext.lower() not in EXTENSIONES:
        return None
    udim = False
    patron = nombre_archivo
    m = RE_UDIM.search(base)
    if RE_UDIM_TOKEN.search(base):
        udim = True
        base = RE_UDIM_TOKEN.sub("", base)
    elif m:
        udim = True
        patron = nombre_archivo[:m.start()] + "<UDIM>" + nombre_archivo[m.end():]
        base = base[:m.start()] + base[m.end():]
    tokens = _tokens(base)
    # Se quitan sufijos de resolución («2k», «4096») al final.
    while tokens and RE_RESOLUCION.match(tokens[-1]) and len(tokens) > 1:
        tokens = tokens[:-1]
    if not tokens:
        return None
    convencion = None
    # Se busca el tipo desde el final, probando grupos de hasta 3 palabras
    # («base_color», «ambient_occlusion», «normal_opengl»).
    for fin in range(len(tokens), 0, -1):
        for largo in range(min(_MAX_TOKENS, fin), 0, -1):
            inicio = fin - largo
            palabra = _sin_separadores(tokens[inicio:fin])
            tipo = _TIPO.get(palabra)
            if tipo:
                if palabra in ("col", "base", "met", "dif") and inicio == 0:
                    continue  # el nombre empieza por esa palabra: no es un sufijo
                resto = [t.lower() for t in tokens[fin:]]
                if tipo == "normal":
                    convencion = _convencion(palabra, resto)
                prefijo = "_".join(tokens[:inicio])
                return tipo, prefijo, convencion, udim, patron
    return None


def _convencion(palabra, resto):
    texto = palabra + "".join(resto)
    if "directx" in texto or texto.endswith("dx") or "dx" in resto:
        return "directx"
    if "opengl" in texto or texto.endswith("gl") or "gl" in resto or "ogl" in resto:
        return "opengl"
    return None


def nombre_juego(prefijo):
    """«silla_Madera» -> «Madera». Painter nombra los mapas <malla>_<juego>_<mapa>."""
    if not prefijo:
        return ""
    return prefijo.split("_")[-1]


def analizar(rutas, normal_por_defecto="opengl", empaquetado=None):
    """Agrupa los archivos en juegos de texturas y decide las conexiones.

    ``empaquetado``: si el usuario sabe de dónde viene (``unreal``, ``unity``, ``gltf``)
    y el nombre es ambiguo («_Mask»), se usa para leer los canales.
    """
    juegos = {}
    vistos = set()
    for ruta in sorted(rutas):
        nombre = os.path.basename(ruta)
        if nombre.startswith("."):
            continue
        if nombre.lower().endswith(".tx"):
            continue
        r = reconocer(nombre)
        if r is None:
            continue
        tipo, prefijo, convencion, udim, patron = r
        clave = prefijo.lower()
        juego = juegos.get(clave)
        if juego is None:
            juego = juegos[clave] = Juego(clave, nombre_juego(prefijo) or prefijo or "Textura")
        ruta_patron = os.path.join(os.path.dirname(ruta), patron)
        if (clave, tipo) in vistos:
            existente = juego.mapas[tipo]
            if udim and existente.udim and existente.patron == ruta_patron:
                existente.tiles.append(ruta)
            else:
                juego.ignorados.append((nombre, "duplicado"))
            continue
        vistos.add((clave, tipo))
        mapa = Mapa(ruta, tipo, prefijo, convencion or (normal_por_defecto if tipo == "normal" else None), udim,
                    ruta_patron)
        mapa.tiles.append(ruta)
        juego.mapas[tipo] = mapa
    for juego in juegos.values():
        _decidir(juego, empaquetado)
    return juegos


def _decidir(juego, empaquetado):
    m = juego.mapas
    c = juego.conexiones
    for tipo in ("color", "rugosidad", "metal", "normal", "altura", "emision", "opacidad", "transmision",
                 "subsuperficie"):
        if tipo in m:
            c[tipo] = Conexion(tipo, m[tipo])
    if "rugosidad" not in c and "brillo" in m:
        c["rugosidad"] = Conexion("rugosidad", m["brillo"], invertir=True)
    elif "brillo" in m:
        juego.ignorados.append((m["brillo"].nombre, "brillo_sobra"))
    if "orm" in m:
        # Unreal y glTF: R oclusión, G rugosidad, B metal (Poly Haven «ARM» igual).
        if "rugosidad" not in c:
            c["rugosidad"] = Conexion("rugosidad", m["orm"], canal="G")
        if "metal" not in c:
            c["metal"] = Conexion("metal", m["orm"], canal="B")
    for tipo in ("mascara_unity", "metal_suavidad"):
        if tipo in m:
            if "metal" not in c:
                c["metal"] = Conexion("metal", m[tipo], canal="R", dividir_alfa=True)
            if "rugosidad" not in c:
                c["rugosidad"] = Conexion("rugosidad", m[tipo], canal="A", invertir=True)
    if "ao" in m:
        juego.ignorados.append((m["ao"].nombre, "ao"))
    if "especular" in m:
        juego.ignorados.append((m["especular"].nombre, "especular"))
    if "color" in c and "opacidad" not in c and empaquetado == "alfa_en_color":
        c["opacidad"] = Conexion("opacidad", m["color"], canal="A")


def buscar_material(nombre_juego_, materiales):
    """El material de la lista cuyo nombre coincide con el juego («Madera» ~ «M_Madera», «madera_mat»)."""
    def limpio(texto):
        t = texto.lower().split(":")[-1]
        for quitar in ("m_", "mat_", "mtl_"):
            if t.startswith(quitar):
                t = t[len(quitar):]
        for quitar in ("_mat", "_mtl", "_material", "_sg", "sg"):
            if t.endswith(quitar):
                t = t[:-len(quitar)]
        return t.replace("_", "")
    objetivo = limpio(nombre_juego_)
    if not objetivo:
        return None
    for material in materiales:
        if limpio(material) == objetivo:
            return material
    return None


# --- Tamaño de imagen (solo cabecera, sin librerías) -----------------------------------------

def tamano_imagen(ruta):
    """(ancho, alto) de un PNG, JPEG, TGA o BMP leyendo solo la cabecera; None si no se sabe."""
    try:
        with open(ruta, "rb") as f:
            cabeza = f.read(32)
            if cabeza.startswith(b"\x89PNG\r\n\x1a\n") and cabeza[12:16] == b"IHDR":
                return struct.unpack(">II", cabeza[16:24])
            if cabeza.startswith(b"BM"):
                ancho, alto = struct.unpack("<ii", cabeza[18:26])
                return ancho, abs(alto)
            if cabeza[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marca = f.read(2)
                    if len(marca) < 2 or marca[0] != 0xFF:
                        return None
                    while marca[1] == 0xFF:
                        marca = marca[:1] + f.read(1)
                    if marca[1] in (0xD8, 0x01) or 0xD0 <= marca[1] <= 0xD7:
                        continue
                    largo = struct.unpack(">H", f.read(2))[0]
                    if 0xC0 <= marca[1] <= 0xCF and marca[1] not in (0xC4, 0xC8, 0xCC):
                        datos = f.read(5)
                        alto, ancho = struct.unpack(">HH", datos[1:5])
                        return ancho, alto
                    f.seek(largo - 2, 1)
            if ruta.lower().endswith(".tga") and len(cabeza) >= 16:
                return struct.unpack("<HH", cabeza[12:16])
    except (OSError, struct.error):
        return None
    return None


def listar_imagenes(carpeta, recursivo=False):
    salida = []
    if not carpeta or not os.path.isdir(carpeta):
        return salida
    if recursivo:
        for raiz, _carpetas, archivos in os.walk(carpeta):
            salida.extend(os.path.join(raiz, a) for a in archivos)
    else:
        salida = [os.path.join(carpeta, a) for a in os.listdir(carpeta)]
    return sorted(r for r in salida if os.path.splitext(r)[1].lower() in EXTENSIONES and os.path.isfile(r))


# --- Rutas ---------------------------------------------------------------------------------

def relativa_al_proyecto(ruta, proyecto):
    """Ruta relativa a la carpeta del proyecto de Maya si está dentro; si no, la misma."""
    if not ruta or not proyecto:
        return ruta
    ruta_n = os.path.normcase(os.path.normpath(os.path.abspath(ruta)))
    proy_n = os.path.normcase(os.path.normpath(os.path.abspath(proyecto)))
    if ruta_n.startswith(proy_n + os.sep):
        return os.path.relpath(os.path.abspath(ruta), os.path.abspath(proyecto)).replace("\\", "/")
    return ruta


def buscar_por_nombre(nombre, carpetas):
    """Busca un archivo perdido por su nombre en varias carpetas (recursivo). Devuelve la ruta o None."""
    nombre_l = nombre.lower()
    for carpeta in carpetas:
        if not carpeta or not os.path.isdir(carpeta):
            continue
        for raiz, _carpetas, archivos in os.walk(carpeta):
            for archivo in archivos:
                if archivo.lower() == nombre_l:
                    return os.path.join(raiz, archivo)
    return None


def nombre_de_ruta(ruta):
    """Nombre de archivo de una ruta escrita en Windows o en Mac, desde cualquiera de los dos."""
    return re.split(r"[\\/]", ruta or "")[-1]
