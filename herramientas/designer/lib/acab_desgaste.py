"""Acabados de desgaste y suciedad: polvo, hollín, moho, salitre, chorretones, grasa, barro, cal, pinturas
cuarteadas y ampolladas, barniz craquelado, chicles, frenadas, quemaduras, salpicaduras, verdín, restos de
espray, gotas de pintura y carteles arrancados.

Casi todos son una base neutra con la marca encima, para poner sobre cualquier material.
"""

import math

import numpy as np

from acab_terreno import esparcir
from superficie import (celdas, estirado, gris, grietas, hoyuelos, manchas_fractales, rejilla, ruido_cm, salpicado,
                        suave)


def _discos(forma, cx, cy, n, tam, semilla, variar=0.6, alto=1.0):
    """Discos sueltos (gotas, chicles, ampollas): devuelve (cúpula 0-1, índice del disco o −1)."""
    def disco(u, v):
        r = u * u + v * v
        return np.where(r < 1, np.sqrt(np.clip(1 - r, 0, 1)) * alto + 1e-3, 0.0)

    cima, quien, _, _ = esparcir(forma, cx, cy, n, tam, tam, semilla, disco, variar=variar)
    return np.clip(cima, 0, 1), quien


def _area(forma, cx, cy):
    return forma[1] * cx * forma[0] * cy


def polvo(forma, cx, cy):
    """Polvo: velo claro, más espeso en nubes, con pelusillas."""
    nube = ruido_cm(forma, cx, cy, 15.0, 32001, octavas=4)
    grano = ruido_cm(forma, cx, cy, 0.03, 32002, octavas=2) - 0.5
    pelusa = salpicado(forma, cx, cy, 0.15, 32003, 0.02, borde=0.05)
    capa = suave(nube, 0.3, 0.75)
    lum = 0.42 + 0.22 * capa + 0.04 * grano + 0.15 * pelusa
    return gris(lum, (1.02, 1.0, 0.96)), 0.5 + 0.25 * capa, 0.5 + 0.03 * grano + 0.03 * capa


def hollin(forma, cx, cy):
    """Hollín: manchas negras difuminadas que suben en lenguas, con grano de carbonilla."""
    lengua = estirado(forma, cx, cy, 12.0, 32101, 4.0, eje="y", octavas=4)
    mancha = suave(lengua + 0.3 * (ruido_cm(forma, cx, cy, 6.0, 32102, octavas=3) - 0.5), 0.45, 0.75)
    grano = ruido_cm(forma, cx, cy, 0.05, 32103, octavas=2) - 0.5
    lum = 0.75 - 0.6 * mancha + 0.05 * grano
    return gris(lum), 0.5 + 0.2 * mancha, 0.5 + 0.02 * grano


def moho(forma, cx, cy):
    """Moho negro: colonias de puntitos oscuros que se aprietan hacia el centro de cada mancha."""
    zona = ruido_cm(forma, cx, cy, 10.0, 32201, octavas=4)
    densidad = suave(zona, 0.45, 0.75)
    puntos = ruido_cm(forma, cx, cy, 0.08, 32202, octavas=2)
    colonia = suave(puntos + 0.5 * densidad, 0.85, 0.95) * (densidad > 0.05)
    velo = suave(zona, 0.55, 0.85)
    lum = 0.72 - 0.55 * colonia - 0.2 * velo
    color = gris(lum) * np.array([1.0, 1.0, 0.96])
    return color, 0.5 + 0.1 * colonia, 0.5 + 0.05 * colonia


