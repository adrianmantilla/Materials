"""Acabados de origen animal: pelajes con dibujo (leopardo, tigre, cebra, vaca, jirafa, dálmata, atigrado),
pieles y cueros exóticos (serpiente, cocodrilo, avestruz, cerdo, tiburón, rana, pergamino), plumas,
escamas de pez, lana, panal, nácar y asta.

Los pelajes se montan sobre el pelo corto de ``acab_tela`` y le pintan encima el dibujo del animal. Los
dibujos son de alto contraste: la muestra es un tono medio y el mapa de color va de ~0,1 a ~1.
"""

import math

import numpy as np

import patrones
from acab_tela import pelo
from acab_terreno import esparcir
from superficie import celdas, estirado, gris, hoyuelos, manchas_fractales, rejilla, ruido_cm, salpicado, suave


def _ondas(forma, cx, cy, n, eje, semilla, torcer, tam_cm):
    """Fase de ``n`` rayas enteras a lo largo de ``eje`` ("x": rayas verticales), torcida con ruido."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    giro = (ruido_cm(forma, cx, cy, tam_cm, semilla, octavas=3) - 0.5) * torcer
    if eje == "x":
        return 2 * math.pi * n * x / tw + giro
    return 2 * math.pi * n * y / th + giro


def _pelaje(forma, cx, cy, mancha, oscuro=0.12, claro=0.62, tinte_oscuro=(1.0, 1.0, 1.0),
            tinte_claro=(1.0, 1.0, 1.0), largo=12.0):
    """Pinta ``mancha`` (0 fondo, 1 dibujo) sobre pelo corto; el dibujo sigue un poco las hebras."""
    color_p, rug, altura = pelo(forma, cx, cy, largo=largo)
    hebra = color_p[..., 0] - 0.5
    m = np.clip(mancha + 0.6 * hebra, 0.0, 1.0)
    base = gris(claro * (1 + 0.8 * hebra), tinte_claro)
    dib = gris(oscuro * (1 + 0.8 * hebra), tinte_oscuro)
    color = base * (1 - m[..., None]) + dib * m[..., None]
    return color, rug, altura


def leopardo(forma, cx, cy):
    """Leopardo: rosetas (anillos rotos oscuros con el centro más tostado) y algunos lunares sueltos."""
    tw, th = forma[1] * cx, forma[0] * cy

    def roseta(u, v):
        r = np.sqrt(u * u + v * v)
        return np.where(r < 1, np.where(r > 0.55, 1.0, 0.5), 0.0)

    n = tw * th / 5.0
    cima, quien, u, v = esparcir(forma, cx, cy, n, 1.4, 1.1, 30001, roseta, variar=0.5)
    roto = suave(ruido_cm(forma, cx, cy, 0.35, 30003, octavas=2), 0.4, 0.48)
    lunar = salpicado(forma, cx, cy, 0.5, 30002, 0.06, borde=0.04)
    anillo = (cima > 0.75) * roto
    centro = (np.abs(cima - 0.5) < 0.1).astype(float)
    color, rug, altura = _pelaje(forma, cx, cy, np.maximum(anillo, lunar * (cima < 0)), oscuro=0.1, claro=0.68,
                                 tinte_claro=(1.08, 0.98, 0.82))
    color = color * (1 - 0.2 * centro[..., None] * np.array([0.5, 1.0, 1.5]))
    return color, rug, altura


def tigre(forma, cx, cy):
    """Tigre: rayas oscuras verticales, estrechas, que se ahorquillan y se cortan."""
    fase = _ondas(forma, cx, cy, 8, "x", 30101, 9.0, 12.0)
    grosor = 0.55 + 0.35 * (ruido_cm(forma, cx, cy, 6.0, 30102) - 0.5)
    raya = suave(np.cos(fase), grosor, grosor + 0.12)
    corte = suave(ruido_cm(forma, cx, cy, 5.0, 30103, octavas=2), 0.28, 0.36)
    return _pelaje(forma, cx, cy, raya * corte, oscuro=0.1, claro=0.66, tinte_claro=(1.18, 0.88, 0.62))


def cebra(forma, cx, cy):
    """Cebra: rayas blancas y negras anchas, onduladas."""
    fase = _ondas(forma, cx, cy, 10, "x", 30201, 7.0, 20.0)
    raya = suave(np.cos(fase), -0.08, 0.08)
    return _pelaje(forma, cx, cy, raya, oscuro=0.08, claro=0.92, largo=6.0)


def vaca(forma, cx, cy):
    """Vaca frisona: grandes manchas negras de borde recortado sobre blanco."""
    m = manchas_fractales(forma, cx, cy, 25.0, 30301, 0.42, detalle=0.5)
    return _pelaje(forma, cx, cy, m, oscuro=0.08, claro=0.82, largo=8.0)


def jirafa(forma, cx, cy):
    """Jirafa: manchas poligonales marrones separadas por líneas claras."""
    _, dist, valor = celdas(forma, cx, cy, 8.0, 30401, temblor=0.7)
    ondula = (ruido_cm(forma, cx, cy, 2.0, 30402, octavas=2) - 0.5) * 0.8
    mancha = suave(dist + ondula, 0.6, 0.8)
    color, rug, altura = _pelaje(forma, cx, cy, mancha, oscuro=0.32, claro=0.85, tinte_oscuro=(1.2, 0.85, 0.6),
                                 tinte_claro=(1.05, 1.0, 0.88), largo=6.0)
    color = color * (1 + 0.12 * (valor[..., None] - 0.5) * mancha[..., None])
    return color, rug, altura


def dalmata(forma, cx, cy):
    """Dálmata: lunares negros redondeados, de tamaños distintos, sobre blanco."""
    tw, th = forma[1] * cx, forma[0] * cy

    def lunar(u, v):
        return np.where(u * u + v * v < 1, 1.0, 0.0)

    cima, _, _, _ = esparcir(forma, cx, cy, tw * th / 9.0, 1.1, 0.9, 30501, lunar, variar=0.6)
    return _pelaje(forma, cx, cy, (cima > 0).astype(float), oscuro=0.06, claro=0.6, largo=6.0)


def atigrado(forma, cx, cy):
    """Gato atigrado: rayas finas pardas que se curvan, con pelo agutí (puntas claras)."""
    fase = _ondas(forma, cx, cy, 12, "x", 30601, 14.0, 8.0)
    raya = suave(np.cos(fase), 0.35, 0.6)
    color, rug, altura = _pelaje(forma, cx, cy, raya, oscuro=0.22, claro=0.62, tinte_oscuro=(1.0, 0.92, 0.8),
                                 tinte_claro=(1.1, 0.98, 0.82), largo=16.0)
    punta = ruido_cm(forma, cx, cy, 0.02, 30602) > 0.6
    return color * (1 + 0.15 * punta[..., None]), rug, altura


def serpiente(forma, cx, cy):
    """Pitón: escamas pequeñas en tresbolillo con manchas en silla de montar de borde oscuro."""
    radio = 0.3
    x, y = rejilla(forma, cx, cy)
    ids = patrones.red_voronoi(x, y, (math.sqrt(3) * radio, 0.0), (math.sqrt(3) * radio / 2, 1.5 * radio))
    borde = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
    from fabricar import distancia_interior
    dist = distancia_interior(~borde, cx, cy, radio)
    cupula = np.sqrt(suave(dist, 0.0, radio * 0.8))
    mancha = ruido_cm(forma, cx, cy, 2.2, 30702, octavas=3)
    mancha = mancha + 0.2 * (ruido_cm(forma, cx, cy, 0.6, 30703) - 0.5)
    q1, q2 = np.quantile(mancha, [0.42, 0.55])
    silla = suave(mancha, q2, q2 + 0.01)
    contorno = suave(mancha, q1, q1 + 0.01) * (1 - silla)
    lum = 0.8 - 0.25 * silla - 0.62 * contorno - 0.15 * (1 - cupula)
    tono = np.where(silla[..., None] > 0.5, np.array([1.15, 0.92, 0.7]), np.array([1.05, 1.0, 0.85]))
    color = gris(lum) * tono
    return color, 0.5 - 0.08 * cupula, 0.25 + 0.65 * cupula


def cocodrilo(forma, cx, cy):
    """Cocodrilo (cuero de vientre): placas casi rectangulares en filas, abombadas, con surcos hondos."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    filas = max(1, round(th / 2.5))
    py = th / filas
    fila = np.floor(y / py).astype(int) % filas
    rng = np.random.default_rng(30801)
    cols = rng.integers(9, 14, filas)
    ancho = tw / cols[fila]
    desf = rng.uniform(0, 1, filas)[fila]
    col = np.floor(x / ancho + desf).astype(int)
    u = ((x / ancho + desf) % 1.0) - 0.5
    v = ((y / py) % 1.0) - 0.5
    ondula = (ruido_cm(forma, cx, cy, 1.0, 30802, octavas=2) - 0.5) * 0.18
    du = (0.5 - np.abs(u + ondula)) * ancho
    dv = (0.5 - np.abs(v - ondula)) * py
    placa = np.sqrt(suave(du, 0.05, 0.9) * suave(dv, 0.05, 0.9))
    valor = np.random.default_rng(30804).uniform(0, 1, (filas, 16))[fila, col % 16]
    grano = ruido_cm(forma, cx, cy, 0.05, 30803, octavas=2) - 0.5
    lum = 0.25 + 0.38 * placa + 0.08 * (valor - 0.5) + 0.04 * grano
    return gris(lum, (1.0, 0.95, 0.85)), 0.55 - 0.15 * placa, 0.1 + 0.8 * placa + 0.04 * grano


