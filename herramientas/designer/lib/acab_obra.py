"""Acabados de obra y construcción: hormigones (tablilla, lavado, abujardado), morteros y yesos, pavimentos de
resina, pintura vial, podotáctiles, placas (fibrocemento, pladur, fenólico), aislantes (lana de roca, XPS),
cemento cola, encalado, tapial, adobe con paja y terrazo de grano grueso.
"""

import math

import numpy as np

from acab_terreno import esparcir
from superficie import (celdas, estirado, gris, hoyuelos, manchas_fractales, rejilla, ruido_cm, salpicado,
                        suave)


def _area(forma, cx, cy):
    return forma[1] * cx * forma[0] * cy


def _cuenta(total, paso):
    return total / max(1, round(total / paso))


def hormigon_tablilla(forma, cx, cy):
    """Hormigón visto de encofrado de tablilla: la veta de las tablas impresa, juntas finas y coqueras."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    p = _cuenta(th, 10.0)
    fila = np.floor(y / p)
    veta = estirado(forma, cx, cy, 0.6, 40001, 15.0, octavas=4)
    tono = np.random.default_rng(40002).uniform(-1, 1, int(round(th / p)) + 1)[fila.astype(int) % int(round(th / p))]
    junta = suave(0.12 - np.minimum(y % p, p - y % p), 0, 0.08)
    coquera = hoyuelos(forma, cx, cy, 0.15, 40003, 0.04)
    lum = 0.58 + 0.06 * (veta - 0.5) + 0.04 * tono - 0.15 * junta - 0.2 * coquera
    return gris(lum), 0.6 + 0.1 * coquera, 0.5 + 0.08 * (veta - 0.5) + 0.05 * junta - 0.3 * coquera


def hormigon_lavado(forma, cx, cy):
    """Hormigón lavado (árido visto): grava redondeada de colores asomando del cemento."""
    n = _area(forma, cx, cy) / 0.9

    def piedra(u, v):
        r = u * u + v * v
        return np.where(r < 1, np.sqrt(np.clip(1 - r, 0, 1)) + 1e-3, 0.0)

    cima, quien, _, _ = esparcir(forma, cx, cy, n, 0.6, 0.45, 40101, piedra, variar=0.5)
    en = quien >= 0
    pal = np.array([[0.85, 0.82, 0.78], [0.55, 0.5, 0.48], [0.75, 0.6, 0.5], [0.35, 0.34, 0.33], [0.9, 0.88, 0.85]])
    c = pal[np.random.default_rng(40102).integers(0, len(pal), int(n) + 1)][np.maximum(quien, 0)]
    color = np.where(en[..., None], c * (0.75 + 0.25 * np.clip(cima, 0, 1))[..., None], 0.55)
    return color, np.where(en, 0.4, 0.75), np.where(en, 0.3 + 0.6 * np.clip(cima, 0, 1), 0.2)


def hormigon_abujardado(forma, cx, cy):
    """Hormigón abujardado: picado fino y uniforme de la bujarda, que deja ver el árido."""
    pico = hoyuelos(forma, cx, cy, 0.12, 40201, 0.45)
    arido = salpicado(forma, cx, cy, 0.2, 40202, 0.2, borde=0.03)
    lum = 0.6 - 0.15 * pico + 0.1 * arido
    return gris(lum, (1.0, 1.0, 0.97)), 0.75 + 0.05 * pico, 0.6 - 0.4 * pico + 0.05 * arido


def mortero(forma, cx, cy):
    """Mortero de cemento: áspero, arenoso, con marcas de llana."""
    arena = ruido_cm(forma, cx, cy, 0.04, 40301, octavas=2) - 0.5
    llana = ruido_cm(forma, cx, cy, 5.0, 40302, octavas=4) - 0.5
    grumo = ruido_cm(forma, cx, cy, 0.4, 40303, octavas=2) - 0.5
    lum = 0.55 + 0.1 * arena + 0.12 * llana + 0.06 * grumo
    return gris(lum, (1.0, 0.99, 0.96)), 0.8 + 0.05 * arena, 0.5 + 0.12 * arena + 0.1 * llana + 0.1 * grumo


def yeso_proyectado(forma, cx, cy):
    """Yeso o pintura proyectada: gotitas apelmazadas en relieve (piel de naranja gruesa)."""
    g1 = hoyuelos(forma, cx, cy, 0.25, 40401, 0.5)
    g2 = hoyuelos(forma, cx, cy, 0.08, 40402, 0.4)
    alto = 0.6 * g1 + 0.4 * g2
    lum = 0.72 + 0.05 * alto
    return gris(lum), np.full(forma, 0.7), 0.3 + 0.6 * alto


def pavimento_epoxi(forma, cx, cy):
    """Pavimento de epoxi con escamas (flakes): base gris brillante con escamas de colores."""
    pal = np.array([[0.15, 0.15, 0.17], [0.9, 0.9, 0.88], [0.55, 0.55, 0.58], [0.7, 0.6, 0.45]])
    n = _area(forma, cx, cy) / 0.25

    def escama(u, v):
        return np.where(np.maximum(np.abs(u), np.abs(v)) + 0.3 * np.abs(u * v) < 1, 1.0, 0.0)

    cima, quien, _, _ = esparcir(forma, cx, cy, n, 0.3, 0.2, 40501, escama, variar=0.6)
    en = quien >= 0
    c = pal[np.random.default_rng(40502).integers(0, len(pal), int(n) + 1)][np.maximum(quien, 0)]
    color = np.where(en[..., None], c, 0.5)
    return color, np.full(forma, 0.25), np.full(forma, 0.5)


def resina_cuarzo(forma, cx, cy):
    """Resina antideslizante con árido de cuarzo: granitos en relieve bajo la capa de pintura."""
    grano = hoyuelos(forma, cx, cy, 0.06, 40601, 0.4)
    lum = 0.55 + 0.08 * grano
    return gris(lum), 0.6 + 0.1 * grano, 0.3 + 0.6 * grano


def pintura_vial(forma, cx, cy):
    """Pintura vial blanca sobre asfalto: capa gruesa con microesferas y desgaste por el tráfico."""
    arido = ruido_cm(forma, cx, cy, 0.3, 40701, octavas=3)
    gastado = manchas_fractales(forma, cx, cy, 5.0, 40702, 0.25, detalle=0.6)
    pintura = (arido > 0.3) * (1 - gastado)
    esfera = salpicado(forma, cx, cy, 0.02, 40703, 0.08, borde=0.01) * pintura
    lum = np.where(pintura > 0.5, 0.88 + 0.05 * esfera, 0.15 + 0.15 * arido)
    return gris(lum), np.where(pintura > 0.5, 0.55 - 0.2 * esfera, 0.8), 0.4 + 0.4 * arido + 0.05 * pintura


def podotactil_botones(forma, cx, cy):
    """Pavimento podotáctil de botones (aviso): cúpulas truncadas en rejilla."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = _cuenta(tw, 5.0)
    d = np.hypot((x % p) - p / 2, (y % p) - p / 2)
    boton = np.clip((1.25 - d) / 0.4, 0, 1)
    grano = ruido_cm(forma, cx, cy, 0.05, 40801, octavas=2) - 0.5
    lum = 0.55 + 0.05 * grano + 0.05 * boton
    return gris(lum), 0.7, 0.15 + 0.8 * boton + 0.03 * grano


