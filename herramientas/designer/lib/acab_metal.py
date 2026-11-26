"""Acabados de metal: pulidos, cepillados, fundición, forja, óxido, pátina, chapas.

Para metales el color de la receta ya es el del metal: aquí el color se mueve poco (salvo óxido
y pátina, que cambian de tono) y lo que manda es la rugosidad (arañazos, cepillado, huellas).
"""

import math

import numpy as np

from superficie import (celdas, estirado, gris, hoyuelos, manchas_fractales, mezclar, rayas, rejilla,
                        ruido_cm, salpicado, suave)

ACERO = (0.55, 0.55, 0.55)  # color lineal típico de la receta base (para calcular tintes)
COBRE = (0.93, 0.62, 0.52)
TITANIO = (0.62, 0.59, 0.55)


def _rel(objetivo, base):
    return np.array([0.5 * o / b for o, b in zip(objetivo, base)])


def pulido_rayado(forma, cx, cy, n=700, largo=4.0, ancho=0.006, fuerza=0.30):
    """Metal pulido con arañazos finos al azar (uso diario)."""
    r = rayas(forma, cx, cy, n, largo, ancho, 1101, curva=0.08)
    velo = ruido_cm(forma, cx, cy, 3.0, 1102, octavas=3) - 0.5
    color = gris(0.5 + 0.02 * velo - 0.03 * r)
    rug = 0.5 + fuerza * r + 0.05 * velo
    altura = 0.5 - 0.25 * r
    return color, rug, altura


def cepillado(forma, cx, cy, tam=0.012, fuerza=0.12, rayas_n=120):
    """Cepillado lineal (a lo largo de X): estrías muy alargadas y algún arañazo cruzado."""
    est = estirado(forma, cx, cy, tam, 1201, 80.0, octavas=2) - 0.5
    larga = estirado(forma, cx, cy, tam * 4, 1202, 40.0) - 0.5
    r = rayas(forma, cx, cy, rayas_n, 3.0, 0.006, 1203)
    color = gris(0.5 + 0.04 * est + 0.02 * larga - 0.02 * r)
    rug = 0.5 + fuerza * est + 0.05 * larga + 0.2 * r
    altura = 0.5 + 0.35 * est - 0.2 * r
    return color, rug, altura


def satinado(forma, cx, cy):
    """Satinado o anodizado: grano isótropo muy fino y velado suave."""
    grano = ruido_cm(forma, cx, cy, 0.01, 1301, octavas=2) - 0.5
    velo = ruido_cm(forma, cx, cy, 4.0, 1302, octavas=3) - 0.5
    color = gris(0.5 + 0.02 * velo + 0.02 * grano)
    rug = 0.5 + 0.06 * grano + 0.05 * velo
    altura = 0.5 + 0.3 * grano
    return color, rug, altura


def fundicion(forma, cx, cy):
    """Hierro fundido en arena: piel granulada, picaduras y manchas de cascarilla."""
    grano = ruido_cm(forma, cx, cy, 0.04, 1401, octavas=2) - 0.5
    bulto = ruido_cm(forma, cx, cy, 0.3, 1402, octavas=2) - 0.5
    pic = hoyuelos(forma, cx, cy, 0.08, 1403, 0.03)
    casc = manchas_fractales(forma, cx, cy, 5.0, 1404, 0.35)
    color = gris(0.5 + 0.08 * grano - 0.10 * casc + 0.05 * bulto - 0.2 * pic)
    rug = 0.5 + 0.15 * casc + 0.08 * grano + 0.1 * pic
    altura = 0.5 + 0.35 * grano + 0.25 * bulto - 0.35 * pic
    return color, rug, altura


def forjado(forma, cx, cy, tam=2.0, oscuro=0.0):
    """Hierro forjado a martillo: golpes planos irregulares, cascarilla oscura y bordes vivos."""
    _, dist, valor = celdas(forma, cx, cy, tam, 1501, temblor=1.0, pesos=0.5)
    golpe = suave(dist, 0.0, tam * 0.35)
    plano = ruido_cm(forma, cx, cy, tam * 0.5, 1502, octavas=2) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.03, 1503) - 0.5
    casc = manchas_fractales(forma, cx, cy, tam * 1.5, 1504, 0.5 + 0.3 * oscuro)
    lum = 0.5 - 0.08 * (1 - golpe) + 0.06 * (valor - 0.5) - (0.12 + 0.2 * oscuro) * casc + 0.04 * grano
    color = gris(lum)
    rug = 0.5 + 0.12 * casc - 0.08 * golpe + 0.05 * grano
    altura = 0.5 + 0.25 * (1 - golpe) + 0.15 * plano + 0.1 * grano
    return color, rug, altura


