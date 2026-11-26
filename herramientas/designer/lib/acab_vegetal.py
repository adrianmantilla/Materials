"""Acabados vegetales: césped natural y artificial, trébol, hiedra, helecho, flores de prado y pétalos,
cortezas (abedul, pino, plátano, alcornoque), testa de tronco, paja, techo de paja, cañizo, esparto,
fibra de coco, astillas y piel de cactus.
"""

import math

import numpy as np

from acab_terreno import esparcir
from superficie import celdas, estirado, gris, rejilla, ruido_cm, salpicado, suave


def _area(forma, cx, cy):
    return forma[1] * cx * forma[0] * cy


def _hoja(u, v, ancho=0.9, nervio=True):
    """Perfil de hoja (u a lo largo −1..1): punta en u=1, nervio central más alto."""
    w = ancho * np.sqrt(np.clip(1 - u * u, 0, 1)) * (1 - 0.25 * u)
    dentro = np.abs(v) < w
    h = 0.6 + 0.4 * (1 - np.abs(v) / np.maximum(w, 1e-6))
    if nervio:
        h = h + 0.2 * (np.abs(v) < 0.06)
    return np.where(dentro, h * (0.8 + 0.2 * (u + 1) / 2), 0.0)


def _hojas(forma, cx, cy, n, largo, ancho, semilla, verde, variar=0.4, angulo=None):
    cima, quien, u, v = esparcir(forma, cx, cy, n, largo, ancho, semilla, _hoja, angulo=angulo, variar=variar)
    tono = np.random.default_rng(semilla + 1).uniform(0.75, 1.2, int(n) + 1)[np.maximum(quien, 0)]
    en = quien >= 0
    nerv = (np.abs(v) < 0.06) & en
    venas = (np.abs(((u * 4 + np.abs(v) * 2.5) % 1.0) - 0.5) < 0.06) & en
    lum = np.where(en, (0.45 + 0.15 * np.clip(cima, 0, 1)) * tono + 0.12 * nerv + 0.05 * venas, 0.12)
    color = gris(lum) * np.asarray(verde)
    return color, cima, en


def cesped(forma, cx, cy, artificial=False):
    """Césped visto desde arriba: briznas finas en todas direcciones, con calvas y tonos."""
    rng_n = _area(forma, cx, cy) * (60 if artificial else 45)
    tw = forma[1] * cx
    del tw
    from superficie import rayas
    brizna = rayas(forma, cx, cy, rng_n, 1.6 if not artificial else 1.2, 0.04, 36001,
                   curva=0.0 if artificial else 0.15)
    fondo = ruido_cm(forma, cx, cy, 6.0, 36002, octavas=3)
    calva = suave(1 - fondo, 0.7, 0.85) * (0 if artificial else 1)
    seco = suave(ruido_cm(forma, cx, cy, 10.0, 36003, octavas=3), 0.6, 0.8) * (0 if artificial else 1)
    lum = 0.25 + 0.5 * brizna + 0.1 * (fondo - 0.5)
    verde = np.array([0.55, 1.25, 0.45]) if not artificial else np.array([0.45, 1.35, 0.4])
    color = gris(lum) * (verde * (1 - seco[..., None]) + np.array([1.2, 1.1, 0.6]) * seco[..., None])
    color = color * (1 - calva[..., None]) + gris(0.4 + 0.05 * fondo) * np.array([1.2, 0.95, 0.7]) * calva[..., None]
    return color, 0.5 - 0.1 * brizna, 0.3 + 0.6 * brizna


def trebol(forma, cx, cy):
    """Trébol: hojitas de tres folíolos redondos con la marca clara en V."""
    n = _area(forma, cx, cy) / 2.2
    cima, quien, u, v = esparcir(forma, cx, cy, n, 1.2, 1.2, 36101, _folios, variar=0.3)
    en = quien >= 0
    marca = (np.abs(cima - 0.55) < 0.05) & en
    tono = np.random.default_rng(36102).uniform(0.8, 1.15, int(n) + 1)[np.maximum(quien, 0)]
    lum = np.where(en, (0.42 + 0.2 * np.clip(cima, 0, 1)) * tono + 0.25 * marca, 0.15)
    return gris(lum) * np.array([0.55, 1.2, 0.5]), 0.5 - 0.05 * en, 0.2 + 0.6 * np.clip(cima, 0, 1)