def podotactil_barras(forma, cx, cy):
    """Pavimento podotáctil de barras (direccional): nervios alargados paralelos."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = _cuenta(tw, 5.0), _cuenta(th, 30.0)
    u = (x % px) - px / 2
    v = (y % py) - py / 2
    d = np.hypot(np.maximum(np.abs(v) - 11.0, 0), u)
    barra = np.clip((1.7 - d) / 0.5, 0, 1)
    grano = ruido_cm(forma, cx, cy, 0.05, 40901, octavas=2) - 0.5
    lum = 0.55 + 0.05 * grano + 0.05 * barra
    return gris(lum), 0.7, 0.15 + 0.8 * barra + 0.03 * grano


def fibrocemento(forma, cx, cy):
    """Placa de fibrocemento: gris claro con fibras finas y manchas de humedad."""
    fibra = estirado(forma, cx, cy, 0.03, 41001, 8.0, octavas=2) - 0.5
    nube = ruido_cm(forma, cx, cy, 10.0, 41002, octavas=4) - 0.5
    lum = 0.6 + 0.04 * fibra + 0.12 * nube
    return gris(lum), 0.75, 0.5 + 0.03 * fibra


def pladur(forma, cx, cy):
    """Placa de yeso laminado: papel liso con juntas emplastecidas y cabezas de tornillo tapadas."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    pw = _cuenta(tw, 120.0)
    junta = suave(10.0 - np.minimum(x % pw, pw - x % pw), 0, 6.0)
    pt = _cuenta(th, 30.0)
    tornillo = (np.hypot(np.minimum(x % pw, pw - x % pw) - 1.5, (y % pt) - pt / 2) < 1.5) * 1.0
    papel = ruido_cm(forma, cx, cy, 0.05, 41101, octavas=2) - 0.5
    lijado = ruido_cm(forma, cx, cy, 3.0, 41102, octavas=3) - 0.5
    pasta = np.clip(junta + tornillo, 0, 1)
    lum = 0.7 + 0.02 * papel + pasta * (0.05 + 0.06 * lijado)
    color = gris(lum) * (np.array([0.98, 0.98, 0.97]) * (1 - pasta[..., None]) + np.array([1.03, 1.03, 1.03]) * pasta[
        ..., None])
    return color, 0.65 + 0.1 * pasta, 0.5 + 0.02 * papel + 0.02 * pasta * lijado


