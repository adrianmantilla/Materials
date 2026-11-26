"""Acabados de terreno: tierras, barro, arenas, gravas, rocas, musgo, hojarasca, nieve, hielo, lava, ceniza."""

import math

import numpy as np

from superficie import (celdas, gris, grietas, hoyuelos, manchas_fractales, mezclar, rejilla,
                        ruido_cm, salpicado, suave)


def esparcir(forma, cx, cy, n, largo_cm, ancho_cm, semilla, perfil, angulo=None, variar=0.4):
    """Deja caer ``n`` objetos (hojas, piedras, agujas) uno encima de otro, sin costuras.

    ``perfil(u, v)`` recibe coordenadas locales (−1..1 a lo largo y a lo ancho) y devuelve la altura
    del objeto (0 = fuera). Devuelve (altura arriba, índice del objeto 0..n-1 o −1, u, v).
    """
    alto, ancho = forma
    tw, th = ancho * cx, alto * cy
    rng = np.random.default_rng(semilla)
    cima = np.full(forma, -1.0)
    quien = np.full(forma, -1, dtype=np.int64)
    uu = np.zeros(forma)
    vv = np.zeros(forma)
    for k in range(int(n)):
        x0, y0 = rng.uniform(0, tw), rng.uniform(0, th)
        a = rng.uniform(0, 2 * math.pi) if angulo is None else angulo + rng.normal(0, 0.15)
        esc = rng.uniform(1 - variar, 1 + variar * 0.5)
        L, W = largo_cm * esc, ancho_cm * esc
        r = max(L, W)
        i0, i1 = int(math.floor((x0 - r) / cx)), int(math.ceil((x0 + r) / cx))
        j0, j1 = int(math.floor((y0 - r) / cy)), int(math.ceil((y0 + r) / cy))
        ii = np.arange(i0, i1 + 1)
        jj = np.arange(j0, j1 + 1)
        px = (ii[None, :] + 0.5) * cx - x0
        py = (jj[:, None] + 0.5) * cy - y0
        u = (px * math.cos(a) + py * math.sin(a)) / L
        v = (-px * math.sin(a) + py * math.cos(a)) / W
        h = perfil(u, v)
        dentro = h > 0
        if not dentro.any():
            continue
        sub = np.ix_(jj % alto, ii % ancho)
        # Cada objeto queda encima del anterior (se apilan): basta con que exista en el píxel.
        h_total = k * 1e-6 + h
        c = cima[sub]
        poner = dentro
        c = np.where(poner, h_total, c)
        cima[sub] = c
        q = quien[sub]
        quien[sub] = np.where(poner, k, q)
        uu[sub] = np.where(poner, u, uu[sub])
        vv[sub] = np.where(poner, v, vv[sub])
    return np.clip(cima, 0, None), quien, uu, vv


def _elipse(u, v):
    d = u * u + v * v
    return np.where(d < 1, np.sqrt(np.clip(1 - d, 0, 1)), 0.0)


def _hoja(u, v):
    """Hoja lanceolada: ancha en el centro, punta en los dos extremos, nervio central."""
    borde = (1 - u * u) * (0.9 + 0.1 * u)
    dentro = (np.abs(u) < 1) & (np.abs(v) < borde)
    return np.where(dentro, 0.4 + 0.6 * (1 - np.abs(v) / np.maximum(borde, 1e-3)), 0.0)


def tierra(forma, cx, cy, humeda=0.0, piedras=0.04):
    """Tierra: grumos, piedrecitas y huellas suaves; ``humeda`` oscurece y abrillanta."""
    grumo = ruido_cm(forma, cx, cy, 0.3, 18001, octavas=3) - 0.5
    fino = ruido_cm(forma, cx, cy, 0.04, 18002, octavas=2) - 0.5
    piedra = salpicado(forma, cx, cy, 0.15, 18003, piedras, borde=0.06)
    mancha = ruido_cm(forma, cx, cy, 20.0, 18004, octavas=4) - 0.5
    lum = 0.5 + 0.08 * grumo + 0.05 * fino + 0.1 * mancha + 0.08 * piedra
    color = gris(lum * (1 - 0.3 * humeda), (1.02, 1.0, 0.96))
    rug = 0.5 + 0.05 * fino - 0.25 * humeda
    return color, rug, 0.5 + 0.3 * grumo + 0.1 * fino + 0.2 * piedra


