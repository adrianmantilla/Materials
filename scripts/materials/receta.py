"""Receta de material: los valores que entiende el alumno y cómo se traducen a OpenPBR.

No depende de Maya. Una receta es un diccionario sencillo (se guarda en JSON):
los ocho controles del panel más unos pocos ajustes finos («Más…»). De aquí sale
el diccionario de atributos del nodo ``openPBRSurface`` y, al revés, una receta
a partir de los atributos de un material que ya existe.

Destinos:
- ``render``: Arnold, con todo OpenPBR (transmisión real, subsuperficie...).
- ``juego``: motores de videojuego (Unreal, Unity, glTF). Solo viaja lo que
  entiende el modelo metal/rugosidad: color, rugosidad, metal, opacidad,
  emisión y normal. Barniz, subsuperficie y pelusa se apagan y la
  transparencia pasa a opacidad.
"""

import copy
import math

from materials import color as col

RENDER = "render"
JUEGO = "juego"
DESTINOS = (RENDER, JUEGO)

# Los ocho controles del panel, en orden. «transparencia» se llama Opacidad en
# modo juego (y entonces significa cuánto se ve a través, por alfa).
CONTROLES = ("color", "rugosidad", "metal", "transparencia", "subsuperficie", "barniz", "pelusa", "emision")
DESLIZADORES = CONTROLES[1:]
SOLO_RENDER = ("subsuperficie", "barniz", "pelusa")

# Emisión: el deslizador va de 0 a 1 y se convierte en luminancia (nits) con una
# curva para que la parte baja (pilotos, pantallas) tenga recorrido.
EMISION_MAX_NITS = 1000.0   # 0,5 = 125 nits; con 5000 los neones se quemaban en Arnold

DEFECTO = {
    "nombre": "Material",
    "familia": "",
    "destinos": [RENDER, JUEGO],
    "nota": "",
    # Los ocho controles
    "color": "#cccccc",
    "rugosidad": 0.5,
    "metal": 0.0,
    "transparencia": 0.0,
    "subsuperficie": 0.0,
    "barniz": 0.0,
    "pelusa": 0.0,
    "emision": 0.0,
    # Más…
    "ior": 1.5,
    "especular": 1.0,
    "color_especular": "#ffffff",
    "anisotropia": 0.0,
    "color_transmision": None,      # None: el color base
    "profundidad_transmision": 0.0,  # cm; 0 = el color tiñe en la superficie
    "color_subsuperficie": None,
    "radio_subsuperficie": 1.0,      # cm
    "rugosidad_barniz": 0.05,
    "ior_barniz": 1.5,
    "color_barniz": "#ffffff",
    "color_pelusa": None,            # None: algo más claro que la base
    "rugosidad_pelusa": 0.5,
    "color_emision": None,           # None: el color base
    "opacidad": 1.0,                 # recorte/alfa (hojas, encaje); aparte de la transparencia
    "pared_fina": False,
    "pelicula": 0.0,                 # película fina (pompas, nácar)
    "grosor_pelicula": 500.0,        # nm
}

NUMEROS = {k: v for k, v in DEFECTO.items() if isinstance(v, float)}
LIMITES = {
    "ior": (1.0, 3.0), "radio_subsuperficie": (0.0, 100.0), "profundidad_transmision": (0.0, 1000.0),
    "ior_barniz": (1.0, 3.0), "grosor_pelicula": (0.0, 2000.0),
}


def nueva(**valores):
    receta = copy.deepcopy(DEFECTO)
    receta.update(valores)
    return normalizar(receta)


def normalizar(receta):
    """Devuelve una copia con todos los campos, números dentro de rango y colores válidos."""
    r = copy.deepcopy(DEFECTO)
    if isinstance(receta, dict):
        for clave, valor in receta.items():
            if clave in DEFECTO or clave in ("id", "origen", "etiquetas", "motivo"):
                r[clave] = valor
    for clave in NUMEROS:
        try:
            valor = float(r[clave])
        except (TypeError, ValueError):
            valor = DEFECTO[clave]
        if math.isnan(valor):
            valor = DEFECTO[clave]
        bajo, alto = LIMITES.get(clave, (0.0, 1.0))
        r[clave] = min(alto, max(bajo, valor))
    for clave in ("color", "color_especular", "color_barniz"):
        if not col.hex_valido(r[clave]):
            r[clave] = DEFECTO[clave]
        r[clave] = r[clave].lower()
    for clave in ("color_transmision", "color_subsuperficie", "color_pelusa", "color_emision"):
        if r[clave] is not None and not col.hex_valido(r[clave]):
            r[clave] = None
        elif r[clave]:
            r[clave] = r[clave].lower()
    destinos = [d for d in (r.get("destinos") or []) if d in DESTINOS]
    r["destinos"] = destinos or [RENDER, JUEGO]
    r["pared_fina"] = bool(r["pared_fina"])
    r["nombre"] = str(r["nombre"] or "Material")
    return r


def sirve_para(receta, destino):
    return destino in receta.get("destinos", DESTINOS)


def emision_a_nits(valor):
    valor = min(1.0, max(0.0, valor))
    return 0.0 if valor <= 0 else EMISION_MAX_NITS * valor ** 3


def nits_a_emision(nits):
    if nits <= 0:
        return 0.0
    return min(1.0, (nits / EMISION_MAX_NITS) ** (1.0 / 3.0))


def para_juego(receta):
    """Versión de la receta que se puede llevar a un motor (modelo metal/rugosidad)."""
    r = normalizar(receta)
    if r["transparencia"] > 0:
        # Un vidrio de motor es un material translúcido con poco alfa.
        r["opacidad"] = min(r["opacidad"], max(0.1, 1.0 - 0.85 * r["transparencia"]))
        r["transparencia"] = 0.0
    r["metal"] = 1.0 if r["metal"] >= 0.5 else 0.0
    for clave in SOLO_RENDER:
        r[clave] = 0.0
    r["pelicula"] = 0.0
    r["anisotropia"] = 0.0
    return r