def martele(forma, cx, cy, tam=0.9):
    """Martelé decorativo: hoyuelos regulares de martillo de bola, pulidos."""
    _, dist, valor = celdas(forma, cx, cy, tam, 1601, temblor=0.7)
    fondo = 1.0 - suave(dist, 0.0, tam * 0.5)
    color = gris(0.5 + 0.03 * (valor - 0.5) - 0.02 * fondo)
    rug = 0.5 + 0.04 * (1 - fondo) + 0.03 * (valor - 0.5)
    altura = 0.5 + 0.4 * suave(dist, 0.0, tam * 0.5) - 0.2
    return color, rug, altura


def galvanizado(forma, cx, cy):
    """Chapa galvanizada: «flor» de zinc (cristales de 1-3 cm) y manchas de óxido blanco."""
    _, dist, valor = celdas(forma, cx, cy, 2.2, 1701, temblor=1.0, pesos=0.6)
    dendrita = estirado(forma, cx, cy, 0.05, 1702, 5.0) - 0.5
    blanco = salpicado(forma, cx, cy, 1.2, 1703, 0.06)
    borde = 1.0 - suave(dist, 0.0, 0.05)
    lum = 0.5 + 0.12 * (valor - 0.5) + 0.03 * dendrita - 0.05 * borde + 0.12 * blanco
    color = gris(lum)
    rug = 0.5 + 0.18 * (valor - 0.5) + 0.25 * blanco + 0.03 * dendrita
    altura = 0.5 + 0.1 * dendrita + 0.15 * blanco - 0.1 * borde
    return color, rug, altura


def oxido(forma, cx, cy, cobertura=0.3, total=False):
    """Óxido: manchas anaranjadas de borde irregular con grano áspero y algún hoyo de corrosión."""
    if total:
        zona = np.clip(0.75 + 0.5 * (ruido_cm(forma, cx, cy, 6.0, 1801, octavas=3) - 0.5), 0, 1)
    else:
        zona = manchas_fractales(forma, cx, cy, 8.0, 1801, cobertura)
    tono = ruido_cm(forma, cx, cy, 2.0, 1802, octavas=3) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.03, 1803, octavas=2) - 0.5
    escama = hoyuelos(forma, cx, cy, 0.4, 1804, 0.12 if total else 0.05) * zona
    claro = _rel((0.42, 0.17, 0.06), ACERO)
    oscuro = _rel((0.14, 0.06, 0.03), ACERO)
    rojo = claro * (1 + 0.6 * tono[..., None]) + oscuro * (0.5 - 0.6 * tono[..., None])
    rojo = rojo * (1 + 0.25 * grano[..., None])
    base = gris(0.5 + 0.03 * grano)
    color = base * (1 - zona[..., None]) + rojo * zona[..., None]
    color = color * (1 - 0.3 * escama[..., None])
    rug = 0.5 + 0.38 * zona + 0.05 * grano
    altura = 0.5 + zona * (0.08 + 0.35 * grano) - 0.3 * escama
    return color, rug, altura


def patina_cobre(forma, cx, cy):
    """Cobre con cardenillo: pátina verde azulada en manchas y chorreones verticales."""
    zona = manchas_fractales(forma, cx, cy, 6.0, 1901, 0.45)
    chorro = estirado(forma, cx, cy, 0.6, 1902, 12.0, eje="y", octavas=2)
    zona = np.clip(zona + suave(chorro, 0.6, 0.75) * 0.8, 0, 1)
    tono = ruido_cm(forma, cx, cy, 1.5, 1903, octavas=3) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.03, 1904) - 0.5
    verde = _rel((0.30, 0.56, 0.46), COBRE) * (1 + 0.3 * tono[..., None])
    oscurecido = gris(0.40 + 0.08 * tono)  # cobre oscurecido donde no hay cardenillo
    color = oscurecido * (1 - zona[..., None]) + verde * zona[..., None]
    rug = 0.5 + 0.25 + 0.15 * zona + 0.04 * grano - 0.2 * (1 - zona)
    altura = 0.5 + 0.15 * zona * (grano + 0.5) + 0.05 * tono
    return color, rug, altura