def barro(forma, cx, cy):
    """Barro: charcos brillantes en las partes bajas, huellas y surcos."""
    relieve = ruido_cm(forma, cx, cy, 6.0, 18101, octavas=5)
    fino = ruido_cm(forma, cx, cy, 0.1, 18102, octavas=2) - 0.5
    charco = 1 - suave(relieve, np.quantile(relieve, 0.15), np.quantile(relieve, 0.25))
    color = gris(0.5 + 0.04 * fino - 0.12 * charco + 0.05 * (relieve - 0.5))
    return color, 0.5 + 0.05 * fino - 0.45 * charco, np.maximum(relieve, np.quantile(relieve, 0.2)) + 0.05 * fino


def barro_agrietado(forma, cx, cy):
    """Barro seco agrietado: placas que se curvan hacia arriba en los bordes y grietas hondas."""
    _, dist, valor = celdas(forma, cx, cy, 8.0, 18201, temblor=0.9)
    grieta = 1 - suave(dist, 0.0, 0.25)
    labio = np.exp(-((dist - 0.6) / 0.5) ** 2)
    menor = grietas(forma, cx, cy, 2.5, 18202, 0.05) * suave(dist, 0.3, 1.0)
    fino = ruido_cm(forma, cx, cy, 0.05, 18203, octavas=2) - 0.5
    color = gris(0.5 + 0.06 * (valor - 0.5) + 0.04 * fino - 0.25 * grieta - 0.1 * menor, (1.03, 1.0, 0.94))
    altura = 0.6 + 0.15 * labio + 0.05 * fino - 0.6 * grieta - 0.15 * menor
    return color, 0.5 + 0.05 * fino, altura


def arena(forma, cx, cy, ondas=0.0, conchas=0.0):
    """Arena: granos finos de varios tonos; ``ondas`` añade rizaduras del viento o del agua."""
    grano = ruido_cm(forma, cx, cy, 0.02, 18301, octavas=1) - 0.5
    oscuro = salpicado(forma, cx, cy, 0.02, 18302, 0.06, borde=0.01)
    mancha = ruido_cm(forma, cx, cy, 15.0, 18303, octavas=4) - 0.5
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    paso = tw / max(1, round(tw / 6.0))
    torcer = (ruido_cm(forma, cx, cy, 10.0, 18304, octavas=3) - 0.5) * 8.0
    fase = 2 * np.pi * (x + torcer) / paso
    riza = (np.sin(fase) + 0.3 * np.sin(2 * fase)) * ondas
    concha = salpicado(forma, cx, cy, 0.3, 18305, conchas, borde=0.05) if conchas else np.zeros(forma)
    color = gris(0.5 + 0.06 * grano - 0.15 * oscuro + 0.06 * mancha + 0.02 * riza + 0.1 * concha,
                 (1.02, 1.0, 0.95))
    return color, 0.5 + 0.05 * grano, 0.5 + 0.25 * grano + 0.25 * riza + 0.2 * concha


def piedras(forma, cx, cy, tam=1.5, n_por_m2=None, semilla=18401, angulosa=0.6, fondo=0.35):
    """Grava / guijarros: piedras apiladas de tonos distintos; ``angulosa`` (0 canto rodado, 1 grava)."""
    alto, ancho = forma
    area = ancho * cx * alto * cy
    n = n_por_m2 or int(area / (tam * tam * 0.18))
    deforma = ruido_cm(forma, cx, cy, tam * 0.5, semilla + 1, octavas=2) - 0.5

    def perfil(u, v):
        d = u * u + v * v
        return np.where(d < 1, np.sqrt(np.clip(1 - d, 0, 1)) ** (0.5 + 0.5 * angulosa), 0.0)

    cima, quien, u, v = esparcir(forma, cx, cy, n, tam * 0.5, tam * 0.38, semilla, perfil)
    rng = np.random.default_rng(semilla + 2)
    tono = rng.uniform(0.35, 0.65, n + 1)[quien]
    tinte_p = rng.uniform(0.95, 1.05, (n + 1, 3))[quien]
    hay = quien >= 0
    faceta = angulosa * 0.15 * np.sign(np.sin(3 * u + 2 * v + quien))
    lum = np.where(hay, tono + 0.06 * deforma + faceta * 0.3, fondo)
    color = gris(lum) * np.where(hay[..., None], tinte_p, 1.0)
    altura = np.where(hay, 0.15 + 0.7 * cima + 0.08 * deforma, 0.05)
    return color, 0.5 + 0.1 * (~hay) - 0.05 * hay, altura