def lana_roca(forma, cx, cy):
    """Lana de roca: fibras amarillo verdosas enmarañadas en capas, esponjosa."""
    from superficie import rayas
    f = rayas(forma, cx, cy, _area(forma, cx, cy) * 12, 2.5, 0.05, 41201, angulo=0.0, dispersion=0.8,
              curva=0.3)
    capa = estirado(forma, cx, cy, 2.0, 41202, 6.0, octavas=3)
    lum = 0.2 + 0.6 * f + 0.15 * (capa - 0.5)
    return gris(lum) * np.array([1.2, 1.1, 0.6]), 0.9, 0.3 + 0.4 * f + 0.2 * capa


def poliestireno_extruido(forma, cx, cy):
    """Poliestireno extruido (XPS): espuma de celdas finas, con la piel de extrusión lisa y algún corte."""
    celdilla = hoyuelos(forma, cx, cy, 0.05, 41301, 0.5)
    corte = estirado(forma, cx, cy, 5.0, 41302, 10.0, octavas=2)
    lum = 0.6 + 0.04 * celdilla + 0.05 * (corte - 0.5)
    return gris(lum) * np.array([1.2, 0.85, 0.9]), 0.6, 0.5 + 0.08 * celdilla


def tablero_fenolico(forma, cx, cy):
    """Tablero fenólico de encofrado: film marrón satinado sobre contrachapado, con sellos y roces."""
    veta = estirado(forma, cx, cy, 2.0, 41401, 8.0, octavas=4) - 0.5
    roce = manchas_fractales(forma, cx, cy, 6.0, 41402, 0.12, detalle=0.5)
    resto = salpicado(forma, cx, cy, 1.5, 41403, 0.06, borde=0.2)
    lum = 0.45 + 0.05 * veta + 0.15 * roce + 0.25 * resto
    color = gris(lum) * (np.array([1.3, 0.85, 0.6]) * (1 - resto[..., None]) + np.array([1.0, 1.0, 0.98]) * resto[
        ..., None])
    return color, 0.35 + 0.3 * roce + 0.3 * resto, 0.5 + 0.02 * veta + 0.05 * resto