def _folios(u, v):
    h = np.zeros(np.broadcast(u, v).shape)
    for k in range(3):
        a = 2 * math.pi * k / 3
        cu, cv = 0.45 * math.cos(a), 0.45 * math.sin(a)
        r = np.hypot(u - cu, v - cv) / 0.5
        hk = np.where(r < 1, 0.7 + 0.3 * (1 - r), 0.0)
        hk = np.where((np.abs(r - 0.55) < 0.06) & (r < 1), 0.55, hk)  # marca en V clara
        h = np.maximum(h, hk)
    return h


def hiedra(forma, cx, cy):
    """Hiedra tupida: hojas lobuladas verde oscuro con nervios claros, unas sobre otras."""
    color, cima, en = _hojas(forma, cx, cy, _area(forma, cx, cy) / 9.0, 4.0, 3.0, 36201, (0.5, 1.05, 0.45),
                             variar=0.4)
    return color, 0.45 - 0.1 * en, 0.15 + 0.7 * np.clip(cima, 0, 1)


def helecho(forma, cx, cy):
    """Frondas de helecho: hojas largas y estrechas, recortadas en pinnas, en un sotobosque."""
    color, cima, en = _hojas(forma, cx, cy, _area(forma, cx, cy) / 12.0, 9.0, 2.2, 36301, (0.6, 1.15, 0.4),
                             variar=0.3)
    x, y = rejilla(forma, cx, cy)
    pinna = np.sin((x + y) * 2 * math.pi / 0.6) > -0.2
    return color * (0.75 + 0.25 * pinna[..., None]), 0.5 - 0.05 * en, 0.15 + 0.7 * np.clip(cima, 0, 1)


def flores_prado(forma, cx, cy):
    """Prado con flores: césped corto salpicado de florecillas blancas, amarillas y moradas."""
    color, rug, alt = cesped(forma, cx, cy)
    pal = np.array([[0.95, 0.95, 0.92], [1.0, 0.85, 0.2], [0.65, 0.4, 0.85]])
    n = _area(forma, cx, cy) / 15.0

    def flor(u, v):
        r = np.hypot(u, v)
        ang = np.arctan2(v, u)
        petalo = r < 0.65 + 0.35 * np.abs(np.cos(2.5 * ang))
        return np.where(petalo, np.where(r < 0.3, 1.2, 1.0), 0.0)

    cima, quien, _, _ = esparcir(forma, cx, cy, n, 0.6, 0.6, 36401, flor, variar=0.4)
    en = quien >= 0
    c = pal[np.random.default_rng(36402).integers(0, 3, int(n) + 1)][np.maximum(quien, 0)]
    centro = cima > 1.1
    flor_c = np.where(centro[..., None], np.array([0.95, 0.75, 0.15]), c)
    color = np.where(en[..., None], 0.8 * flor_c, color)
    return color, rug, np.where(en, 0.95, alt)


def petalos(forma, cx, cy):
    """Pétalos de rosa esparcidos: rojos y rosas, curvados, unos sobre otros."""
    n = _area(forma, cx, cy) / 3.0
    cima, quien, u, v = esparcir(forma, cx, cy, n, 1.8, 1.5, 36501, _hoja_ancha, variar=0.4)
    en = quien >= 0
    tono = np.random.default_rng(36502).uniform(0, 1, int(n) + 1)[np.maximum(quien, 0)]
    rojo = np.stack([0.85 + 0.1 * tono, 0.15 + 0.35 * tono, 0.25 + 0.3 * tono], axis=-1)
    lum = 0.6 + 0.4 * np.clip(cima, 0, 1)
    color = np.where(en[..., None], rojo * lum[..., None], 0.12)
    return color, 0.45 - 0.05 * en, 0.2 + 0.6 * np.clip(cima, 0, 1)


