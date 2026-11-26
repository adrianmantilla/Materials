"""Acabados de comida (segundo lote): masas y quesos por dentro, embutidos, carne veteada, salmón, granos
y semillas a granel (arroz, lentejas, café, maíz, sal, granada, palomitas), fideos de colores, masa de pizza,
piel de pollo asado, galleta, gofre y sandía.
"""

import math

import numpy as np

from acab_terreno import esparcir
from superficie import celdas, estirado, gris, hoyuelos, rejilla, ruido_cm, salpicado, suave


def _area(forma, cx, cy):
    return forma[1] * cx * forma[0] * cy


def _ovalo(u, v):
    r = u * u + v * v
    return np.where(r < 1, np.sqrt(np.clip(1 - r, 0, 1)) + 1e-3, 0.0)


def _granel(forma, cx, cy, densidad, largo, ancho, semilla, perfil=_ovalo, variar=0.25, angulo=None):
    """Granos amontonados que tapan todo el fondo: (cima 0-1, índice, u, v)."""
    n = _area(forma, cx, cy) / (largo * ancho) * densidad
    cima, quien, u, v = esparcir(forma, cx, cy, n, largo, ancho, semilla, perfil, angulo=angulo, variar=variar)
    tono = np.random.default_rng(semilla + 1).uniform(0.8, 1.2, int(n) + 1)[np.maximum(quien, 0)]
    return np.clip(cima, 0, 1), quien, u, v, tono


def galleta(forma, cx, cy):
    """Galleta tostada: agujeritos de pinchar en rejilla, bordes más tostados y azúcar."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = tw / max(1, round(tw / 1.2))
    d = np.hypot(((x % p) - p / 2), ((y % p) - p / 2))
    agujero = suave(0.12 - d, 0, 0.04)
    tostado = ruido_cm(forma, cx, cy, 2.0, 38001, octavas=3) - 0.5
    grano = hoyuelos(forma, cx, cy, 0.05, 38002, 0.4)
    lum = 0.6 + 0.15 * tostado - 0.25 * agujero - 0.05 * grano
    color = gris(lum) * np.array([1.25, 1.0, 0.6])
    return color, 0.6, 0.55 - 0.4 * agujero - 0.05 * grano + 0.05 * tostado


def gofre_dulce(forma, cx, cy):
    """Gofre: cuadrícula de pozos hondos con los nervios dorados y brillo de azúcar."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = tw / max(1, round(tw / 1.6))
    u, v = np.abs((x % p) / p - 0.5), np.abs((y % p) / p - 0.5)
    pozo = 1 - suave(np.maximum(u, v), 0.3, 0.42)
    tostado = ruido_cm(forma, cx, cy, 1.5, 38101, octavas=3) - 0.5
    lum = 0.6 + 0.12 * tostado - 0.2 * pozo + 0.1 * (1 - pozo) * (tostado > 0.1)
    color = gris(lum) * np.array([1.3, 1.0, 0.55])
    return color, 0.55 - 0.05 * pozo, 0.9 - 0.75 * pozo + 0.03 * tostado


def bizcocho(forma, cx, cy):
    """Miga de bizcocho: alvéolos pequeños y regulares, amarilla y esponjosa."""
    alv = hoyuelos(forma, cx, cy, 0.12, 38201, 0.35)
    fino = hoyuelos(forma, cx, cy, 0.04, 38202, 0.3)
    lum = 0.7 - 0.25 * alv - 0.1 * fino
    color = gris(lum) * np.array([1.15, 1.05, 0.65])
    return color, 0.75, 0.6 - 0.4 * alv - 0.1 * fino


def miga_pan(forma, cx, cy):
    """Miga de pan: alvéolos irregulares de tamaños muy distintos, crema."""
    grande = hoyuelos(forma, cx, cy, 0.5, 38301, 0.18)
    medio = hoyuelos(forma, cx, cy, 0.18, 38302, 0.25)
    fino = hoyuelos(forma, cx, cy, 0.05, 38303, 0.3)
    hueco = np.maximum.reduce([grande, 0.8 * medio, 0.5 * fino])
    lum = 0.74 - 0.35 * hueco
    color = gris(lum) * np.array([1.1, 1.03, 0.85])
    return color, 0.75, 0.65 - 0.55 * hueco