def cemento_cola(forma, cx, cy):
    """Cemento cola peinado con llana dentada: surcos paralelos que ondulan con la mano."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    giro = (ruido_cm(forma, cx, cy, 20.0, 41501, octavas=2) - 0.5) * 8
    fase = 2 * math.pi * round(th / 1.0) * y / th + giro
    surco = 0.5 + 0.5 * np.sin(fase)
    arena = ruido_cm(forma, cx, cy, 0.04, 41502, octavas=2) - 0.5
    lum = 0.58 + 0.12 * surco + 0.05 * arena
    return gris(lum), 0.8, 0.2 + 0.7 * surco + 0.05 * arena


def encalado(forma, cx, cy):
    """Encalado: cal blanca sobre muro rugoso, con capas, desconchones y algo de piedra asomando."""
    muro = ruido_cm(forma, cx, cy, 4.0, 41601, octavas=5)
    descon = manchas_fractales(forma, cx, cy, 8.0, 41602, 0.08, detalle=0.6)
    brocha = estirado(forma, cx, cy, 1.0, 41603, 4.0, octavas=2) - 0.5
    lum = 0.85 + 0.04 * brocha - 0.4 * descon + 0.05 * (muro - 0.5)
    color = gris(lum) * (1 + descon[..., None] * np.array([0.1, 0.0, -0.15]))
    return color, 0.85, 0.3 + 0.5 * muro - 0.1 * descon


def tapial(forma, cx, cy):
    """Tapial (tierra apisonada): estratos horizontales de tierra de distintos tonos y gravilla."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    onda = (ruido_cm(forma, cx, cy, 30.0, 41701, octavas=2) - 0.5) * 6
    capa = np.sin(2 * math.pi * round(th / 12.0) * (y + onda) / th)
    banda = np.sin(2 * math.pi * round(th / 4.0) * (y + onda) / th)
    grava = salpicado(forma, cx, cy, 0.3, 41702, 0.1, borde=0.04)
    lum = 0.55 + 0.08 * capa + 0.04 * banda - 0.1 * grava
    color = gris(lum) * (np.array([1.2, 0.95, 0.72]) + 0.08 * capa[..., None] * np.array([0.5, 0.2, -0.2]))
    return color, 0.85, 0.5 + 0.05 * banda + 0.1 * grava


def adobe_paja(forma, cx, cy):
    """Barro con paja (adobe, revoco de tierra): masa parda con briznas de paja doradas."""
    from superficie import rayas
    paja = rayas(forma, cx, cy, _area(forma, cx, cy) * 1.5, 3.0, 0.08, 41801, curva=0.1)
    masa = ruido_cm(forma, cx, cy, 2.0, 41802, octavas=4) - 0.5
    lum = 0.45 + 0.1 * masa + 0.45 * paja
    color = gris(lum) * (np.array([1.2, 0.95, 0.7]) * (1 - paja[..., None]) + np.array([1.3, 1.1, 0.55]) * paja[
        ..., None])
    return color, 0.85, 0.5 + 0.15 * masa + 0.1 * paja


def terrazo_grueso(forma, cx, cy):
    """Terrazo de grano grueso (veneciano): trozos grandes de mármol de colores en cemento claro."""
    _, dist, valor = celdas(forma, cx, cy, 2.5, 41901, temblor=1.0, pesos=0.6)
    chip = suave(dist, 0.3, 0.35)
    pal = np.array([[0.85, 0.82, 0.78], [0.4, 0.38, 0.36], [0.7, 0.45, 0.4], [0.5, 0.55, 0.5], [0.95, 0.93, 0.9]])
    idx = np.clip((valor * len(pal)).astype(int), 0, len(pal) - 1)
    vena = ruido_cm(forma, cx, cy, 0.5, 41902, octavas=3) - 0.5
    color = pal[idx] * (1 + 0.1 * vena[..., None])
    color = color * chip[..., None] + np.array([0.78, 0.76, 0.72]) * (1 - chip[..., None])
    return color, 0.3, 0.5 + 0.01 * chip


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.75, familia="Obra", **kw):
    def f(forma, cx, cy):
        r = funcion(forma, cx, cy, **kw)
        color = np.clip(r[0] * (0.5 / max(1e-6, float(r[0].mean()))), 0.0, 1.0)
        rug_ = np.clip(np.broadcast_to(np.asarray(r[1], dtype=np.float64), forma), 0.0, 1.0)
        rug_ = np.clip(rug_ + (0.5 - float(rug_.mean())), 0.0, 1.0)
        return (color, rug_) + tuple(r[2:])

    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


