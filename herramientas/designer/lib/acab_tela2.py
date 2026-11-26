"""Acabados de tela (segundo lote): tejidos con dibujo de color (tweed, pata de gallo, escocés, vichy),
punto, pana, mimbre, lentejuelas, polar, damasco y tejidos técnicos.

Los dibujos de color salen del propio ligamento: el color que se ve en cada punto es el del hilo que
va por encima (urdimbre o trama), como en el telar.
"""

import numpy as np

from acab_tela import pelo, punto, tela
from superficie import (SARGA_2_2, SATEN_5, TAFETAN, estirado, gris, rejilla, ruido_cm,
                        salpicado, suave, tejido)

ESPIGA_SARGA = [[1, 1, 0, 0, 0, 0, 1, 1], [0, 1, 1, 0, 0, 1, 1, 0], [0, 0, 1, 1, 1, 1, 0, 0],
                [1, 0, 0, 1, 1, 0, 0, 1]]
CESTA_2 = [[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 1, 1], [0, 0, 1, 1]]


def _hilos(forma, cx, cy, paso):
    """Índice de columna (urdimbre) y de fila (trama) de cada píxel."""
    x, y = rejilla(forma, cx, cy)
    return np.floor(x / paso).astype(np.int64), np.floor(y / paso).astype(np.int64)


def _dibujo(forma, cx, cy, paso, patron, col_urd, col_tra, semilla, hueco=0.12, slub=0.3):
    """Tela con dibujo de color: ``col_urd(i)`` y ``col_tra(j)`` dan el color (RGB ~0,5) de cada hilo."""
    h, urd, fib = tejido(forma, cx, cy, paso, patron, semilla, hueco=hueco)
    i, j = _hilos(forma, cx, cy, paso)
    cu, ct = col_urd(i), col_tra(j)
    color = np.where(urd[..., None] > 0.5, cu, ct)
    irregular = estirado(forma, cx, cy, paso * 2, semilla + 1, 15.0, eje="y") - 0.5
    color = color * (1 + 0.2 * (h[..., None] - 0.6) + 0.06 * fib[..., None] + slub * 0.15 * irregular[..., None])
    altura = 0.5 + 0.45 * (h - 0.6) + 0.05 * fib
    return color, 0.5 + 0.03 * (1 - h), altura


def _paleta(*colores):
    return np.array(colores, dtype=np.float64)


def tweed(forma, cx, cy):
    """Tweed en espiga: sarga quebrada de lana gruesa con motas de colores."""
    claro, oscuro = _paleta((0.58, 0.55, 0.50), (0.36, 0.34, 0.31))
    color, rug, altura = _dibujo(forma, cx, cy, 0.06, ESPIGA_SARGA, lambda i: np.broadcast_to(claro, i.shape + (3,)),
                                 lambda j: np.broadcast_to(oscuro, j.shape + (3,)), 23501, slub=0.8)
    for k, c in enumerate(((0.70, 0.30, 0.25), (0.35, 0.50, 0.65), (0.75, 0.65, 0.35))):
        mota = salpicado(forma, cx, cy, 0.04, 23510 + k, 0.015, borde=0.02)
        color = color * (1 - mota[..., None]) + np.array(c) * mota[..., None]
    pel = ruido_cm(forma, cx, cy, 0.02, 23520) - 0.5
    return color * (1 + 0.08 * pel[..., None]), rug + 0.05, altura + 0.05 * pel