def avestruz(forma, cx, cy):
    """Avestruz (cuero): bultitos de los cañones de las plumas repartidos sobre piel lisa."""
    tw, th = forma[1] * cx, forma[0] * cy

    def bulto(u, v):
        r = u * u + v * v
        return np.where(r < 1, np.sqrt(np.clip(1 - r, 0, 1)), 0.0)

    cima, _, _, _ = esparcir(forma, cx, cy, tw * th / 2.2, 0.45, 0.45, 30901, bulto, variar=0.3)
    b = np.clip(cima, 0, 1)
    grano = ruido_cm(forma, cx, cy, 0.04, 30902, octavas=2) - 0.5
    color = gris(0.52 - 0.1 * b + 0.03 * grano)
    return color, 0.5 - 0.1 * b, 0.3 + 0.55 * b + 0.05 * grano


def plumas(forma, cx, cy):
    """Plumas superpuestas en una dirección: raquis claro y barbas finas en espiga."""
    tw, th = forma[1] * cx, forma[0] * cy

    def pluma(u, v):
        dentro = (u * u + v * v * (1 + 0.6 * u)) < 1
        return np.where(dentro, 1.2 - 0.4 * u, 0.0)

    cima, quien, u, v = esparcir(forma, cx, cy, tw * th / 5.0, 3.5, 1.2, 31001, pluma,
                                 angulo=-math.pi / 2, variar=0.25)
    raquis = suave(0.08 - np.abs(v), 0.0, 0.05) * (quien >= 0)
    barba = 0.5 + 0.5 * np.sin(2 * math.pi * (u * 3.5 * 7 + np.abs(v) * 6))
    borde = suave(cima, 0.0, 0.15)
    rng = np.random.default_rng(31002)
    tono = rng.uniform(0.85, 1.15, int(tw * th / 5.0) + 1)[np.maximum(quien, 0)]
    lum = (0.42 + 0.12 * barba) * tono * (0.6 + 0.4 * borde) + 0.3 * raquis
    color = gris(lum, (1.0, 0.97, 0.92))
    return color, 0.55 - 0.1 * raquis, 0.3 + 0.25 * cima + 0.05 * barba + 0.1 * raquis