def _hoja_ancha(u, v):
    w = np.sqrt(np.clip(1 - u * u, 0, 1))
    return np.where(np.abs(v) < w, 0.6 + 0.4 * (1 - u * u), 0.0)


def corteza_abedul(forma, cx, cy):
    """Corteza de abedul: blanca con lenticelas oscuras horizontales y manchas negras."""
    lent = estirado(forma, cx, cy, 0.4, 36601, 6.0, eje="x", octavas=2)
    lenticela = suave(lent, 0.7, 0.75)
    negro = suave(ruido_cm(forma, cx, cy, 6.0, 36602, octavas=4), 0.66, 0.7)
    pelado = suave(estirado(forma, cx, cy, 3.0, 36603, 4.0, eje="x", octavas=3), 0.65, 0.68)
    fibra = estirado(forma, cx, cy, 0.1, 36604, 10.0, eje="x") - 0.5
    lum = 0.85 + 0.04 * fibra - 0.65 * np.maximum(lenticela, negro) - 0.15 * pelado
    color = gris(lum) * (1 + 0.15 * pelado[..., None] * np.array([1.0, 0.2, -0.6]))
    return color, 0.5 + 0.2 * negro, 0.5 - 0.2 * lenticela + 0.1 * pelado + 0.03 * fibra


def corteza_pino(forma, cx, cy):
    """Corteza de pino: placas grandes rojizas separadas por surcos hondos y oscuros."""
    ids, dist, valor = celdas(forma, cx, cy, 6.0, 36701, temblor=0.8, estirar=0.5)
    placa = suave(dist, 0.1, 1.2)
    escama = estirado(forma, cx, cy, 0.4, 36702, 3.0, eje="y", octavas=3) - 0.5
    lum = 0.15 + 0.45 * placa + 0.1 * (valor - 0.5) + 0.08 * escama
    color = gris(lum) * np.array([1.3, 0.95, 0.7])
    return color, 0.6 - 0.1 * placa, 0.1 + 0.8 * placa + 0.06 * escama


def corteza_platano(forma, cx, cy):
    """Corteza de plátano de sombra: placas finas que se desprenden en manchas crema, verdes y grises."""
    pal = np.array([[0.85, 0.82, 0.65], [0.6, 0.65, 0.45], [0.55, 0.53, 0.5], [0.75, 0.7, 0.55]])
    ids, dist, valor = celdas(forma, cx, cy, 5.0, 36801, temblor=1.0)
    ruido = ruido_cm(forma, cx, cy, 1.5, 36802, octavas=3)
    idx = np.clip((valor * 4 + (ruido - 0.5)).astype(int), 0, 3)
    color = pal[idx]
    borde = 1 - suave(dist + 0.3 * (ruido - 0.5), 0.0, 0.08)
    color = color * (1 - 0.3 * borde[..., None])
    return color, np.full(forma, 0.5), 0.5 - 0.05 * borde + 0.05 * idx / 3


def corteza_alcornoque(forma, cx, cy):
    """Corcho virgen de alcornoque: crestas gruesas verticales y grietas muy hondas, gris pardo."""
    _, dist, valor = celdas(forma, cx, cy, 4.0, 36901, temblor=1.0, estirar=0.3)
    ondula = (ruido_cm(forma, cx, cy, 1.0, 36902, octavas=3) - 0.5) * 0.8
    raja = 1 - suave(dist + ondula, 0.0, 0.7)
    cresta = estirado(forma, cx, cy, 0.6, 36903, 4.0, eje="y", octavas=4)
    poro = salpicado(forma, cx, cy, 0.08, 36904, 0.08, borde=0.04)
    lum = 0.55 - 0.45 * raja + 0.15 * (cresta - 0.5) - 0.1 * poro + 0.06 * (valor - 0.5)
    color = gris(lum) * np.array([1.1, 0.98, 0.85])
    return color, 0.6 + 0.1 * raja, 0.75 - 0.65 * raja + 0.15 * (cresta - 0.5)