ACABADOS = [
    _a("hormigon_tablilla", hormigon_tablilla, "Hormigón de encofrado de tablilla", (120.0, 120.0), 0.3,
       "#a09c96", ["hormigon visto", "tablilla", "encofrado"]),
    _a("hormigon_lavado", hormigon_lavado, "Hormigón lavado (árido visto)", (30.0, 30.0), 0.4, "#a8a49c",
       ["arido visto", "hormigon lavado", "acera"], rug=0.7),
    _a("hormigon_abujardado", hormigon_abujardado, "Hormigón abujardado", (30.0, 30.0), 0.15, "#b0aca4",
       ["abujardado", "hormigon", "escalon"], rug=0.85),
    _a("mortero", mortero, "Mortero de cemento", (60.0, 60.0), 0.1, "#9a968e", ["mortero", "cemento", "revoco"],
       rug=0.9),
    _a("yeso_proyectado", yeso_proyectado, "Yeso proyectado", (20.0, 20.0), 0.2, "#e0ddd6", ["proyectado",
       "techo", "piel de naranja"], rug=0.85),
    _a("pavimento_epoxi", pavimento_epoxi, "Pavimento de epoxi con escamas", (20.0, 20.0), 0.0, "#8a8c90",
       ["epoxi", "garaje", "taller"], rug=0.2),
    _a("resina_cuarzo", resina_cuarzo, "Resina con árido de cuarzo", (10.0, 10.0), 0.05, "#6a8a7a",
       ["antideslizante", "resina", "rampa"], rug=0.6),
    _a("pintura_vial", pintura_vial, "Pintura vial", (30.0, 30.0), 0.2, "#d8d8d4", ["paso de cebra",
       "marca vial", "carretera"], rug=0.6),
    _a("podotactil_botones", podotactil_botones, "Podotáctil de botones", (40.0, 40.0), 0.5, "#c8b04a",
       ["podotactil", "botones", "andén", "accesibilidad"]),
    _a("podotactil_barras", podotactil_barras, "Podotáctil de barras", (40.0, 30.0), 0.5, "#c8b04a",
       ["podotactil", "barras", "accesibilidad"]),
    _a("fibrocemento", fibrocemento, "Placa de fibrocemento", (60.0, 60.0), 0.01, "#a8a8a2", ["fibrocemento",
       "placa", "uralita"], rug=0.8),
    _a("pladur", pladur, "Placa de yeso laminado (juntas)", (240.0, 240.0), 0.02, "#e8e6e0", ["pladur", "obra",
       "tabique"], rug=0.8),
    _a("lana_roca", lana_roca, "Lana de roca", (15.0, 15.0), 1.0, "#b8a870", ["lana de roca", "aislante"],
       rug=0.95),
    _a("poliestireno_extruido", poliestireno_extruido, "Poliestireno extruido (XPS)", (30.0, 30.0), 0.05,
       "#d8a8b8", ["xps", "aislante", "poliestireno"], rug=0.7),
    _a("tablero_fenolico", tablero_fenolico, "Tablero fenólico", (60.0, 60.0), 0.01, "#7a4a30", ["fenolico",
       "encofrado", "obra"], rug=0.45),
    _a("cemento_cola", cemento_cola, "Cemento cola peinado", (40.0, 40.0), 0.6, "#b0aca4", ["cemento cola",
       "llana dentada", "obra"], rug=0.9),
    _a("encalado", encalado, "Encalado", (80.0, 80.0), 0.5, "#eeece6", ["cal", "encalado", "cortijo"], rug=0.9),
    _a("tapial", tapial, "Tapial", (120.0, 120.0), 0.5, "#a8845e", ["tapial", "tierra", "rammed earth"], rug=0.9),
    _a("adobe_paja", adobe_paja, "Barro con paja", (40.0, 40.0), 0.4, "#9a7652", ["adobe", "barro", "paja"],
       rug=0.9),
    _a("terrazo_grueso", terrazo_grueso, "Terrazo de grano grueso", (40.0, 40.0), 0.0, "#c8c0b4", ["terrazo",
       "veneciano", "suelo"], rug=0.3),
]