def roca(forma, cx, cy, estratos=0.0):
    """Roca: bloques fracturados de cara rugosa, grietas sueltas y líquenes; ``estratos`` añade capas."""
    detalle = ruido_cm(forma, cx, cy, 1.0, 18502, octavas=5) - 0.5
    grande = ruido_cm(forma, cx, cy, 20.0, 18504, octavas=3) - 0.5
    cresta = 1 - np.abs(2 * ruido_cm(forma, cx, cy, 8.0, 18505, octavas=3) - 1)
    _, dist, valor = celdas(forma, cx, cy, 25.0, 18501, temblor=1.0)
    suelta = suave(ruido_cm(forma, cx, cy, 15.0, 18506), 0.45, 0.6)
    grieta = (1 - suave(dist + 0.6 * detalle, 0.0, 0.25)) * suelta
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    paso = th / max(1, round(th / 5.0))
    capa = np.sin(2 * np.pi * (y + 3.0 * detalle + 6.0 * grande) / paso)
    liquen = manchas_fractales(forma, cx, cy, 3.0, 18503, 0.06)
    lum = 0.5 + 0.05 * (valor - 0.5) + 0.1 * detalle + 0.08 * grande + 0.06 * cresta - 0.2 * grieta
    color = gris(lum + 0.06 * estratos * capa)
    color = mezclar(color, (0.62, 0.62, 0.50), 0.5 * liquen)
    altura = (0.45 + 0.1 * (valor - 0.5) + 0.25 * detalle + 0.2 * grande + 0.12 * cresta - 0.35 * grieta
              + 0.12 * estratos * np.abs(capa))
    return color, 0.5 + 0.05 * detalle + 0.1 * grieta, altura


def musgo(forma, cx, cy):
    """Musgo: cojines mullidos con puntas claras y huecos oscuros."""
    cojin = ruido_cm(forma, cx, cy, 0.6, 18601, octavas=3)
    pelo = ruido_cm(forma, cx, cy, 0.03, 18602, octavas=1) - 0.5
    hueco = 1 - suave(cojin, 0.25, 0.4)
    lum = 0.5 + 0.12 * pelo + 0.1 * (cojin - 0.5) - 0.25 * hueco
    color = gris(lum, (0.95, 1.05, 0.85))
    return color, 0.5 + 0.1 * hueco, 0.2 + 0.6 * cojin + 0.25 * pelo


def liquen(forma, cx, cy):
    """Roca con líquenes: rosetas amarillas, grises y verdosas sobre piedra."""
    color, rug, altura = roca(forma, cx, cy)
    for k, c in enumerate(((0.70, 0.62, 0.30), (0.62, 0.64, 0.58), (0.50, 0.58, 0.40))):
        m = manchas_fractales(forma, cx, cy, 5.0 + 3 * k, 18701 + k, 0.15, detalle=0.8)
        color = mezclar(color, c, 0.85 * m)
        altura = altura + 0.05 * m
    return color, rug + 0.05, altura


def hierba_seca(forma, cx, cy):
    """Hierba seca aplastada: briznas alargadas en una dirección dominante, pajizas y verdosas."""
    def perfil(u, v):
        return np.where((np.abs(u) < 1) & (np.abs(v) < 1), (1 - np.abs(v)) * np.clip(1 - u * u, 0, 1) ** 0.2, 0.0)

    alto, ancho = forma
    n = int(ancho * cx * alto * cy * 1.6)
    cima, quien, u, v = esparcir(forma, cx, cy, n, 3.0, 0.08, 18801, perfil, angulo=0.4)
    rng = np.random.default_rng(18802)
    tono = rng.uniform(0.38, 0.62, n + 1)[quien]
    verde = (rng.uniform(0, 1, n + 1) > 0.8)[quien]
    hay = quien >= 0
    color = gris(np.where(hay, tono, 0.25), (1.05, 1.0, 0.8))
    color = np.where((verde & hay)[..., None], color * np.array([0.85, 1.05, 0.7]), color)
    return color, 0.5 + 0.1 * (~hay), np.where(hay, 0.3 + 0.7 * cima, 0.0)