def salitre(forma, cx, cy):
    """Salitre (eflorescencia): costras blancas y algodonosas que trepan desde abajo en bandas."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    banda = 0.5 + 0.5 * np.cos(2 * math.pi * y / th)
    costra = manchas_fractales(forma, cx, cy, 6.0, 32301, 0.35, detalle=0.6)
    borde = ruido_cm(forma, cx, cy, 2.0, 32302, octavas=3)
    blanco = np.clip(costra + suave(banda + 0.4 * (borde - 0.5), 0.75, 0.85), 0, 1)
    cristal = ruido_cm(forma, cx, cy, 0.03, 32303, octavas=2) - 0.5
    humedad = suave(banda + 0.3 * (borde - 0.5), 0.45, 0.75) * (1 - blanco)
    lum = 0.42 + 0.45 * blanco - 0.1 * humedad + 0.06 * cristal * blanco
    return gris(lum), 0.5 + 0.2 * blanco - 0.1 * humedad, 0.5 + 0.12 * blanco * (0.5 + cristal)


def oxido_chorreado(forma, cx, cy):
    """Chorretones de óxido: lágrimas naranjas que bajan desde puntos (tornillos, juntas)."""
    chorro = estirado(forma, cx, cy, 1.5, 32401, 14.0, eje="y", octavas=3)
    largo = ruido_cm(forma, cx, cy, 10.0, 32402, octavas=2)
    marca = suave(chorro, 0.55, 0.75) * suave(largo, 0.35, 0.6)
    lum = 0.6 - 0.25 * marca
    color = gris(lum) * (1 + marca[..., None] * np.array([0.5, 0.0, -0.45]))
    return color, 0.5 + 0.15 * marca, 0.5 + 0.02 * marca


def churretes(forma, cx, cy):
    """Churretes de agua sucia en fachada: rayas grises verticales que se desvanecen hacia abajo."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    chorro = estirado(forma, cx, cy, 2.0, 32501, 20.0, eje="y", octavas=4)
    caida = 0.5 + 0.5 * np.cos(2 * math.pi * y / th)
    marca = suave(chorro, 0.5, 0.72) * (0.4 + 0.6 * caida)
    lum = 0.62 - 0.32 * marca
    return gris(lum, (1.0, 1.0, 0.97)), 0.5 + 0.05 * marca, np.full(forma, 0.5)


def grasa(forma, cx, cy):
    """Grasa de taller: manchas oscuras con aureola, brillantes, y pisadas de goteo."""
    mancha = manchas_fractales(forma, cx, cy, 12.0, 32601, 0.3, detalle=0.25)
    halo = manchas_fractales(forma, cx, cy, 12.0, 32601, 0.42, detalle=0.25) * (1 - mancha)
    gota, _ = _discos(forma, cx, cy, _area(forma, cx, cy) / 60.0, 0.6, 32602)
    m = np.clip(mancha + 0.8 * (gota > 0), 0, 1)
    grano = ruido_cm(forma, cx, cy, 0.05, 32603, octavas=2) - 0.5
    lum = 0.64 - 0.38 * m - 0.12 * halo + 0.04 * grano
    return gris(lum, (1.0, 0.98, 0.94)), 0.5 - 0.3 * m - 0.1 * halo, 0.5 + 0.02 * grano


def barro_salpicado(forma, cx, cy):
    """Salpicaduras de barro: gotas marrones con rabillo y polvo de barro seco alrededor."""
    tw, th = forma[1] * cx, forma[0] * cy

    def gota(u, v):
        r = u * u + (v * (1 + 0.8 * np.clip(u, 0, None))) ** 2
        return np.where(r < 1, np.sqrt(np.clip(1 - r, 0, 1)) + 1e-3, 0.0)

    cima, _, _, _ = esparcir(forma, cx, cy, tw * th / 2.5, 0.5, 0.3, 32701, gota, angulo=math.pi / 2,
                             variar=0.7)
    g = np.clip(cima, 0, 1)
    velo = salpicado(forma, cx, cy, 3.0, 32702, 0.35, borde=0.3)
    lum = 0.66 - 0.3 * (g > 0) - 0.1 * velo
    color = gris(lum) * (1 + ((g > 0) + 0.5 * velo)[..., None] * np.array([0.15, 0.0, -0.2]))
    return color, 0.5 + 0.2 * (g > 0), 0.45 + 0.3 * g


def cal(forma, cx, cy):
    """Cal incrustada: anillos blancos de gotas secas y costra rugosa."""
    gota, quien = _discos(forma, cx, cy, _area(forma, cx, cy) / 3.0, 1.0, 32801, variar=0.7)
    anillo = suave(gota, 0.0, 0.05) * (1 - suave(gota, 0.25, 0.45))
    costra = manchas_fractales(forma, cx, cy, 5.0, 32802, 0.2, detalle=0.5)
    grano = ruido_cm(forma, cx, cy, 0.02, 32803) - 0.5
    blanco = np.clip(anillo + 0.25 * (gota > 0) + costra, 0, 1)
    lum = 0.42 + 0.4 * blanco + 0.05 * grano * blanco
    return gris(lum), 0.5 + 0.25 * blanco, 0.5 + 0.06 * blanco * (0.5 + grano)


def pintura_craquelada(forma, cx, cy):
    """Pintura cuarteada en piel de cocodrilo: placas con bordes levantados y fondo oscuro en las grietas."""
    raja = grietas(forma, cx, cy, 2.0, 32901, 0.1)
    _, dist, valor = celdas(forma, cx, cy, 2.0, 32901)
    labio = 1 - suave(dist, 0.08, 0.3)
    lum = 0.6 + 0.04 * (valor - 0.5) - 0.45 * raja + 0.06 * labio
    return gris(lum), 0.5 + 0.2 * raja, 0.55 - 0.45 * raja + 0.1 * labio