def emmental(forma, cx, cy):
    """Queso emmental cortado: ojos redondos brillantes de varios tamaños sobre pasta amarilla."""
    tw, th = forma[1] * cx, forma[0] * cy

    def ojo(u, v):
        r = u * u + v * v
        return np.where(r < 1, 1.0 - r + 1e-3, 0.0)

    cima, quien, _, _ = esparcir(forma, cx, cy, tw * th / 6.0, 1.0, 1.0, 38401, ojo, variar=0.7)
    hondo = np.clip(cima, 0, 1)
    lum = 0.7 - 0.25 * hondo * (quien >= 0)
    color = gris(lum) * np.array([1.15, 1.05, 0.55])
    return color, np.where(quien >= 0, 0.35, 0.55), 0.7 - 0.6 * hondo


def queso_azul(forma, cx, cy):
    """Queso azul: pasta blanca con vetas y bolsas de moho azul verdoso."""
    veta = 1 - np.abs(2 * ruido_cm(forma, cx, cy, 2.5, 38501, octavas=4) - 1)
    moho = suave(veta, 0.85, 0.95)
    bolsa = salpicado(forma, cx, cy, 0.2, 38502, 0.12, borde=0.05)
    m = np.clip(moho + bolsa * suave(veta, 0.6, 0.8), 0, 1)
    lum = 0.78 - 0.45 * m
    color = gris(lum) * (np.array([1.05, 1.03, 0.95]) * (1 - m[..., None]) + np.array([0.7, 0.95, 1.0]) * m[..., None])
    return color, 0.6 - 0.05 * m, 0.55 - 0.3 * bolsa * m


def salami(forma, cx, cy):
    """Salami cortado: carne roja oscura con trocitos blancos de grasa y granos de pimienta."""
    _, dist, valor = celdas(forma, cx, cy, 0.4, 38601, temblor=1.0)
    grasa = (valor > 0.72) & (dist > 0.03)
    pimienta = salpicado(forma, cx, cy, 0.05, 38602, 0.015, borde=0.02)
    lum = np.where(grasa, 0.85, 0.35 + 0.08 * (valor - 0.5)) - 0.25 * pimienta
    color = gris(lum) * np.where(grasa[..., None], np.array([1.05, 0.95, 0.9]), np.array([1.4, 0.65, 0.6]))
    return color, np.where(grasa, 0.45, 0.6), 0.5 + 0.04 * grasa


def carne_veteada(forma, cx, cy):
    """Carne veteada (buey de wagyu): red fina de grasa blanca en carne roja."""
    red = 1 - np.abs(2 * ruido_cm(forma, cx, cy, 1.2, 38701, octavas=5) - 1)
    grasa = suave(red, 0.82, 0.9)
    fibra = estirado(forma, cx, cy, 0.05, 38702, 6.0) - 0.5
    lum = 0.4 + 0.45 * grasa + 0.04 * fibra
    color = gris(lum) * (np.array([1.4, 0.6, 0.6]) * (1 - grasa[..., None]) + np.array([1.05, 0.97, 0.9]) * grasa[
        ..., None])
    return color, 0.45 - 0.05 * grasa, 0.5 + 0.03 * fibra + 0.02 * grasa