def envejecido(forma, cx, cy, tinte=(0.9, 0.95, 1.05), fuerza=0.5, verdin=0.0):
    """Plata, latón o bronce envejecidos: oscurecido en manchas suaves, brillo gastado en zonas."""
    zona = np.clip((ruido_cm(forma, cx, cy, 4.0, 2001, octavas=4) - 0.35) * 2.0, 0, 1)
    grano = ruido_cm(forma, cx, cy, 0.02, 2002) - 0.5
    r = rayas(forma, cx, cy, 250, 3.0, 0.006, 2003)
    lum = 0.5 - fuerza * 0.3 * zona + 0.03 * grano - 0.02 * r
    color = gris(lum, (1 + (tinte[0] - 1) * zona, 1 + (tinte[1] - 1) * zona, 1 + (tinte[2] - 1) * zona))
    if verdin:
        v = salpicado(forma, cx, cy, 0.4, 2004, 0.05 * verdin) * zona
        color = mezclar(color, (0.18, 0.32, 0.26), v)
    rug = 0.5 + 0.15 * zona + 0.15 * r + 0.03 * grano
    altura = 0.5 + 0.2 * grano - 0.2 * r
    return color, rug, altura


def cromo_huellas(forma, cx, cy):
    """Cromo o acero espejo con huellas y velos de grasa (solo rugosidad)."""
    x, y = rejilla(forma, cx, cy)
    mancha = salpicado(forma, cx, cy, 1.2, 2101, 0.12, borde=0.08)
    giro = ruido_cm(forma, cx, cy, 0.6, 2102) - 0.5
    crestas = 0.5 + 0.5 * np.sin(2 * np.pi * (np.hypot(x % 7.0 - 3.5, y % 7.0 - 3.5) + 1.5 * giro) / 0.05)
    huella = mancha * (0.6 + 0.4 * crestas)
    velo = ruido_cm(forma, cx, cy, 5.0, 2103, octavas=3) - 0.5
    color = gris(0.5 - 0.02 * huella)
    rug = 0.5 + 0.25 * huella + 0.04 * velo
    altura = 0.5 + 0.02 * huella
    return color, rug, altura


def titanio_quemado(forma, cx, cy):
    """Titanio con colores de calor (dorado, morado, azul) en bandas que ondulan."""
    alto, ancho = forma
    x, _ = rejilla(forma, cx, cy)
    tw = ancho * cx
    onda = ruido_cm(forma, cx, cy, 3.0, 2201, octavas=3) - 0.5
    t = (2 * x / tw + 0.25 * onda) % 1.0
    paleta = [_rel(c, TITANIO) for c in ((0.62, 0.59, 0.55), (0.80, 0.58, 0.22), (0.42, 0.20, 0.48),
                                          (0.18, 0.32, 0.72), (0.40, 0.62, 0.80), (0.62, 0.59, 0.55))]
    pos = t * (len(paleta) - 1)
    k = np.floor(pos).astype(int)
    f = suave(pos - k, 0.0, 1.0)[..., None]
    pal = np.array(paleta)
    color = pal[k] * (1 - f) + pal[np.minimum(k + 1, len(paleta) - 1)] * f
    grano = ruido_cm(forma, cx, cy, 0.01, 2202) - 0.5
    color = color * (1 + 0.04 * grano[..., None])
    rug = 0.5 + 0.04 * grano
    altura = 0.5 + 0.2 * grano
    return color, rug, altura