def pata_de_gallo(forma, cx, cy):
    """Pata de gallo: sarga 2/2 con 4 hilos oscuros y 4 claros en urdimbre y trama."""
    pal = _paleta((0.66, 0.64, 0.60), (0.16, 0.15, 0.15))

    def col(k):
        return pal[(k // 4) % 2]
    return _dibujo(forma, cx, cy, 0.05, SARGA_2_2, col, col, 23601)


def _franjas(secuencia, paleta):
    """Secuencia de franjas (color, hilos) en espejo, como un tartán: devuelve función hilo -> color."""
    tabla = []
    for c, n in secuencia:
        tabla += [c] * n
    tabla = tabla + tabla[::-1]
    tabla = np.array(tabla)
    pal = _paleta(*paleta)
    return lambda k: pal[tabla[k % len(tabla)]], len(tabla)


def tartan(forma, cx, cy):
    """Tela escocesa (tartán): franjas de colores cruzadas en sarga 2/2."""
    col, n = _franjas([(0, 16), (1, 4), (0, 4), (2, 12), (3, 2), (2, 10)],
                      [(0.62, 0.12, 0.12), (0.10, 0.10, 0.10), (0.12, 0.25, 0.18), (0.75, 0.70, 0.30)])
    return _dibujo(forma, cx, cy, 0.05, SARGA_2_2, col, col, 23701)


def vichy(forma, cx, cy):
    """Vichy: cuadros de un color y blanco en tafetán; donde se cruzan los dos colores sale el oscuro."""
    pal = _paleta((0.62, 0.62, 0.62), (0.30, 0.30, 0.30))

    def col(k):
        return pal[(k // 8) % 2]
    return _dibujo(forma, cx, cy, 0.04, TAFETAN, col, col, 23801, slub=0.1)


def pana(forma, cx, cy, canal=0.3):
    """Pana: canutillos verticales de pelo corto separados por surcos."""
    x, _ = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = tw / max(1, round(tw / canal))
    f = (x % p) / p
    canuto = np.sqrt(np.clip(np.sin(np.pi * f), 0, 1))
    pel = ruido_cm(forma, cx, cy, 0.01, 23901, octavas=2) - 0.5
    marca = ruido_cm(forma, cx, cy, 2.0, 23902, octavas=3) - 0.5
    color = gris(0.5 + 0.1 * (canuto - 0.6) + 0.04 * pel + 0.06 * marca)
    return color, 0.5 + 0.04 * pel, 0.15 + 0.7 * canuto + 0.1 * pel


def canale(forma, cx, cy, ancho=0.4, alto=0.32):
    """Punto canalé 2 × 2: dos columnas del derecho salientes y dos del reves hundidas."""
    color, rug, altura = punto(forma, cx, cy, ancho=ancho, alto=alto)
    x, _ = rejilla(forma, cx, cy)
    reves = (np.floor(x / ancho).astype(np.int64) // 2) % 2 == 1
    altura = np.where(reves, 0.25 + 0.3 * (altura - 0.2), altura)
    color = color * np.where(reves[..., None], 0.85, 1.0)
    return color, rug, altura


def punto_rayas(forma, cx, cy):
    """Punto a rayas (marinero): punto de media con franjas de 8 vueltas."""
    color, rug, altura = punto(forma, cx, cy, ancho=0.32, alto=0.25)
    _, y = rejilla(forma, cx, cy)
    franja = (np.floor(y / (0.25 * 8)).astype(np.int64) % 2) == 1
    color = np.where(franja[..., None], color * np.array([0.30, 0.34, 0.55]) / 0.5, color * 1.25)
    return color, rug, altura


def mimbre(forma, cx, cy):
    """Mimbre / ratán tejido: tiras planas anchas al tresbolillo, con fibra y huecos oscuros."""
    h, urd, fib = tejido(forma, cx, cy, 1.2, TAFETAN, 24001, hueco=0.2, fibra=1.5)
    hueco = (h <= 0.0).astype(float)
    tono = ruido_cm(forma, cx, cy, 3.0, 24002, octavas=3) - 0.5
    color = gris(0.5 + 0.08 * (h - 0.7) + 0.06 * fib + 0.05 * tono - 0.35 * hueco)
    return color, 0.5 + 0.05 * fib + 0.1 * hueco, 0.5 + 0.45 * (h - 0.6) + 0.1 * fib


def lentejuelas(forma, cx, cy, radio=0.3):
    """Lentejuelas cosidas en filas que se solapan como escamas: cada una refleja a su manera."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    sx = tw / max(1, round(tw / (radio * 1.7)))
    sy = th / max(1, round(th / (radio * 1.15)))
    filas = int(round(th / sy))
    rng = np.random.default_rng(24101)
    tono = rng.uniform(0.75, 1.15, (filas, int(round(tw / sx)) + 1))
    color = np.full(forma, 0.18)
    altura = np.zeros(forma)
    disco = np.zeros(forma)
    for j in range(filas):
        y0 = j * sy
        desplaza = 0.5 * sx * (j % 2)
        u = ((x - desplaza) % sx) - sx / 2
        v = (y - y0 + th / 2) % th - th / 2
        d = np.hypot(u, v)
        dentro = d < radio
        col = np.floor(((x - desplaza) % tw) / sx).astype(np.int64)
        brillo = tono[j][np.clip(col, 0, tono.shape[1] - 1)]
        agujero = d < radio * 0.12
        color = np.where(dentro, np.where(agujero, 0.25, 0.5 * brillo), color)
        altura = np.where(dentro, 0.5 + 0.3 * (v / radio) + 0.05 * (j % 2), altura)
        disco = np.where(dentro, 1.0, disco)
    return gris(color), 0.5 - 0.2 * disco + 0.3 * (1 - disco), altura, disco


def polar(forma, cx, cy):
    """Forro polar: fibra esponjada en grumitos (bolitas), sin trama visible."""
    grumo = ruido_cm(forma, cx, cy, 0.12, 24201, octavas=2)
    pel = ruido_cm(forma, cx, cy, 0.01, 24202, octavas=2) - 0.5
    bolita = suave(ruido_cm(forma, cx, cy, 0.08, 24203), 0.68, 0.75)
    color = gris(0.5 + 0.06 * (grumo - 0.5) + 0.04 * pel + 0.04 * bolita)
    return color, 0.5 + 0.03 * pel, 0.3 + 0.4 * grumo + 0.1 * pel + 0.15 * bolita


def gabardina(forma, cx, cy):
    """Gabardina: sarga fina y apretada de líneas diagonales marcadas."""
    return tela(forma, cx, cy, paso=0.025, patron=SARGA_2_2, hueco=0.06, slub=0.1, contraste=0.1, pelusa=0.1)


def hule(forma, cx, cy):
    """Hule (tela plastificada): la trama apenas se adivina bajo una capa lisa y brillante."""
    color, rug, altura = tela(forma, cx, cy, paso=0.05, slub=0.2, contraste=0.03, pelusa=0.0)
    return color, 0.5 + 0.2 * (rug - 0.5), 0.5 + 0.3 * (altura - 0.5)


def pelo_largo(forma, cx, cy):
    """Alfombra de pelo largo (shaggy): mechones gruesos que caen hacia distintos lados."""
    color, rug, altura = pelo(forma, cx, cy, largo=25.0)
    mechon = ruido_cm(forma, cx, cy, 1.2, 24301, octavas=2) - 0.5
    hueco = 1 - suave(mechon, -0.3, -0.05)
    return color * (1 - 0.15 * hueco[..., None]), rug, altura + 0.4 * mechon - 0.2 * hueco


def lana_hervida(forma, cx, cy):
    """Lana cocida (abatanada): punto que apenas se ve bajo una capa de fieltro."""
    color, rug, altura = punto(forma, cx, cy, ancho=0.25, alto=0.2, pelusa=1.0)
    fx = estirado(forma, cx, cy, 0.01, 24401, 8.0) - 0.5
    fy = estirado(forma, cx, cy, 0.01, 24402, 8.0, eje="y") - 0.5
    fieltro = np.maximum(fx, fy)
    color = gris(0.5 + 0.3 * (color.mean(axis=2) - 0.5) + 0.06 * fieltro)
    return color, rug, 0.5 + 0.3 * (altura - 0.5) + 0.2 * fieltro


def damasco_tela(forma, cx, cy):
    """Damasco: dibujo simétrico de ramas en raso brillante sobre fondo de sarga mate."""
    a = ruido_cm(forma, cx, cy, 2.0, 24501, octavas=3)
    sim = 0.5 * (a + a[:, ::-1])
    dibujo = suave(sim, 0.53, 0.56)
    h1, u1, f1 = tejido(forma, cx, cy, 0.04, SATEN_5, 24502, hueco=0.04)
    h2, u2, f2 = tejido(forma, cx, cy, 0.04, SARGA_2_2, 24503, hueco=0.06)
    h = h1 * dibujo + h2 * (1 - dibujo)
    color = gris(0.5 + 0.06 * dibujo + 0.04 * (h - 0.6))
    return color, 0.5 - 0.2 * dibujo + 0.05, 0.5 + 0.3 * (h - 0.6) + 0.05 * dibujo


def neopreno(forma, cx, cy):
    """Neopreno: punto finísimo laminado sobre espuma; casi liso, mate."""
    color, rug, altura = punto(forma, cx, cy, ancho=0.05, alto=0.04, pelusa=0.2)
    return gris(0.5 + 0.3 * (color.mean(axis=2) - 0.5)), rug, 0.5 + 0.4 * (altura - 0.5)


def cordura(forma, cx, cy):
    """Cordura / nailon balístico: panamá 2 × 2 de hilo grueso, apretado y algo brillante."""
    return tela(forma, cx, cy, paso=0.05, patron=CESTA_2, hueco=0.08, slub=0.1, contraste=0.08, pelusa=0.05)


def muselina(forma, cx, cy):
    """Muselina / gasa: tafetán muy abierto con huecos entre hilos finos."""
    h, urd, fib = tejido(forma, cx, cy, 0.05, TAFETAN, 24601, hueco=0.45, fibra=0.4)
    hueco = (h <= 0.0).astype(float)
    color = gris(0.5 + 0.04 * (h - 0.6) - 0.25 * hueco)
    return color, 0.5 + 0.05 * hueco, 0.5 + 0.45 * (h - 0.6)


def gofre(forma, cx, cy, celda=0.6):
    """Tejido de gofre (nido de abeja): cuadritos hundidos con bordes altos, tela de toalla de cocina."""
    color, rug, altura = tela(forma, cx, cy, paso=0.05, slub=0.2, contraste=0.05)
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = tw / max(1, round(tw / celda)), th / max(1, round(th / celda))
    u = np.abs((x % px) / px - 0.5) * 2
    v = np.abs((y % py) / py - 0.5) * 2
    borde = np.maximum(u, v)
    cuenco = 1 - borde ** 2
    color = color * (1 - 0.1 * cuenco[..., None])
    return color, rug, 0.6 + 0.2 * (altura - 0.5) - 0.4 * cuenco


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.8, familia="Tela", metal=0.0, **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=metal, recomendado_para=para)


ACABADOS = [
    _a("tweed", tweed, "Tweed en espiga", (4.8, 4.8), 0.05, "#9a9a9a", ["tweed", "americana", "chaqueta"]),
    _a("pata_de_gallo", pata_de_gallo, "Pata de gallo", (4.0, 4.0), 0.03, "#9a9a9a", ["pata de gallo",
       "houndstooth"]),
    _a("tartan", tartan, "Tela escocesa", (9.6, 9.6), 0.03, "#9a9a9a", ["escoces", "tartan", "cuadros"]),
    _a("vichy", vichy, "Vichy", (6.4, 6.4), 0.02, "#c04050", ["vichy", "cuadritos", "mantel"]),
    _a("pana", pana, "Pana", (6.0, 6.0), 0.08, "#8a6a3a", ["pana", "corduroy"], rug=0.75),
    _a("punto_canale", canale, "Punto canalé", (8.0, 8.0), 0.2, "#4a5a6a", ["canale", "punto", "jersey",
       "puño"]),
    _a("punto_fino", punto, "Punto fino (camiseta)", (3.0, 3.0), 0.02, "#d8d8d8", ["camiseta", "jersey fino",
       "punto"], ancho=0.12, alto=0.1, pelusa=0.3),
    _a("punto_rayas", punto_rayas, "Punto a rayas", (8.0, 8.0), 0.15, "#d8d4cc", ["marinero", "rayas"]),
    _a("mimbre", mimbre, "Mimbre tejido", (24.0, 24.0), 0.3, "#c09a60", ["mimbre", "ratan", "cesto"], rug=0.6),
    _a("lentejuelas", lentejuelas, "Lentejuelas", (10.0, 10.0), 0.1, "#c8a050", ["lentejuela", "brillo",
       "disfraz"], rug=0.15, metal=1.0),
    _a("forro_polar", polar, "Forro polar", (6.0, 6.0), 0.06, "#3a6a4a", ["polar", "forro"], rug=0.95),
    _a("gabardina", gabardina, "Gabardina", (2.0, 2.0), 0.01, "#b8a47a", ["gabardina", "chino"]),
    _a("hule", hule, "Hule", (4.0, 4.0), 0.005, "#c85a4a", ["hule", "plastificad", "mantel"], rug=0.3),
    _a("alfombra_pelo_largo", pelo_largo, "Alfombra de pelo largo", (20.0, 20.0), 1.5, "#d8d0c0",
       ["shaggy", "pelo largo", "alfombra"], rug=0.9),
    _a("lana_cocida", lana_hervida, "Lana cocida", (5.0, 5.0), 0.05, "#7a4a3a", ["lana cocida", "abrigo",
       "abatanad"], rug=0.9),
    _a("damasco_tela", damasco_tela, "Damasco (tela)", (20.0, 20.0), 0.01, "#a89060", ["damasco", "brocado",
       "tapiceria"], rug=0.5),
    _a("neopreno", neopreno, "Neopreno", (2.0, 2.0), 0.01, "#202428", ["neopreno", "traje de buceo"], rug=0.7),
    _a("cordura", cordura, "Cordura", (4.0, 4.0), 0.02, "#3a4030", ["cordura", "balistico", "mochila"], rug=0.6),
    _a("muselina", muselina, "Muselina / gasa", (4.0, 4.0), 0.01, "#ece6d8", ["muselina", "gasa", "venda"]),
    _a("gofre", gofre, "Tela de gofre", (6.0, 6.0), 0.1, "#e8e4dc", ["gofre", "nido de abeja", "waffle"]),
]