def hojarasca(forma, cx, cy):
    """Hojarasca: hojas caídas apiladas, cada una con su color de otoño y su nervio."""
    alto, ancho = forma
    n = int(ancho * cx * alto * cy / 9.0)
    cima, quien, u, v = esparcir(forma, cx, cy, n, 3.5, 1.6, 18901, _hoja)
    rng = np.random.default_rng(18902)
    pal = np.array([[0.62, 0.40, 0.20], [0.55, 0.30, 0.15], [0.66, 0.52, 0.25], [0.45, 0.32, 0.22],
                    [0.50, 0.45, 0.25]])
    elec = rng.integers(0, len(pal), n + 1)
    tono = rng.uniform(0.85, 1.1, n + 1)
    hay = quien >= 0
    base = pal[elec[quien]] * tono[quien][..., None]
    nervio = np.exp(-(v / 0.06) ** 2) * (np.abs(u) < 0.95)
    lateral = np.exp(-(np.sin(8 * (u - 0.7 * np.abs(v))) / 0.15) ** 2) * 0.4
    mancha = ruido_cm(forma, cx, cy, 0.4, 18903, octavas=2) - 0.5
    color = base * (1 + 0.2 * mancha[..., None] - 0.12 * nervio[..., None] - 0.06 * lateral[..., None])
    color = np.where(hay[..., None], color, np.array([0.18, 0.14, 0.10]))
    return color * 0.9, 0.5 + 0.1 * (~hay), np.where(hay, 0.3 + 0.5 * cima + 0.05 * nervio, 0.0)


def pinocha(forma, cx, cy):
    """Pinocha: agujas de pino secas cruzadas sobre tierra."""
    def perfil(u, v):
        return np.where((np.abs(u) < 1) & (np.abs(v) < 1), 1 - v * v, 0.0)

    alto, ancho = forma
    n = int(ancho * cx * alto * cy * 1.2)
    cima, quien, u, v = esparcir(forma, cx, cy, n, 4.0, 0.06, 19001, perfil)
    rng = np.random.default_rng(19002)
    tono = rng.uniform(0.4, 0.62, n + 1)[quien]
    hay = quien >= 0
    color = gris(np.where(hay, tono, 0.25), (1.08, 0.95, 0.75))
    return color, 0.5 + 0.1 * (~hay), np.where(hay, 0.4 + 0.6 * cima, 0.0)


def nieve(forma, cx, cy, pisada=0.0):
    """Nieve: blanca con brillos de cristal, ondulación del viento; ``pisada`` añade huellas y compacta."""
    ondula = ruido_cm(forma, cx, cy, 15.0, 19101, octavas=4) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.03, 19102) - 0.5
    _, _, valor = celdas(forma, cx, cy, 0.05, 19103, temblor=1.0)
    brillo = (valor > 0.97).astype(float)
    huella = hoyuelos(forma, cx, cy, 6.0, 19104, 0.2 * pisada) if pisada else np.zeros(forma)
    color = gris(0.55 + 0.02 * grano - 0.06 * huella, (0.98, 0.99, 1.02))
    rug = 0.5 + 0.05 * grano - 0.2 * brillo - 0.1 * huella
    return color, rug, 0.5 + 0.4 * ondula + 0.08 * grano - 0.4 * huella


def hielo(forma, cx, cy):
    """Hielo: liso con burbujas atrapadas, grietas blancas y escarcha en manchas."""
    burbuja = salpicado(forma, cx, cy, 0.08, 19201, 0.03, borde=0.03)
    grieta = grietas(forma, cx, cy, 15.0, 19202, 0.05) * suave(ruido_cm(forma, cx, cy, 10.0, 19203), 0.45, 0.6)
    escarcha = manchas_fractales(forma, cx, cy, 6.0, 19204, 0.25, detalle=0.6)
    fino = ruido_cm(forma, cx, cy, 0.02, 19205) - 0.5
    color = gris(0.45 + 0.1 * burbuja + 0.2 * grieta + 0.12 * escarcha * (0.6 + fino), (0.95, 1.0, 1.05))
    return color, 0.5 - 0.1 + 0.5 * escarcha, 0.5 + 0.05 * escarcha + 0.05 * fino * escarcha - 0.05 * grieta