def pintura_ampollada(forma, cx, cy):
    """Pintura ampollada: burbujas abombadas; algunas reventadas dejan ver la capa de abajo."""
    amp, quien = _discos(forma, cx, cy, _area(forma, cx, cy) / 1.2, 0.6, 33001, variar=0.7)
    rota = (np.random.default_rng(33002).uniform(0, 1, int(_area(forma, cx, cy) / 1.2) + 1) < 0.25)[
        np.maximum(quien, 0)] & (quien >= 0)
    hueco = rota & (amp > 0.35)
    lum = 0.6 + 0.04 * amp - 0.3 * hueco
    color = gris(lum) * np.where(hueco[..., None], np.array([1.1, 0.95, 0.8]), 1.0)
    altura = 0.35 + 0.45 * amp * ~hueco + 0.05 * hueco
    return color, 0.5 + 0.15 * hueco, altura


def barniz_cuarteado(forma, cx, cy):
    """Barniz craquelado (cuadro antiguo): red fina de grietas oscuras bajo un barniz amarillento."""
    fina = grietas(forma, cx, cy, 0.6, 33101, 0.025)
    gruesa = grietas(forma, cx, cy, 2.5, 33102, 0.04)
    sucio = ruido_cm(forma, cx, cy, 8.0, 33103, octavas=3) - 0.5
    raja = np.maximum(0.6 * fina, gruesa)
    lum = 0.55 - 0.35 * raja + 0.15 * sucio
    color = gris(lum) * np.array([1.1, 1.0, 0.78])
    return color, 0.45 + 0.15 * raja, 0.5 - 0.3 * raja


def chicles(forma, cx, cy):
    """Chicles aplastados en la acera: manchas grises y negras redondas, algo brillantes."""
    gom, quien = _discos(forma, cx, cy, _area(forma, cx, cy) / 50.0, 1.6, 33201, variar=0.5, alto=0.3)
    tono = np.random.default_rng(33202).uniform(0.15, 0.85, int(_area(forma, cx, cy) / 50.0) + 1)
    t = tono[np.maximum(quien, 0)]
    en = gom > 0
    sucio = ruido_cm(forma, cx, cy, 0.4, 33203, octavas=2) - 0.5
    lum = np.where(en, 0.15 + 0.55 * t + 0.15 * sucio, 0.6)
    return gris(lum), np.where(en, 0.35, 0.5), 0.5 + 0.15 * gom