def salmon(forma, cx, cy):
    """Lomo de salmón: carne naranja con líneas blancas de grasa curvas y paralelas."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    giro = (ruido_cm(forma, cx, cy, 6.0, 38801, octavas=2) - 0.5) * 4
    fase = 2 * math.pi * 8 * y / th + giro + 1.5 * np.sin(2 * math.pi * x / (forma[1] * cx))
    linea = suave(np.cos(fase), 0.85, 0.95)
    fibra = estirado(forma, cx, cy, 0.08, 38802, 3.0) - 0.5
    lum = 0.55 + 0.3 * linea + 0.05 * fibra
    color = gris(lum) * (np.array([1.45, 0.8, 0.5]) * (1 - linea[..., None]) + np.array([1.1, 1.0, 0.92]) * linea[
        ..., None])
    return color, 0.4, 0.5 + 0.03 * fibra


def arroz(forma, cx, cy):
    """Arroz crudo: granos alargados blancos translúcidos amontonados."""
    cima, quien, u, v, tono = _granel(forma, cx, cy, 2.2, 0.32, 0.12, 38901)
    lum = np.where(quien >= 0, (0.6 + 0.3 * cima) * tono, 0.2)
    return gris(lum, (1.0, 1.0, 0.95)), 0.45, 0.2 + 0.7 * cima


def lentejas(forma, cx, cy):
    """Lentejas pardinas: discos pardos moteados, amontonados."""
    cima, quien, u, v, tono = _granel(forma, cx, cy, 2.0, 0.5, 0.5, 39001)
    mota = salpicado(forma, cx, cy, 0.02, 39002, 0.25, borde=0.02)
    lum = np.where(quien >= 0, (0.45 + 0.2 * cima) * tono - 0.1 * mota, 0.1)
    return gris(lum) * np.array([1.2, 1.0, 0.7]), 0.6, 0.2 + 0.7 * cima


def cafe(forma, cx, cy):
    """Granos de café tostado: óvalos marrones brillantes con la raja central."""
    cima, quien, u, v, tono = _granel(forma, cx, cy, 1.8, 1.0, 0.75, 39101)
    raja = (np.abs(v + 0.15 * np.sin(u * 3)) < 0.08) & (quien >= 0)
    lum = np.where(quien >= 0, (0.3 + 0.2 * cima) * tono - 0.2 * raja, 0.05)
    return gris(lum) * np.array([1.3, 0.95, 0.7]), np.where(quien >= 0, 0.35, 0.8), 0.2 + 0.7 * cima - 0.3 * raja


def sal_gruesa(forma, cx, cy):
    """Sal gruesa: cristales cúbicos blancos con caras planas y aristas."""
    def cristal(u, v):
        m = np.maximum(np.abs(u), np.abs(v))
        return np.where(m < 1, 1.0 - 0.3 * m + 0.3 * (u > v), 0.0)

    cima, quien, u, v, tono = _granel(forma, cx, cy, 2.0, 0.3, 0.3, 39201, perfil=cristal, variar=0.5)
    lum = np.where(quien >= 0, 0.55 + 0.35 * cima * tono, 0.25)
    return gris(lum), 0.35, 0.2 + 0.7 * cima


def fideos_colores(forma, cx, cy):
    """Fideos de colores (virutas de azúcar): bastoncitos de colores vivos apilados."""
    pal = np.array([[0.95, 0.3, 0.35], [0.3, 0.6, 0.95], [0.98, 0.85, 0.25], [0.35, 0.8, 0.45],
                    [0.95, 0.95, 0.92], [0.85, 0.45, 0.85]])

    def baston(u, v):
        return np.where((np.abs(u) < 1) & (np.abs(v) < 1), np.sqrt(np.clip(1 - v * v, 0, 1)) + 1e-3, 0.0)

    cima, quien, u, v, tono = _granel(forma, cx, cy, 2.2, 0.6, 0.12, 39301, perfil=baston)
    n = int(_area(forma, cx, cy) / (0.6 * 0.12) * 2.2) + 1
    c = pal[np.random.default_rng(39302).integers(0, len(pal), n)][np.maximum(quien, 0)]
    color = np.where((quien >= 0)[..., None], c * (0.6 + 0.4 * cima[..., None]), 0.2)
    return color, 0.35, 0.2 + 0.7 * cima


def masa_pizza(forma, cx, cy):
    """Masa de pizza horneada: superficie clara con burbujas tostadas y manchas quemadas."""
    burbuja = hoyuelos(forma, cx, cy, 1.5, 39401, 0.25)
    quemado = suave(burbuja, 0.6, 0.9)
    harina = salpicado(forma, cx, cy, 0.05, 39402, 0.1, borde=0.05)
    tono = ruido_cm(forma, cx, cy, 3.0, 39403, octavas=3) - 0.5
    lum = 0.7 + 0.1 * tono - 0.3 * suave(burbuja, 0.2, 0.6) - 0.35 * quemado + 0.08 * harina
    color = gris(lum) * np.array([1.2, 1.0, 0.7])
    return color, 0.7, 0.4 + 0.4 * burbuja


def piel_pollo(forma, cx, cy):
    """Piel de pollo asado: dorada, con folículos en relieve y zonas más tostadas y brillantes."""
    foliculo = hoyuelos(forma, cx, cy, 0.25, 39501, 0.3)
    tostado = ruido_cm(forma, cx, cy, 3.0, 39502, octavas=4)
    pliegue = 1 - np.abs(2 * ruido_cm(forma, cx, cy, 2.0, 39503, octavas=2) - 1)
    lum = 0.6 - 0.25 * suave(tostado, 0.4, 0.8) + 0.06 * foliculo - 0.1 * suave(pliegue, 0.85, 1.0)
    color = gris(lum) * np.array([1.3, 0.95, 0.5])
    return color, 0.35 - 0.1 * tostado, 0.5 + 0.2 * foliculo - 0.2 * suave(pliegue, 0.85, 1.0)


def maiz(forma, cx, cy):
    """Mazorca de maíz: granos amarillos redondeados en filas apretadas."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = tw / max(1, round(tw / 0.85)), th / max(1, round(th / 0.75))
    col = np.floor(x / px)
    u = (x % px) / px - 0.5
    v = ((y / py + 0.5 * (col % 2)) % 1.0) - 0.5
    d = np.sqrt((u / 0.48) ** 2 + (v / 0.47) ** 4)
    grano = np.sqrt(np.clip(1 - d, 0, 1))
    tono = 0.9 + 0.2 * (ruido_cm(forma, cx, cy, 2.0, 39601) - 0.5)
    lum = (0.25 + 0.6 * grano) * tono
    return gris(lum) * np.array([1.25, 1.05, 0.35]), 0.4 - 0.1 * grano, 0.1 + 0.8 * grano