def testa(forma, cx, cy):
    """Testa de troncos apilados: rodajas redondas con anillos, corteza y grietas radiales; huecos oscuros."""
    n = _area(forma, cx, cy) / 90.0

    def rodaja(u, v):
        r = np.hypot(u, v)
        return np.where(r < 1, 1.0 + 0.001 * r, 0.0)

    cima, quien, u, v = esparcir(forma, cx, cy, n, 9.0, 9.0, 37001, rodaja, variar=0.45)
    en = quien >= 0
    r = np.hypot(u, v)
    ondula = 0.04 * (ruido_cm(forma, cx, cy, 3.0, 37002, octavas=2) - 0.5)
    anillo = 0.5 + 0.5 * np.sin((r + ondula) * 2 * math.pi * 14)
    corteza = suave(r, 0.88, 0.92)
    ang = np.arctan2(v, u)
    raja = (np.abs(np.sin(ang * 3 + quien)) < 0.03) & (r > 0.3) & (r < 0.85)
    tono = np.random.default_rng(37003).uniform(0.85, 1.15, int(n) + 1)[np.maximum(quien, 0)]
    lum = (0.62 + 0.1 * anillo - 0.12 * r) * tono - 0.4 * corteza - 0.3 * raja
    lum = np.where(en, lum, 0.06)
    color = gris(lum) * np.array([1.15, 1.0, 0.75])
    return color, 0.6 + 0.1 * corteza, np.where(en, 0.6 + 0.02 * anillo - 0.1 * corteza - 0.2 * raja, 0.0)


def paja(forma, cx, cy):
    """Paja suelta: tallos dorados huecos y brillantes, cruzados al azar."""
    from superficie import rayas
    tallo = rayas(forma, cx, cy, _area(forma, cx, cy) * 3, 8.0, 0.18, 37101, curva=0.05)
    fondo = ruido_cm(forma, cx, cy, 2.0, 37102, octavas=2) - 0.5
    lum = 0.2 + 0.65 * tallo + 0.1 * fondo
    color = gris(lum) * np.array([1.25, 1.05, 0.55])
    return color, 0.5 - 0.15 * tallo, 0.2 + 0.7 * tallo


def techo_paja(forma, cx, cy):
    """Techo de paja (bálago): haces de paja inclinados en hiladas, puntas cortadas en fila."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    hilada = th / max(1, round(th / 15.0))
    fila = (y % hilada) / hilada
    haz = estirado(forma, cx, cy, 0.15, 37201, 25.0, eje="y", octavas=3)
    punta = suave(fila, 0.85, 1.0)
    lum = 0.28 + 0.45 * haz - 0.15 * punta + 0.15 * fila
    color = gris(lum) * np.array([1.15, 1.0, 0.65])
    return color, 0.5 + 0.05 * (haz - 0.5), 0.2 + 0.5 * haz + 0.3 * fila


def canizo(forma, cx, cy):
    """Cañizo: cañas finas horizontales atadas con alambre, con los nudos de la caña."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    paso = th / max(1, round(th / 0.9))
    f = (y % paso) / paso
    cana = np.sqrt(np.clip(np.sin(math.pi * f), 0, 1))
    fila = np.floor(y / paso)
    nudo_x = (x + 13.7 * fila) % 25.0
    nudo = suave(0.3 - np.abs(nudo_x - 12.5), 0, 0.2)
    pasoa = tw / max(1, round(tw / 40.0))
    alambre = suave(0.08 - np.abs((x % pasoa) - pasoa / 2), 0, 0.03)
    tono = np.random.default_rng(37301).uniform(0.85, 1.15, int(round(th / paso)) + 1)[fila.astype(int) % int(
        round(th / paso))]
    lum = (0.25 + 0.5 * cana) * tono - 0.15 * nudo
    color = gris(lum) * np.array([1.2, 1.05, 0.65])
    color = color * (1 - alambre[..., None]) + 0.35 * alambre[..., None]
    return color, 0.4 - 0.1 * cana, 0.1 + 0.7 * cana + 0.1 * nudo + 0.2 * alambre