def escamas_pez(forma, cx, cy, paso=0.6):
    """Escamas de pez: filas de escamas redondas que se solapan (la de abajo tapa a la de arriba), irisadas."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px = tw / max(1, round(tw / paso))
    py = px / 2
    r = px * 0.62
    j0 = np.floor(y / py).astype(np.int64)
    h = np.full(forma, -1.0)
    for dj in (-2, -1, 0, 1):
        j = j0 + dj
        cyj = j * py
        desf = 0.5 * (j % 2)
        i = np.round(x / px - desf)
        for di in (-1, 0, 1):
            cxi = (i + di + desf) * px
            d = np.hypot(x - cxi, y - cyj) / r
            dentro = (d < 1) & (y >= cyj - 0.15 * r)
            h = np.where(dentro, d, h)  # la fila más baja (dj mayor) queda encima
    h = np.where(h < 0, 1.0, h)
    filo = suave(h, 0.85, 1.0)
    iris = 0.5 + 0.5 * np.sin(2 * math.pi * (y / th * 3 + 0.6 * h))
    tono = np.stack([0.9 + 0.2 * iris, 0.95 + 0.1 * (1 - iris), 1.05 + 0.1 * iris], axis=-1)
    color = gris(0.68 - 0.3 * filo) * tono
    return color, 0.45 - 0.1 * (1 - filo), 0.3 + 0.5 * h - 0.3 * filo


def lana_oveja(forma, cx, cy):
    """Vellón de oveja: rizos apretados en mechones esponjosos."""
    mechon = ruido_cm(forma, cx, cy, 1.5, 31201, octavas=3)
    rizo = 1 - np.abs(2 * ruido_cm(forma, cx, cy, 0.25, 31202, octavas=2) - 1)
    fibra = estirado(forma, cx, cy, 0.03, 31203, 5.0, octavas=2) - 0.5
    hueco = 1 - suave(mechon, 0.35, 0.5)
    lum = 0.62 + 0.12 * rizo + 0.06 * fibra - 0.3 * hueco
    color = gris(lum, (1.03, 1.0, 0.9))
    return color, 0.5 + 0.05 * fibra, 0.2 + 0.4 * mechon + 0.3 * rizo + 0.05 * fibra


def tiburon(forma, cx, cy):
    """Piel de tiburón (lija): dentículos diminutos orientados, tacto áspero, gris azulado."""
    den = hoyuelos(forma, cx, cy, 0.04, 31301, 0.55)
    hilo = estirado(forma, cx, cy, 0.05, 31302, 4.0, octavas=2) - 0.5
    sombra = ruido_cm(forma, cx, cy, 8.0, 31303, octavas=3) - 0.5
    lum = 0.5 + 0.06 * den + 0.04 * hilo + 0.18 * sombra
    return gris(lum, (0.95, 1.0, 1.06)), 0.5 + 0.08 * den, 0.4 + 0.3 * den + 0.08 * hilo


def rana(forma, cx, cy):
    """Piel de rana o sapo: verrugas abombadas, manchas oscuras y brillo húmedo."""
    tw, th = forma[1] * cx, forma[0] * cy

    def verruga(u, v):
        r = u * u + v * v
        return np.where(r < 1, np.sqrt(np.clip(1 - r, 0, 1)), 0.0)

    cima, _, _, _ = esparcir(forma, cx, cy, tw * th / 1.5, 0.5, 0.5, 31401, verruga, variar=0.6)
    b = np.clip(cima, 0, 1)
    mancha = manchas_fractales(forma, cx, cy, 2.5, 31402, 0.3, detalle=0.4)
    lum = 0.62 - 0.38 * mancha + 0.06 * b
    color = gris(lum) * np.array([0.9, 1.1, 0.75])
    return color, 0.4 - 0.08 * b, 0.3 + 0.5 * b


def cerdo(forma, cx, cy):
    """Cuero de cerdo (serraje fino): poros en grupos de tres y grano liso."""
    tw, th = forma[1] * cx, forma[0] * cy
    n = tw * th / 0.35

    def poro(u, v):
        r = u * u + v * v
        return np.where(r < 1, 1 - r, 0.0)

    hondo = np.zeros(forma)
    c, _, _, _ = esparcir(forma, cx, cy, n, 0.05, 0.05, 31502, poro, variar=0.2)
    c = np.clip(c, 0, 1)
    for dx, dy in ((0.0, 0.0), (0.12, 0.05), (0.04, 0.13)):  # poros en grupos de tres
        hondo = np.maximum(hondo, np.roll(c, (int(round(dy / cy)), int(round(dx / cx))), (0, 1)))
    grano = ruido_cm(forma, cx, cy, 0.08, 31503, octavas=2) - 0.5
    lum = 0.55 - 0.2 * hondo + 0.04 * grano
    return gris(lum, (1.05, 0.98, 0.9)), 0.5 + 0.08 * hondo, 0.6 - 0.45 * hondo + 0.05 * grano


def pergamino(forma, cx, cy):
    """Pergamino (piel curtida en blanco): fibras, manchas translúcidas y algún folículo."""
    fibra = estirado(forma, cx, cy, 0.3, 31601, 4.0, octavas=3) - 0.5
    nube = ruido_cm(forma, cx, cy, 6.0, 31602, octavas=4) - 0.5
    mancha = manchas_fractales(forma, cx, cy, 3.0, 31603, 0.12, detalle=0.5)
    foliculo = salpicado(forma, cx, cy, 0.06, 31604, 0.03, borde=0.02)
    lum = 0.6 + 0.06 * fibra + 0.14 * nube - 0.12 * mancha - 0.15 * foliculo
    return gris(lum, (1.05, 1.0, 0.86)), 0.5 + 0.05 * fibra, 0.5 + 0.1 * fibra + 0.1 * nube


def panal(forma, cx, cy, radio=0.31):
    """Panal de cera: celdas hexagonales hondas con paredes finas, color miel."""
    x, y = rejilla(forma, cx, cy)
    _, _, pxc, pyc = patrones._centro_hex(x, y, radio)
    dx, dy = np.abs(x - pxc), np.abs(y - pyc)
    hexd = np.maximum(dx, dx * 0.5 + dy * math.sqrt(3) / 2)
    apotema = radio * math.sqrt(3) / 2
    pared = suave(hexd, apotema - 0.045, apotema - 0.015)
    fondo = 1 - hexd / apotema
    lum = 0.42 + 0.35 * pared - 0.12 * fondo
    color = gris(lum) * np.array([1.2, 0.95, 0.55])
    return color, 0.45 - 0.1 * pared, 0.1 + 0.85 * pared


def nacar(forma, cx, cy):
    """Nácar: capas onduladas finas y tornasoladas, muy pulido."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    giro = (ruido_cm(forma, cx, cy, 3.0, 31801, octavas=4) - 0.5) * 20
    fase = 2 * math.pi * 30 * y / th + giro
    capa = 0.5 + 0.5 * np.sin(fase)
    iris = 0.5 + 0.5 * np.sin(fase / 6 + 2 * math.pi * ruido_cm(forma, cx, cy, 2.0, 31802))
    tono = np.stack([1.0 + 0.22 * iris, 1.0 + 0.16 * (1 - iris), 1.0 + 0.22 * np.cos(math.pi * iris)], axis=-1)
    color = gris(0.5 + 0.12 * capa) * tono
    return color, 0.48 + 0.02 * capa, 0.5 + 0.02 * capa