def sandia(forma, cx, cy):
    """Pulpa de sandía: roja granulosa con pepitas negras en forma de lágrima."""
    granulo = hoyuelos(forma, cx, cy, 0.08, 39701, 0.5)

    def pepita(u, v):
        ancho = 0.35 + 0.65 * np.sqrt(np.clip((1 - u) / 2, 0, 1))  # lágrima: punta en u = 1
        return np.where((np.abs(u) < 1) & (np.abs(v) < ancho * np.sqrt(np.clip(1 - u * u, 0, 1)) * 1.4), 1.0, 0.0)

    tw, th = forma[1] * cx, forma[0] * cy
    cima, quien, _, _ = esparcir(forma, cx, cy, tw * th / 5.0, 0.6, 0.35, 39702, pepita, variar=0.2)
    pep = quien >= 0
    lum = np.where(pep, 0.08, 0.5 + 0.1 * granulo)
    color = gris(lum) * np.where(pep[..., None], 1.0, np.array([1.45, 0.62, 0.62]))
    return color, np.where(pep, 0.3, 0.45), 0.5 + 0.05 * granulo + 0.05 * pep


def granada(forma, cx, cy):
    """Granos de granada: granos rojos translúcidos facetados, muy apretados y brillantes."""
    _, dist, valor = celdas(forma, cx, cy, 0.7, 39801, temblor=0.6)
    cupula = np.sqrt(suave(dist, 0.0, 0.3))
    pepita = suave(dist, 0.22, 0.26) * (valor > 0.4)
    lum = 0.2 + 0.45 * cupula + 0.1 * pepita
    color = gris(lum) * (np.array([1.6, 0.35, 0.45]) * (1 - pepita[..., None]) + np.array([1.1, 0.9, 0.85]) * pepita[
        ..., None])
    return color, 0.25, 0.1 + 0.8 * cupula


def palomitas(forma, cx, cy):
    """Palomitas: copos blancos abombados e irregulares, con restos de cáscara."""
    def copo(u, v):
        r = np.hypot(u, v)
        ang = np.arctan2(v, u)
        borde = 0.75 + 0.25 * np.sin(ang * 5 + u * 3)
        return np.where(r < borde, np.sqrt(np.clip(1 - (r / borde) ** 2, 0, 1)) + 1e-3, 0.0)

    cima, quien, u, v, tono = _granel(forma, cx, cy, 1.6, 2.0, 2.0, 39901, perfil=copo, variar=0.4)
    cascara = (np.hypot(u, v) < 0.2) & (quien >= 0)
    rugo = ruido_cm(forma, cx, cy, 0.2, 39902, octavas=2) - 0.5
    lum = np.where(quien >= 0, 0.6 + 0.3 * cima + 0.08 * rugo, 0.15)
    color = gris(lum) * np.where(cascara[..., None], np.array([1.2, 0.9, 0.5]), np.array([1.05, 1.02, 0.85]))
    return color, 0.65, 0.1 + 0.8 * cima + 0.05 * rugo


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.6, familia="Comida", **kw):
    def f(forma, cx, cy):
        r = funcion(forma, cx, cy, **kw)
        color = np.clip(r[0] * (0.5 / max(1e-6, float(r[0].mean()))), 0.0, 1.0)
        rug_ = np.clip(np.broadcast_to(np.asarray(r[1], dtype=np.float64), forma), 0.0, 1.0)
        rug_ = np.clip(rug_ + (0.5 - float(rug_.mean())), 0.0, 1.0)
        return (color, rug_) + tuple(r[2:])

    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