def esparto(forma, cx, cy):
    """Estera de esparto: trenzas de fibra en espiga cosidas una junto a otra."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    ancho = th / max(1, round(th / 2.0))
    fila = np.floor(y / ancho)
    v = (y % ancho) / ancho - 0.5
    lado = np.sign(v)
    fase = (x / 0.5 + lado * v * 2 + 0.5 * fila) % 1.0
    trenza = np.sqrt(np.clip(np.sin(math.pi * fase), 0, 1)) * (1 - (2 * np.abs(v)) ** 4)
    fibra = estirado(forma, cx, cy, 0.03, 37401, 6.0) - 0.5
    lum = 0.25 + 0.5 * trenza + 0.08 * fibra
    color = gris(lum) * np.array([1.15, 1.05, 0.72])
    return color, 0.6, 0.15 + 0.7 * trenza + 0.05 * fibra


def fibra_coco(forma, cx, cy):
    """Fibra de coco (felpudo): fibras gruesas y rizadas, pardas, en todas direcciones."""
    from superficie import rayas
    f1 = rayas(forma, cx, cy, _area(forma, cx, cy) * 25, 1.5, 0.04, 37501, curva=0.4)
    f2 = rayas(forma, cx, cy, _area(forma, cx, cy) * 15, 2.5, 0.05, 37502, curva=0.6)
    f = np.maximum(f1, f2)
    lum = 0.15 + 0.55 * f
    color = gris(lum) * np.array([1.3, 0.95, 0.6])
    return color, 0.7 - 0.05 * f, 0.15 + 0.75 * f


def astillas(forma, cx, cy):
    """Astillas de corteza (acolchado de jardín): trozos alargados pardos rojizos, apilados."""
    n = _area(forma, cx, cy) / 4.0

    def astilla(u, v):
        return np.where((np.abs(u) < 1) & (np.abs(v) < 1 - 0.3 * u * u), 0.7 + 0.3 * (1 - np.abs(v)), 0.0)

    cima, quien, u, v = esparcir(forma, cx, cy, n, 3.0, 1.0, 37601, astilla, variar=0.6)
    en = quien >= 0
    tono = np.random.default_rng(37602).uniform(0.6, 1.3, int(n) + 1)[np.maximum(quien, 0)]
    veta = estirado(forma, cx, cy, 0.1, 37603, 5.0) - 0.5
    lum = np.where(en, (0.35 + 0.2 * np.clip(cima, 0, 1)) * tono + 0.06 * veta, 0.08)
    color = gris(lum) * np.array([1.3, 0.9, 0.62])
    return color, np.full(forma, 0.6), 0.1 + 0.8 * np.clip(cima, 0, 1)


def cactus(forma, cx, cy):
    """Piel de cactus: costillas verticales verdes con areolas blancas y espinas."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    paso = tw / max(1, round(tw / 3.0))
    f = (x % paso) / paso
    costilla = np.sqrt(np.clip(np.sin(math.pi * f), 0, 1))
    pv = th / max(1, round(th / 2.0))
    col = np.floor(x / paso)
    vy = ((y + 0.5 * pv * (col % 2)) % pv) - pv / 2
    d = np.hypot((f - 0.5) * paso, vy)
    areola = d < 0.18
    espina = (np.abs(vy - (f - 0.5) * paso * 0.6) < 0.025) & (d < 0.8) & ~areola
    cera = ruido_cm(forma, cx, cy, 0.5, 37701, octavas=2) - 0.5
    lum = 0.3 + 0.25 * costilla + 0.05 * cera
    color = gris(lum) * np.array([0.6, 1.2, 0.6])
    color = np.where(areola[..., None], 0.85, color)
    color = np.where(espina[..., None], np.array([0.9, 0.85, 0.6]), color)
    return color, 0.45 - 0.05 * costilla, 0.1 + 0.6 * costilla + 0.2 * areola + 0.3 * espina


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.7, familia="Vegetal", **kw):
    def f(forma, cx, cy):
        r = funcion(forma, cx, cy, **kw)
        color = np.clip(r[0] * (0.5 / max(1e-6, float(r[0].mean()))), 0.0, 1.0)
        rug_ = np.clip(np.broadcast_to(r[1], forma) + (0.5 - float(np.mean(r[1]))), 0.0, 1.0)
        return (color, rug_) + tuple(r[2:])

    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