def frenadas(forma, cx, cy):
    """Marcas de frenada: pares de trazos negros largos (las dos ruedas), con estrías de la banda de rodadura."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    m = np.zeros(forma)
    rng = np.random.default_rng(33301)
    for k in range(3):
        y0 = rng.uniform(0, th)
        deriva = (ruido_cm(forma, cx, cy, 120.0, 33310 + k, octavas=2) - 0.5) * 40
        for via in (0.0, 150.0):
            d = ((y - y0 - via - deriva + th / 2) % th) - th / 2
            rueda = suave(11 - np.abs(d), 0, 3)
            estria = 0.85 + 0.15 * np.sin(2 * math.pi * d / 4.0)
            fuerza = suave(ruido_cm(forma, cx, cy, 60.0, 33320 + k, octavas=2), 0.3, 0.6)
            m = np.maximum(m, rueda * estria * fuerza)
    lum = 0.62 - 0.45 * m
    return gris(lum), 0.5 - 0.1 * m, np.full(forma, 0.5)


def quemadura(forma, cx, cy):
    """Quemadura: centro negro carbonizado, aureola parda y borde chamuscado."""
    q = ruido_cm(forma, cx, cy, 14.0, 33401, octavas=5)
    negro = suave(q, 0.62, 0.68)
    pardo = suave(q, 0.5, 0.62) * (1 - negro)
    ampolla = hoyuelos(forma, cx, cy, 0.3, 33402, 0.3) * negro
    lum = 0.66 - 0.55 * negro - 0.2 * pardo
    color = gris(lum) * (1 + pardo[..., None] * np.array([0.25, 0.0, -0.35]))
    return color, 0.5 + 0.2 * negro, 0.5 - 0.05 * negro + 0.1 * ampolla


def salpicado_cemento(forma, cx, cy):
    """Salpicaduras de cemento o yeso: pegotes grises claros en relieve, con gotitas alrededor."""
    grande, _ = _discos(forma, cx, cy, _area(forma, cx, cy) / 40.0, 1.5, 33501, variar=0.6, alto=0.6)
    chica = salpicado(forma, cx, cy, 0.12, 33502, 0.06, borde=0.02)
    rugo = ruido_cm(forma, cx, cy, 0.1, 33503, octavas=2) - 0.5
    m = np.clip((grande > 0) + chica, 0, 1)
    lum = 0.42 + 0.35 * m + 0.05 * rugo * m
    return gris(lum, (1.0, 1.0, 0.97)), 0.5 + 0.3 * m, 0.45 + 0.35 * grande + 0.1 * chica + 0.04 * rugo * m


def verdin(forma, cx, cy):
    """Verdín: película verde de algas, en manchas y chorretones de zonas húmedas."""
    chorro = estirado(forma, cx, cy, 4.0, 33601, 6.0, eje="y", octavas=4)
    mancha = manchas_fractales(forma, cx, cy, 10.0, 33602, 0.35, detalle=0.5)
    v = np.clip(mancha + suave(chorro, 0.6, 0.8), 0, 1)
    grano = ruido_cm(forma, cx, cy, 0.05, 33603, octavas=2) - 0.5
    lum = 0.62 - 0.22 * v + 0.04 * grano
    color = gris(lum) * (1 + v[..., None] * np.array([-0.25, 0.15, -0.35]))
    return color, 0.5 - 0.12 * v, 0.5 + 0.03 * v


def espray(forma, cx, cy):
    """Restos de espray: niebla de puntitos de pintura de colores, más densa en algunas zonas."""
    pal = np.array([[0.9, 0.25, 0.25], [0.25, 0.45, 0.9], [0.95, 0.8, 0.2], [0.2, 0.2, 0.22]])
    color = gris(np.full(forma, 0.62))
    for k, c in enumerate(pal):
        zona = suave(ruido_cm(forma, cx, cy, 15.0, 33701 + k, octavas=3), 0.55, 0.8)
        punto = ruido_cm(forma, cx, cy, 0.15, 33711 + k) > 0.75 - 0.15 * zona
        peso = np.clip(0.1 * zona + 0.9 * punto * (zona > 0.02), 0, 1)
        color = color * (1 - peso[..., None]) + c * 0.62 * peso[..., None]
    return color, np.full(forma, 0.5), np.full(forma, 0.5)


def gotas_pintura(forma, cx, cy):
    """Gotas de pintura de colores en el suelo de un taller de pintura: gotas en relieve y salpicones."""
    pal = np.array([[0.9, 0.2, 0.2], [0.2, 0.45, 0.9], [0.95, 0.85, 0.2], [0.95, 0.95, 0.95],
                    [0.25, 0.7, 0.35], [0.1, 0.1, 0.12]])
    n = int(_area(forma, cx, cy) / 4.0)
    gota, quien = _discos(forma, cx, cy, n, 0.6, 33801, variar=0.8, alto=0.5)
    c = pal[np.random.default_rng(33802).integers(0, len(pal), n + 1)][np.maximum(quien, 0)]
    en = (gota > 0)[..., None]
    base = gris(np.full(forma, 0.55) + 0.05 * (ruido_cm(forma, cx, cy, 2.0, 33803, octavas=3) - 0.5))
    color = np.where(en, 0.7 * c, base)
    return color, np.where(gota > 0, 0.3, 0.55), 0.45 + 0.3 * gota


def cartel_rasgado(forma, cx, cy):
    """Carteles arrancados: capas de carteles rectangulares pegadas unas sobre otras y rotas a tirones,
    con el borde blanco del papel desgarrado."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    pal = np.array([[0.85, 0.3, 0.25], [0.95, 0.85, 0.35], [0.3, 0.45, 0.75], [0.9, 0.9, 0.86], [0.35, 0.65, 0.5],
                    [0.15, 0.15, 0.18]])
    rng = np.random.default_rng(33900)
    color = gris(np.full(forma, 0.45))
    altura = np.full(forma, 0.4)
    for k in range(len(pal)):
        ancho, alto = tw / rng.integers(1, 3), th / rng.integers(1, 3)
        ox, oy = rng.uniform(0, tw), rng.uniform(0, th)
        u, v = ((x - ox) % ancho) / ancho, ((y - oy) % alto) / alto
        hueco = (u > 0.96) | (v > 0.97)  # separación entre carteles de la misma capa
        r = ruido_cm(forma, cx, cy, 25.0, 33901 + k, octavas=5)
        corte = np.quantile(r, 0.2 + 0.1 * k)
        capa = (r > corte) & ~hueco
        filo = suave(r, corte, corte + 0.015) * (1 - suave(r, corte + 0.015, corte + 0.04)) * ~hueco
        franja = (np.sin(2 * math.pi * v * rng.integers(3, 8)) > 0.6) * (u > 0.1) * (u < 0.9)
        tinta = pal[k] * (1 - 0.25 * franja)[..., None]
        color = np.where(capa[..., None], 0.75 * tinta, color)
        color = np.where((filo > 0.3)[..., None] & ~capa[..., None], 0.85, color)
        altura = np.where(capa, 0.45 + 0.03 * k, altura)
    fibra = estirado(forma, cx, cy, 0.05, 33920, 4.0) - 0.5
    return np.clip(color + 0.03 * fibra[..., None], 0, 1), np.full(forma, 0.55), altura + 0.02 * fibra


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.8, familia="Desgaste", **kw):
    def f(forma, cx, cy):
        r = funcion(forma, cx, cy, **kw)
        color = np.clip(r[0] * (0.5 / max(1e-6, float(r[0].mean()))), 0.0, 1.0)
        rug = np.clip(r[1] + (0.5 - float(r[1].mean())), 0.0, 1.0)
        return (color, rug) + tuple(r[2:])

    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