def lava(forma, cx, cy):
    """Lava enfriada (cordada): pliegues como cuerdas, costra negra brillante y grietas."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    paso = tw / max(1, round(tw / 3.0))
    torcer = (ruido_cm(forma, cx, cy, 25.0, 19301, octavas=3) - 0.5) * 30.0
    cuerda = 0.5 + 0.5 * np.sin(2 * np.pi * (x + torcer) / paso)
    grieta = grietas(forma, cx, cy, 8.0, 19302, 0.12)
    fino = ruido_cm(forma, cx, cy, 0.1, 19303, octavas=3) - 0.5
    color = gris(0.5 + 0.06 * cuerda + 0.05 * fino - 0.2 * grieta)
    rug = 0.5 - 0.12 * cuerda + 0.1 * grieta
    return color, rug, 0.3 + 0.45 * cuerda + 0.15 * fino - 0.4 * grieta


def ceniza(forma, cx, cy):
    """Ceniza: polvo gris muy fino con trocitos de carbón y huellas de soplo."""
    polvo = ruido_cm(forma, cx, cy, 0.02, 19401) - 0.5
    carbon = salpicado(forma, cx, cy, 0.3, 19402, 0.05, borde=0.05)
    soplo = ruido_cm(forma, cx, cy, 8.0, 19403, octavas=4) - 0.5
    color = gris(0.5 + 0.03 * polvo + 0.12 * soplo - 0.35 * carbon)
    return color, 0.5 + 0.03 * polvo, 0.5 + 0.2 * soplo + 0.1 * polvo + 0.2 * carbon


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.85, familia="Terreno", **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


ACABADOS = [
    _a("tierra_seca", tierra, "Tierra seca", (60.0, 60.0), 0.6, "#8a6e50", ["tierra", "suelo", "camino"]),
    _a("tierra_humeda", tierra, "Tierra húmeda", (60.0, 60.0), 0.6, "#6a5038", ["tierra humeda", "huerto"],
       rug=0.7, humeda=1.0),
    _a("barro", barro, "Barro con charcos", (120.0, 120.0), 2.0, "#5e4a38", ["barro", "lodo", "charco"], rug=0.6),
    _a("barro_agrietado", barro_agrietado, "Barro seco agrietado", (80.0, 80.0), 1.5, "#9a8064",
       ["agrietad", "seco", "desierto"]),
    _a("arena_playa", arena, "Arena de playa", (40.0, 40.0), 0.2, "#d8c49a", ["arena", "playa"], conchas=0.01),
    _a("arena_ondulada", arena, "Arena con rizaduras", (60.0, 60.0), 1.0, "#d4b888", ["duna", "rizadura"],
       ondas=1.0),
    _a("grava", piedras, "Grava", (30.0, 30.0), 1.5, "#8a8680", ["grava", "zahorra", "balasto"], tam=1.5),
    _a("gravilla", piedras, "Gravilla", (15.0, 15.0), 0.6, "#a09a90", ["gravilla"], tam=0.6, semilla=18411),
    _a("guijarros", piedras, "Guijarros (canto rodado)", (60.0, 60.0), 3.0, "#9a948c", ["guijarro",
       "canto rodado", "rio"], tam=5.0, angulosa=0.0, semilla=18421, fondo=0.25),
    _a("roca", roca, "Roca", (120.0, 120.0), 5.0, "#86827c", ["roca", "peña", "acantilado"]),
    _a("roca_estratificada", roca, "Roca estratificada", (120.0, 120.0), 5.0, "#a08c74", ["estrato", "sedimentaria"],
       estratos=1.0),
    _a("musgo", musgo, "Musgo", (30.0, 30.0), 1.0, "#5a7030", ["musgo"], rug=0.95, familia="Vegetal"),
    _a("roca_liquen", liquen, "Roca con líquenes", (120.0, 120.0), 5.0, "#86827c", ["liquen"], familia="Vegetal"),
    _a("hierba_seca", hierba_seca, "Hierba seca aplastada", (40.0, 40.0), 0.8, "#b8a070", ["hierba seca", "paja",
       "heno"], familia="Vegetal"),
    _a("hojarasca", hojarasca, "Hojarasca", (60.0, 60.0), 1.0, "#8a8a8a", ["hojarasca", "hojas", "otoño"],
       familia="Vegetal"),
    _a("pinocha", pinocha, "Pinocha", (40.0, 40.0), 0.6, "#9a7048", ["pinocha", "pinar"], familia="Vegetal"),
    _a("nieve", nieve, "Nieve", (100.0, 100.0), 2.0, "#f2f4f8", ["nieve"], rug=0.6),
    _a("nieve_pisada", nieve, "Nieve pisada", (100.0, 100.0), 3.0, "#e8ecf2", ["nieve pisada", "huellas"], rug=0.5,
       pisada=1.0),
    _a("hielo", hielo, "Hielo", (80.0, 80.0), 0.1, "#b8d0dc", ["hielo", "lago helado"], rug=0.1),
    _a("lava_enfriada", lava, "Lava enfriada (cordada)", (80.0, 80.0), 3.0, "#3a3634", ["lava", "volcan"], rug=0.5),
    _a("ceniza", ceniza, "Ceniza", (40.0, 40.0), 0.3, "#8a8884", ["ceniza", "hoguera"], rug=0.95),
]