ACABADOS = [
    _a("cesped", cesped, "Césped", (30.0, 30.0), 1.0, "#6a8a48", ["cesped", "hierba", "jardin"]),
    _a("cesped_artificial", cesped, "Césped artificial", (20.0, 20.0), 1.0, "#5a9a48", ["cesped artificial",
       "padel", "terraza"], rug=0.5, artificial=True),
    _a("trebol", trebol, "Trébol", (20.0, 20.0), 0.6, "#5a8a44", ["trebol", "prado"]),
    _a("hiedra_hojas", hiedra, "Hiedra (hojas)", (60.0, 60.0), 3.0, "#3e6a34", ["hiedra", "muro verde",
       "enredadera"], rug=0.5),
    _a("helecho", helecho, "Helecho", (80.0, 80.0), 4.0, "#4e7a3a", ["helecho", "sotobosque", "bosque"]),
    _a("flores_prado", flores_prado, "Prado con flores", (40.0, 40.0), 1.0, "#6a8a48", ["prado", "flores",
       "primavera"]),
    _a("petalos", petalos, "Pétalos de rosa", (30.0, 30.0), 0.2, "#b04a5a", ["petalos", "rosa", "boda"], rug=0.5),
    _a("corteza_abedul", corteza_abedul, "Corteza de abedul", (40.0, 40.0), 0.3, "#d8d6d0", ["abedul",
       "corteza blanca"]),
    _a("corteza_pino", corteza_pino, "Corteza de pino", (60.0, 60.0), 3.0, "#7a5038", ["pino", "corteza",
       "tronco"], rug=0.85),
    _a("corteza_platano", corteza_platano, "Corteza de plátano de sombra", (60.0, 60.0), 0.2, "#9a9478",
       ["platano", "corteza", "camuflaje"]),
    _a("corteza_alcornoque", corteza_alcornoque, "Corteza de alcornoque", (60.0, 60.0), 4.0, "#7a6a58",
       ["alcornoque", "corcho", "dehesa"], rug=0.9),
    _a("testa_troncos", testa, "Testa de troncos (rodajas)", (100.0, 100.0), 1.0, "#a8865a", ["leña", "troncos",
       "rodaja"], rug=0.8),
    _a("paja", paja, "Paja suelta", (40.0, 40.0), 1.0, "#c8a860", ["paja", "establo", "heno"]),
    _a("techo_paja", techo_paja, "Techo de paja", (60.0, 60.0), 5.0, "#a8905a", ["techo de paja", "balago",
       "cabaña"], rug=0.85),
    _a("canizo", canizo, "Cañizo", (80.0, 40.0), 0.6, "#c0a870", ["cañizo", "sombra", "valla"], rug=0.6),
    _a("esparto", esparto, "Estera de esparto", (30.0, 30.0), 0.4, "#b8a070", ["esparto", "estera", "alfombra"],
       rug=0.85),
    _a("fibra_coco", fibra_coco, "Fibra de coco", (20.0, 20.0), 1.0, "#8a6440", ["coco", "felpudo"], rug=0.9),
    _a("astillas", astillas, "Astillas de corteza (acolchado)", (60.0, 60.0), 2.0, "#7a4e34", ["astillas",
       "acolchado", "mulch", "jardin"], rug=0.85),
    _a("piel_cactus", cactus, "Piel de cactus", (24.0, 24.0), 1.5, "#4e7a4a", ["cactus", "desierto"], rug=0.5),
]