ACABADOS = [
    _a("polvo", polvo, "Polvo", (60.0, 60.0), 0.01, "#9a9690", ["polvo", "abandonado", "desvan"]),
    _a("hollin", hollin, "Hollín", (60.0, 60.0), 0.01, "#9a9a9a", ["hollin", "chimenea", "incendio"]),
    _a("moho_negro", moho, "Moho negro", (40.0, 40.0), 0.01, "#a8a8a2", ["moho", "humedad", "baño"]),
    _a("salitre", salitre, "Salitre", (60.0, 60.0), 0.1, "#9a948a", ["salitre", "eflorescencia", "sotano"]),
    _a("oxido_chorreado", oxido_chorreado, "Chorretones de óxido", (60.0, 60.0), 0.01, "#9a9a9a",
       ["oxido", "chorreon", "fachada"]),
    _a("churretes", churretes, "Churretes de agua sucia", (100.0, 100.0), 0.0, "#a8a6a0", ["fachada", "churrete",
       "suciedad"]),
    _a("grasa", grasa, "Manchas de grasa", (80.0, 80.0), 0.01, "#8a8884", ["grasa", "taller", "garaje"]),
    _a("barro_salpicado", barro_salpicado, "Salpicaduras de barro", (40.0, 40.0), 0.15, "#9a9690",
       ["barro", "salpicadura", "coche"]),
    _a("cal_incrustada", cal, "Cal incrustada", (30.0, 30.0), 0.05, "#8a8a8a", ["cal", "grifo", "mampara"]),
    _a("pintura_craquelada", pintura_craquelada, "Pintura cuarteada", (20.0, 20.0), 0.08, "#a8a8a4",
       ["pintura vieja", "cuarteado", "puerta vieja"]),
    _a("pintura_ampollada", pintura_ampollada, "Pintura ampollada", (20.0, 20.0), 0.1, "#9aa6b0",
       ["ampolla", "pintura", "humedad"]),
    _a("barniz_cuarteado", barniz_cuarteado, "Barniz craquelado", (20.0, 20.0), 0.01, "#8a7a5a",
       ["craquelado", "cuadro", "antiguo"], rug=0.4),
    _a("chicles", chicles, "Chicles en la acera", (80.0, 80.0), 0.05, "#8a8a88", ["chicle", "acera", "calle"]),
    _a("frenadas", frenadas, "Marcas de frenada", (200.0, 200.0), 0.0, "#8a8a8a", ["frenada", "asfalto",
       "circuito"]),
    _a("quemadura", quemadura, "Quemadura", (60.0, 60.0), 0.05, "#9a9690", ["quemado", "incendio", "chamuscado"]),
    _a("salpicado_cemento", salpicado_cemento, "Salpicaduras de cemento", (40.0, 40.0), 0.2, "#8a8884",
       ["obra", "cemento", "yeso"]),
    _a("verdin", verdin, "Verdín", (60.0, 60.0), 0.02, "#9a9a92", ["verdin", "algas", "humedad"]),
    _a("restos_espray", espray, "Restos de espray", (60.0, 60.0), 0.0, "#9a9a9a", ["espray", "taller",
       "pintura"]),
    _a("gotas_pintura", gotas_pintura, "Gotas de pintura", (40.0, 40.0), 0.05, "#9a9a9a", ["pintura", "taller",
       "suelo de estudio"]),
    _a("cartel_rasgado", cartel_rasgado, "Carteles arrancados", (100.0, 100.0), 0.03, "#a0a0a0",
       ["cartel", "calle", "pared urbana"]),
]