def plomo(forma, cx, cy):
    """Plomo: blando y abollado, gris mate con óxido blanquecino en manchas."""
    abolla = ruido_cm(forma, cx, cy, 3.0, 2301, octavas=3) - 0.5
    r = rayas(forma, cx, cy, 150, 4.0, 0.02, 2302, curva=0.2)
    blanco = manchas_fractales(forma, cx, cy, 5.0, 2303, 0.25)
    grano = ruido_cm(forma, cx, cy, 0.03, 2304) - 0.5
    color = gris(0.5 + 0.05 * abolla + 0.15 * blanco - 0.03 * r + 0.03 * grano)
    rug = 0.5 + 0.12 * blanco - 0.1 * r + 0.04 * grano
    altura = 0.5 + 0.35 * abolla - 0.25 * r + 0.08 * grano
    return color, rug, altura


def moleteado(forma, cx, cy, paso=0.25):
    """Moleteado en diamante (empuñaduras, mandos)."""
    x, y = rejilla(forma, cx, cy)
    a = np.abs(((x + y) / paso) % 1.0 - 0.5) * 2
    b = np.abs(((x - y) / paso) % 1.0 - 0.5) * 2
    h = np.minimum(a, b)
    color = gris(0.5 - 0.06 * (1 - h))
    rug = 0.5 + 0.08 * (1 - h)
    return color, rug, 0.15 + 0.7 * h


def chapa_lagrimada(forma, cx, cy, paso=2.8):
    """Chapa lagrimada (suelo antideslizante): lágrimas en relieve a ±45° alternas."""
    x, y = rejilla(forma, cx, cy)
    i, j = np.floor(x / paso), np.floor(y / paso)
    u, v = x / paso - i - 0.5, y / paso - j - 0.5
    signo = np.where((i + j) % 2 == 0, 1.0, -1.0)
    s, t = (u + signo * v) / math.sqrt(2), (u - signo * v) / math.sqrt(2)
    r = (s / 0.36) ** 2 + (t / 0.09) ** 2
    lagrima = np.sqrt(np.clip(1 - r, 0, 1))
    r_ = rayas(forma, cx, cy, 200, 6.0, 0.01, 2401)
    color = gris(0.5 + 0.04 * lagrima - 0.03 * r_)
    rug = 0.5 - 0.12 * lagrima + 0.2 * r_
    return color, rug, 0.3 + 0.6 * lagrima - 0.1 * r_


def pintura_rayada(forma, cx, cy, desconchon=0.04):
    """Chapa pintada con arañazos y golpes que dejan ver la imprimación y el metal."""
    r = rayas(forma, cx, cy, 180, 6.0, 0.015, 2501, curva=0.15)
    golpe = manchas_fractales(forma, cx, cy, 1.5, 2502, desconchon)
    piel = ruido_cm(forma, cx, cy, 0.25, 2503, octavas=2) - 0.5
    sucio = ruido_cm(forma, cx, cy, 8.0, 2504, octavas=3) - 0.5
    hueco = np.maximum(suave(r, 0.4, 0.6), golpe)
    color = gris(0.5 + 0.04 * sucio)
    color = mezclar(color, (0.42, 0.40, 0.38), 0.9 * hueco)  # metal o imprimación gris
    rug = 0.5 + 0.06 * sucio + 0.15 * hueco
    altura = 0.5 + 0.06 * piel - 0.25 * hueco
    return color, rug, altura


def pintura_desconchada(forma, cx, cy):
    """Pintura vieja desconchada en placas sobre metal oxidado."""
    placa = manchas_fractales(forma, cx, cy, 4.0, 2601, 0.2, detalle=0.5)
    borde = suave(placa, 0.0, 0.6) * (1 - suave(placa, 0.6, 1.0))
    grano = ruido_cm(forma, cx, cy, 0.03, 2602) - 0.5
    tono = ruido_cm(forma, cx, cy, 2.0, 2603, octavas=2) - 0.5
    pintura = gris(0.5 + 0.05 * tono)
    debajo = np.array([0.24, 0.17, 0.13]) * (1 + 0.5 * tono[..., None]) * (1 + 0.3 * grano[..., None])
    color = pintura * (1 - placa[..., None]) + debajo * placa[..., None]
    rug = 0.5 + 0.35 * placa + 0.04 * grano
    altura = 0.5 + 0.12 * (1 - placa) + 0.15 * borde + 0.1 * placa * grano
    return color, rug, altura


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.35, metal=1.0, **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia="Metal", tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=metal, recomendado_para=para)