ACABADOS = [
    _a("galleta", galleta, "Galleta", (12.0, 12.0), 0.1, "#c89a5a", ["galleta", "biscote"], rug=0.75),
    _a("gofre_dulce", gofre_dulce, "Gofre", (12.8, 12.8), 0.6, "#c8904a", ["gofre", "waffle"], rug=0.6),
    _a("bizcocho", bizcocho, "Miga de bizcocho", (8.0, 8.0), 0.2, "#e0c070", ["bizcocho", "tarta", "pastel"],
       rug=0.8),
    _a("miga_pan", miga_pan, "Miga de pan", (10.0, 10.0), 0.4, "#e0d0a8", ["miga", "pan", "rebanada"], rug=0.8),
    _a("queso_emmental", emmental, "Queso emmental", (20.0, 20.0), 0.6, "#e8d070", ["emmental", "queso"],
       rug=0.5),
    _a("queso_azul", queso_azul, "Queso azul", (10.0, 10.0), 0.1, "#d8d6c8", ["queso azul", "roquefort",
       "cabrales"], rug=0.6),
    _a("salami", salami, "Salami", (8.0, 8.0), 0.02, "#9a3a3a", ["salami", "embutido", "chorizo"], rug=0.5),
    _a("carne_veteada", carne_veteada, "Carne veteada", (10.0, 10.0), 0.02, "#a8444a", ["wagyu", "chuleton",
       "carne"], rug=0.45),
    _a("salmon", salmon, "Salmón", (10.0, 10.0), 0.02, "#e08050", ["salmon", "pescado", "sashimi"], rug=0.35),
    _a("arroz", arroz, "Arroz", (6.0, 6.0), 0.15, "#e8e4d8", ["arroz", "grano"], rug=0.5),
    _a("lentejas", lentejas, "Lentejas", (8.0, 8.0), 0.2, "#8a6a48", ["lentejas", "legumbre"], rug=0.6),
    _a("cafe_granos", cafe, "Granos de café", (12.0, 12.0), 0.5, "#4a2e1e", ["cafe", "grano"], rug=0.4),
    _a("sal_gruesa", sal_gruesa, "Sal gruesa", (5.0, 5.0), 0.15, "#e8e8e6", ["sal", "cristales", "azucar"],
       rug=0.35),
    _a("fideos_colores", fideos_colores, "Fideos de colores", (6.0, 6.0), 0.1, "#9a9a9a", ["fideos", "virutas",
       "reposteria"], rug=0.4),
    _a("masa_pizza", masa_pizza, "Masa de pizza", (30.0, 30.0), 0.5, "#d8b080", ["pizza", "masa"], rug=0.75),
    _a("piel_pollo", piel_pollo, "Piel de pollo asado", (15.0, 15.0), 0.15, "#c8884a", ["pollo", "asado"],
       rug=0.4),
    _a("maiz", maiz, "Maíz (mazorca)", (8.5, 7.5), 0.4, "#e8c040", ["maiz", "mazorca"], rug=0.4),
    _a("sandia", sandia, "Pulpa de sandía", (15.0, 15.0), 0.05, "#d04048", ["sandia", "fruta"], rug=0.4),
    _a("granada", granada, "Granos de granada", (8.0, 8.0), 0.3, "#a8202a", ["granada", "fruta"], rug=0.25),
    _a("palomitas", palomitas, "Palomitas", (20.0, 20.0), 1.5, "#e8dcb8", ["palomitas", "cine"], rug=0.7),
]