def _rgb(hex_o_none, respaldo):
    return col.hex_a_lineal(hex_o_none or respaldo)


def atributos_openpbr(receta, destino=RENDER):
    """Diccionario atributo de ``openPBRSurface`` -> valor (floats o tuplas lineales)."""
    r = para_juego(receta) if destino == JUEGO else normalizar(receta)
    base = col.hex_a_lineal(r["color"])
    pelusa = r["color_pelusa"] or col.aclarar_hex(r["color"], 0.25)
    a = {
        "baseWeight": 1.0,
        "baseColor": base,
        "baseMetalness": r["metal"],
        "baseDiffuseRoughness": round(r["rugosidad"] * 0.3, 4) if r["metal"] < 1 else 0.0,
        "specularWeight": r["especular"],
        "specularColor": col.hex_a_lineal(r["color_especular"]),
        "specularRoughness": r["rugosidad"],
        "specularIOR": r["ior"],
        "specularRoughnessAnisotropy": r["anisotropia"],
        "transmissionWeight": r["transparencia"],
        "transmissionColor": _rgb(r["color_transmision"], r["color"]),
        "transmissionDepth": r["profundidad_transmision"],
        "subsurfaceWeight": r["subsuperficie"],
        "subsurfaceColor": _rgb(r["color_subsuperficie"], r["color"]),
        "subsurfaceRadius": r["radio_subsuperficie"],
        "coatWeight": r["barniz"],
        "coatColor": col.hex_a_lineal(r["color_barniz"]),
        "coatRoughness": r["rugosidad_barniz"],
        "coatIOR": r["ior_barniz"],
        "fuzzWeight": r["pelusa"],
        "fuzzColor": col.hex_a_lineal(pelusa),
        "fuzzRoughness": r["rugosidad_pelusa"],
        "emissionLuminance": emision_a_nits(r["emision"]),
        "emissionColor": _rgb(r["color_emision"], r["color"]),
        "thinFilmWeight": r["pelicula"],
        "thinFilmThickness": r["grosor_pelicula"],
        "geometryOpacity": r["opacidad"],
        "geometryThinWalled": r["pared_fina"],
    }
    return a


def _hex_de(valor):
    return col.lineal_a_hex(valor) if isinstance(valor, (tuple, list)) and len(valor) == 3 else None


def desde_atributos(atributos, nombre="Material"):
    """Receta a partir de los atributos leídos de un ``openPBRSurface`` (los que falten, por defecto)."""
    g = atributos.get
    r = nueva(nombre=nombre)
    if _hex_de(g("baseColor")):
        r["color"] = _hex_de(g("baseColor"))
    pares = {
        "rugosidad": "specularRoughness", "metal": "baseMetalness", "transparencia": "transmissionWeight",
        "subsuperficie": "subsurfaceWeight", "barniz": "coatWeight", "pelusa": "fuzzWeight", "ior": "specularIOR",
        "especular": "specularWeight", "anisotropia": "specularRoughnessAnisotropy",
        "profundidad_transmision": "transmissionDepth", "radio_subsuperficie": "subsurfaceRadius",
        "rugosidad_barniz": "coatRoughness", "ior_barniz": "coatIOR", "rugosidad_pelusa": "fuzzRoughness",
        "opacidad": "geometryOpacity", "pelicula": "thinFilmWeight", "grosor_pelicula": "thinFilmThickness",
    }
    for clave, atributo in pares.items():
        if isinstance(g(atributo), (int, float)) and not isinstance(g(atributo), bool):
            r[clave] = float(g(atributo))
    if isinstance(g("emissionLuminance"), (int, float)):
        r["emision"] = nits_a_emision(float(g("emissionLuminance")))
    r["pared_fina"] = bool(g("geometryThinWalled", False))
    for clave, atributo in (("color_especular", "specularColor"), ("color_barniz", "coatColor")):
        if _hex_de(g(atributo)):
            r[clave] = _hex_de(g(atributo))
    # Colores que solo se guardan si no coinciden con la base.
    for clave, atributo in (("color_transmision", "transmissionColor"), ("color_subsuperficie", "subsurfaceColor"),
                            ("color_emision", "emissionColor"), ("color_pelusa", "fuzzColor")):
        valor = _hex_de(g(atributo))
        if valor and valor != r["color"]:
            r[clave] = valor
    if r["color_pelusa"] == col.aclarar_hex(r["color"], 0.25):
        r["color_pelusa"] = None
    return normalizar(r)


def nombre_material(nombre):
    """«Pintura de coche» -> «M_Pintura_de_coche» (sin tildes ni espacios, válido en Maya)."""
    import unicodedata
    texto = unicodedata.normalize("NFD", str(nombre))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    limpio = "".join(c if c.isalnum() else "_" for c in texto).strip("_")
    while "__" in limpio:
        limpio = limpio.replace("__", "_")
    if not limpio:
        limpio = "Material"
    if limpio[0].isdigit():
        limpio = "_" + limpio
    return limpio if limpio.startswith("M_") else "M_" + limpio


def diferencias(a, b, tolerancia=1e-3):
    """Claves cuyo valor cambia entre dos recetas (para avisar de cambios sin guardar)."""
    a, b = normalizar(a), normalizar(b)
    salida = []
    for clave in DEFECTO:
        x, y = a.get(clave), b.get(clave)
        if isinstance(x, float) and isinstance(y, float):
            if abs(x - y) > tolerancia:
                salida.append(clave)
        elif x != y:
            salida.append(clave)
    return salida