ACABADOS = [
    _a("metal_pulido_rayado", pulido_rayado, "Metal pulido con arañazos", (20.0, 20.0), 0.01, "#c8c8c8",
       ["pulid", "espejo", "plata pulida", "oro pulido"], rug=0.1),
    _a("metal_cepillado", cepillado, "Metal cepillado", (20.0, 20.0), 0.01, "#b4b4b4",
       ["cepillad", "acero inoxidable", "inox"], rug=0.3),
    _a("metal_satinado", satinado, "Metal satinado o anodizado", (20.0, 20.0), 0.005, "#a9adb3",
       ["anodizad", "aluminio", "titanio", "niquel", "satinad"], rug=0.35),
    _a("hierro_fundido", fundicion, "Hierro fundido", (30.0, 30.0), 0.12, "#5c5a58",
       ["hierro fundido", "fundicion", "hierro"], rug=0.7),
    _a("hierro_forjado", forjado, "Hierro forjado a martillo", (40.0, 40.0), 0.15, "#4b4a49",
       ["forjad", "hierro"], rug=0.6),
    _a("hierro_forjado_negro", forjado, "Hierro forjado ennegrecido", (40.0, 40.0), 0.15, "#2f2e2d",
       ["forjado oscuro", "hierro forjado oscuro"], rug=0.65, oscuro=1.0),
    _a("metal_martele", martele, "Martelé", (24.0, 24.0), 0.12, "#c38a5f", ["martel", "cobre", "laton"],
       rug=0.25),
    _a("chapa_galvanizada", galvanizado, "Chapa galvanizada", (60.0, 60.0), 0.02, "#9da3a8",
       ["galvaniz", "zinc"], rug=0.4),
    _a("oxido_leve", oxido, "Acero con óxido", (60.0, 60.0), 0.08, "#8a8c8e", ["oxid", "acero", "hierro"],
       rug=0.45, cobertura=0.3),
    _a("oxido_total", oxido, "Óxido", (60.0, 60.0), 0.15, "#8a8c8e", ["oxido", "corroid", "herrumbre"],
       rug=0.6, total=True),
    _a("cobre_cardenillo", patina_cobre, "Cobre con cardenillo", (60.0, 60.0), 0.05, "#c37a5c",
       ["cobre envejecido", "cardenillo", "patina", "bronce"], rug=0.4),
    _a("plata_envejecida", envejecido, "Plata envejecida", (20.0, 20.0), 0.01, "#c9c9cb",
       ["plata envejecida", "plata"], rug=0.25, tinte=(0.95, 0.92, 0.85), fuerza=0.7),
    _a("laton_envejecido", envejecido, "Latón envejecido", (20.0, 20.0), 0.01, "#b5944b",
       ["laton envejecido", "laton", "bronce"], rug=0.3, tinte=(0.9, 0.85, 0.75), fuerza=0.6, verdin=1.0),
    _a("cromo_huellas", cromo_huellas, "Cromo con huellas", (20.0, 20.0), 0.002, "#d8d8d8",
       ["cromo", "espejo", "acero pulido"], rug=0.05),
    _a("titanio_quemado", titanio_quemado, "Titanio quemado", (30.0, 30.0), 0.002, "#9e978c",
       ["titanio quemado", "escape", "tornasol"], rug=0.25),
    _a("plomo", plomo, "Plomo", (40.0, 40.0), 0.08, "#6e7173", ["plomo", "estaño"], rug=0.6),
    _a("metal_moleteado", moleteado, "Moleteado", (5.0, 5.0), 0.05, "#a0a0a0", ["moletead", "empuñadura"],
       rug=0.35),
    _a("chapa_lagrimada", chapa_lagrimada, "Chapa lagrimada", (22.4, 22.4), 0.25, "#9ea2a6",
       ["lagrimad", "antideslizante", "chapa de suelo"], rug=0.35),
    _a("chapa_pintada_rayada", pintura_rayada, "Chapa pintada rayada", (60.0, 60.0), 0.02, "#2f5f8f",
       ["chapa pintada", "pintura de coche"], rug=0.35, metal=0.0),
    _a("pintura_desconchada", pintura_desconchada, "Pintura desconchada sobre óxido", (60.0, 60.0), 0.06,
       "#5d8a6a", ["desconchad", "pintura vieja"], rug=0.5, metal=0.0),
]