def asta(forma, cx, cy):
    """Asta o cuerno pulido: fibras largas, vetas casi negras y zonas claras translúcidas."""
    fibra = estirado(forma, cx, cy, 0.3, 31901, 12.0, eje="y", octavas=4)
    veta = estirado(forma, cx, cy, 1.5, 31902, 6.0, eje="y", octavas=4)
    q1, q2 = np.quantile(veta, [0.3, 0.75])
    lum = 0.12 + 0.75 * suave(veta, q1, q2) + 0.12 * (fibra - 0.5)
    color = gris(lum, (1.08, 1.0, 0.85))
    return color, 0.5 + 0.03 * (fibra - 0.5), 0.5 + 0.06 * (fibra - 0.5)


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.8, familia="Animal", **kw):
    def f(forma, cx, cy):
        r = funcion(forma, cx, cy, **kw)
        color = np.clip(r[0] * (0.5 / max(1e-6, float(r[0].mean()))), 0.0, 1.0)
        return (color,) + tuple(r[1:])

    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


ACABADOS = [
    _a("leopardo", leopardo, "Pelaje de leopardo", (30.0, 30.0), 0.1, "#b89058", ["leopardo", "estampado animal"]),
    _a("tigre", tigre, "Pelaje de tigre", (40.0, 40.0), 0.1, "#b88a58", ["tigre", "rayas"]),
    _a("cebra", cebra, "Pelaje de cebra", (40.0, 40.0), 0.05, "#a0a0a0", ["cebra", "rayas"]),
    _a("vaca", vaca, "Pelaje de vaca", (100.0, 100.0), 0.08, "#a0a0a0", ["vaca", "piel de vaca", "frisona"]),
    _a("jirafa", jirafa, "Pelaje de jirafa", (60.0, 60.0), 0.05, "#a88860", ["jirafa"]),
    _a("dalmata", dalmata, "Pelaje de dálmata", (30.0, 30.0), 0.05, "#e4e2dc", ["dalmata", "lunares"]),
    _a("atigrado", atigrado, "Pelaje atigrado (gato)", (20.0, 20.0), 0.1, "#9a8060", ["gato", "atigrado"]),
    _a("piel_serpiente", serpiente, "Piel de serpiente (pitón)", (math.sqrt(3) * 0.3 * 40, 0.3 * 3 * 13), 0.04,
       "#a89870", ["serpiente", "piton", "bolso"], rug=0.6),
    _a("cocodrilo", cocodrilo, "Cuero de cocodrilo", (30.0, 30.0), 0.2, "#5a4a3a", ["cocodrilo", "bolso",
       "cinturon"], rug=0.55),
    _a("avestruz", avestruz, "Cuero de avestruz", (15.0, 15.0), 0.08, "#8a6a4a", ["avestruz", "bolso"], rug=0.6),
    _a("plumas", plumas, "Plumas", (30.0, 30.0), 0.3, "#8a7a68", ["plumas", "ala", "pajaro"]),
    _a("escamas_pez", escamas_pez, "Escamas de pez", (12.0, 12.0), 0.05, "#a8b0b4", ["pez", "sirena", "escamas"],
       rug=0.35),
    _a("lana_oveja", lana_oveja, "Vellón de oveja", (20.0, 20.0), 0.8, "#d8d0bc", ["oveja", "lana", "vellon"],
       rug=0.95),
    _a("piel_tiburon", tiburon, "Piel de tiburón", (40.0, 40.0), 0.02, "#7a8288", ["tiburon", "lija"]),
    _a("piel_rana", rana, "Piel de rana", (10.0, 10.0), 0.1, "#6a8a4a", ["rana", "sapo", "anfibio"], rug=0.3),
    _a("cuero_cerdo", cerdo, "Cuero de cerdo", (10.0, 10.0), 0.03, "#b08a68", ["cerdo", "cuero", "guante"]),
    _a("pergamino", pergamino, "Pergamino", (40.0, 40.0), 0.02, "#d8c8a0", ["pergamino", "manuscrito",
       "mapa antiguo"]),
    _a("panal", panal, "Panal de cera", (math.sqrt(3) * 0.31 * 20, 0.31 * 3 * 7), 0.5, "#b88a3a",
       ["panal", "abeja", "miel"], rug=0.4),
    _a("nacar", nacar, "Nácar", (10.0, 10.0), 0.005, "#d8d4d0", ["nacar", "madreperla", "boton"], rug=0.15),
    _a("asta", asta, "Asta o cuerno", (20.0, 20.0), 0.01, "#8a7a60", ["cuerno", "asta", "mango de cuchillo"],
       rug=0.3),
]
