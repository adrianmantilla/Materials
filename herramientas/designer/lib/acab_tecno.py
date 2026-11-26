"""Acabados técnicos: placa de circuito, chapas perforadas y expandidas, mallas, rejillas, panal de aluminio,
panel solar, píxeles de pantalla, carbono forjado, kevlar, disipador, espuma acústica, funda trenzada,
remaches, panel de ciencia ficción, lámina holográfica y papel milimetrado.

Las piezas que se repiten (agujeros, celdas, píxeles) caben un número entero de veces en la tesela.
"""

import math

import numpy as np

import patrones
from acab_plastico2 import _reticula
from superficie import SARGA_2_2, TAFETAN, estirado, gris, rejilla, ruido_cm, suave, tejido


def _cuenta(total, paso):
    return total / max(1, round(total / paso))


def _grano(forma, cx, cy, semilla, tam=0.02):
    return ruido_cm(forma, cx, cy, tam, semilla, octavas=2) - 0.5


def pcb(forma, cx, cy):
    """Placa de circuito: máscara verde, pistas de cobre en ángulos de 45°, pads y vías."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    paso = _cuenta(tw, 0.254)
    rng = np.random.default_rng(34001)
    pista = np.zeros(forma)
    gx, gy = int(round(tw / paso)), int(round(th / paso))
    # Pistas: tramos rectos horizontales/verticales con un quiebro a 45°, sobre la rejilla de 0,254 cm.
    for _ in range(int(tw * th / 0.6)):
        i0, j0 = rng.integers(0, gx), rng.integers(0, gy)
        largo = rng.integers(4, 30)
        horiz = rng.uniform() < 0.5
        diag = rng.integers(0, 6)
        ancho = rng.choice([0.03, 0.05, 0.08])
        pts = []
        i, j = i0, j0
        for k in range(largo):
            pts.append((i, j))
            if k == diag:
                i, j = i + 1, j + 1
            elif horiz:
                i += 1
            else:
                j += 1
        finos = []
        for (a, b), (a2, b2) in zip(pts[:-1], pts[1:]):
            for t in np.linspace(0, 1, 6, endpoint=False):
                finos.append((a + (a2 - a) * t, b + (b2 - b) * t))
        for (a, b) in finos:
            cxp, cyp = (a % gx + 0.5) * paso, (b % gy + 0.5) * paso
            ii = np.arange(int((cxp - paso) / cx), int((cxp + paso) / cx) + 1)
            jj = np.arange(int((cyp - paso) / cy), int((cyp + paso) / cy) + 1)
            px = (ii[None, :] + 0.5) * cx - cxp
            py = (jj[:, None] + 0.5) * cy - cyp
            d = np.hypot(px, py)
            sub = np.ix_(jj % forma[0], ii % forma[1])
            pista[sub] = np.maximum(pista[sub], suave(ancho / 2 - d, 0, 0.008))
    pad = np.zeros(forma)
    via = np.zeros(forma)
    for _ in range(int(tw * th / 1.5)):
        cxp, cyp = (rng.integers(0, gx) + 0.5) * paso, (rng.integers(0, gy) + 0.5) * paso
        r = rng.choice([0.06, 0.08, 0.1])
        ii = np.arange(int((cxp - 2 * r) / cx), int((cxp + 2 * r) / cx) + 2)
        jj = np.arange(int((cyp - 2 * r) / cy), int((cyp + 2 * r) / cy) + 2)
        px = (ii[None, :] + 0.5) * cx - cxp
        py = (jj[:, None] + 0.5) * cy - cyp
        d = np.hypot(px, py)
        sub = np.ix_(jj % forma[0], ii % forma[1])
        pad[sub] = np.maximum(pad[sub], (d < r).astype(float))
        via[sub] = np.maximum(via[sub], (d < r * 0.4).astype(float))
    pista = np.clip(pista, 0, 1)
    verde = gris(np.full(forma, 0.42)) * np.array([0.55, 1.25, 0.65])
    cobre = gris(np.full(forma, 0.62)) * np.array([1.25, 1.1, 0.55])
    estano = gris(np.full(forma, 0.78))
    color = verde * (1 + 0.45 * pista[..., None])
    color = np.where(pad[..., None] > 0, estano, color)
    color = np.where(via[..., None] > 0, 0.15, color)
    del cobre
    rug = 0.4 - 0.1 * pista - 0.15 * pad
    altura = 0.45 + 0.08 * pista + 0.12 * pad - 0.4 * via
    metal = pad * (1 - via)
    return color, rug, altura, metal


def chapa_perforada(forma, cx, cy, paso=0.8, agujero=0.25):
    """Chapa perforada de agujeros redondos al tresbolillo."""
    u, v = _reticula(forma, cx, cy, paso)
    d = np.hypot(u, v) * paso
    hueco = d < agujero
    canto = suave(agujero + 0.03 - d, 0, 0.03) * ~hueco
    grano = estirado(forma, cx, cy, 0.05, 34101, 8.0) - 0.5
    lum = np.where(hueco, 0.08, 0.6 + 0.05 * grano - 0.1 * canto)
    return gris(lum), 0.5 + 0.05 * grano + 0.2 * hueco, np.where(hueco, 0.0, 0.6 - 0.1 * canto), (~hueco) * 1.0


def rejilla_altavoz(forma, cx, cy):
    """Rejilla de altavoz: agujeritos hexagonales muy juntos en chapa negra."""
    x, y = rejilla(forma, cx, cy)
    r = 0.12
    _, _, pxc, pyc = patrones._centro_hex(x, y, r)
    dx, dy = np.abs(x - pxc), np.abs(y - pyc)
    hexd = np.maximum(dx, dx * 0.5 + dy * math.sqrt(3) / 2)
    hueco = hexd < r * math.sqrt(3) / 2 - 0.03
    lum = np.where(hueco, 0.05, 0.55)
    return gris(lum), np.where(hueco, 0.8, 0.45), np.where(hueco, 0.0, 0.7), (~hueco) * 0.8


def malla_metalica(forma, cx, cy, paso=0.4):
    """Malla metálica tejida (tela de alambre): hilos redondos que suben y bajan, huecos oscuros."""
    alt, _, fib = tejido(forma, cx, cy, paso, TAFETAN, 34301, hueco=0.55, fibra=0.1)
    hueco = alt <= 0.01
    lum = np.where(hueco, 0.05, 0.4 + 0.4 * alt)
    return gris(lum), np.where(hueco, 0.8, 0.35 - 0.1 * alt), alt, (~hueco) * 1.0


def malla_mosquitera(forma, cx, cy):
    """Mosquitera: malla fina de fibra gris, casi translúcida, con hilos sueltos."""
    alt, _, fib = tejido(forma, cx, cy, 0.12, TAFETAN, 34401, hueco=0.6, fibra=0.2)
    hueco = alt <= 0.01
    lum = np.where(hueco, 0.2, 0.5 + 0.3 * alt)
    return gris(lum), np.full(forma, 0.5), alt


def metal_expandido(forma, cx, cy, ancho=3.0, alto=1.5):
    """Metal desplegado: rombos abiertos en chapa estirada, con los nervios inclinados."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    aw, ah = _cuenta(tw, ancho), _cuenta(th, alto * 2) / 2
    fila = np.floor(y / ah)
    u = ((x / aw + 0.5 * (fila % 2)) % 1.0) - 0.5
    v = ((y / ah) % 1.0) - 0.5
    rombo = np.abs(u) * 2 + np.abs(v) * 2
    hueco = rombo < 0.72
    nervio = suave(rombo, 0.72, 0.9)
    lum = np.where(hueco, 0.06, 0.45 + 0.25 * nervio + 0.1 * np.sign(v) * (1 - nervio))
    return gris(lum), np.where(hueco, 0.8, 0.4), np.where(hueco, 0.0, 0.4 + 0.4 * nervio), (~hueco) * 1.0


def panal_aluminio(forma, cx, cy, radio=0.5):
    """Núcleo de panal de aluminio: paredes finísimas brillantes y celdas hondas."""
    x, y = rejilla(forma, cx, cy)
    _, _, pxc, pyc = patrones._centro_hex(x, y, radio)
    dx, dy = np.abs(x - pxc), np.abs(y - pyc)
    hexd = np.maximum(dx, dx * 0.5 + dy * math.sqrt(3) / 2)
    ap = radio * math.sqrt(3) / 2
    pared = suave(hexd, ap - 0.03, ap - 0.01)
    fondo = hexd / ap
    lum = 0.15 + 0.25 * fondo + 0.55 * pared
    return gris(lum), 0.4 - 0.1 * pared, 0.05 + 0.9 * pared, np.full(forma, 1.0)


def rejilla_ventilacion(forma, cx, cy):
    """Rejilla de ventilación: ranuras alargadas en filas desplazadas sobre chapa pintada."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = _cuenta(tw, 5.0), _cuenta(th, 1.2)
    fila = np.floor(y / py)
    u = ((x / px + 0.5 * (fila % 2)) % 1.0 - 0.5) * px
    v = ((y / py) % 1.0 - 0.5) * py
    largo, ancho = 1.9, 0.25
    d = np.hypot(np.maximum(np.abs(u) - (largo - ancho), 0), v)
    hueco = d < ancho
    labio = suave(ancho + 0.08 - d, 0, 0.08) * ~hueco
    lum = np.where(hueco, 0.06, 0.6 - 0.12 * labio)
    return gris(lum), np.where(hueco, 0.8, 0.5), np.where(hueco, 0.0, 0.6 + 0.1 * labio)


def panel_solar(forma, cx, cy):
    """Panel solar: células de silicio azul oscuro con dedos plateados finos y dos barras colectoras."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    lado = _cuenta(tw, 15.6)
    u, v = (x % lado) / lado, (y % lado) / lado
    hueco = (np.minimum(u, 1 - u) < 0.012) | (np.minimum(v, 1 - v) < 0.012)
    dedo = (np.abs(((v * lado) % 0.2) - 0.1) < 0.008)
    barra = (np.abs(u - 0.33) < 0.006) | (np.abs(u - 0.67) < 0.006)
    cristal = ruido_cm(forma, cx, cy, 0.3, 34901, octavas=3) - 0.5
    celda = gris(0.35 + 0.08 * cristal) * np.array([0.55, 0.75, 1.5])
    color = np.where(dedo[..., None] | barra[..., None], 0.75, celda)
    color = np.where(hueco[..., None], 0.85, color)
    return color, np.where(barra | dedo, 0.35, 0.2), 0.5 + 0.05 * (barra | dedo) - 0.05 * hueco


def pixeles(forma, cx, cy, paso=0.03):
    """Pantalla vista de muy cerca: subpíxeles rojo, verde y azul en columnas, con rejilla negra."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = _cuenta(tw, paso), _cuenta(th, paso)
    u, v = (x % px) / px, (y % py) / py
    canal = np.floor(u * 3).astype(int)
    du = (u * 3) % 1.0
    luz = (np.abs(du - 0.5) < 0.4) & (np.abs(v - 0.5) < 0.45)
    imagen = ruido_cm(forma, cx, cy, 0.6, 35001, octavas=3)
    rgb = np.stack([canal == 0, canal == 1, canal == 2], axis=-1) * 1.0
    nivel = 0.4 + 0.6 * np.stack([imagen, ruido_cm(forma, cx, cy, 0.6, 35002, octavas=3),
                                  ruido_cm(forma, cx, cy, 0.6, 35003, octavas=3)], axis=-1)
    color = rgb * nivel * luz[..., None] * 1.3 + 0.18 * luz[..., None] + 0.22
    return color, np.full(forma, 0.15), np.full(forma, 0.5)


def carbono_forjado(forma, cx, cy):
    """Carbono forjado: trozos de fibra prensados al azar, vetas grises brillantes sobre negro."""
    from superficie import celdas
    ids, dist, valor = celdas(forma, cx, cy, 0.45, 35101, temblor=1.0, estirar=3.0)
    ang = valor * math.pi
    x, y = rejilla(forma, cx, cy)
    hebra = 0.5 + 0.5 * np.sin((x * np.cos(ang) + y * np.sin(ang)) * 2 * math.pi / 0.03)
    brillo = 0.5 + 0.5 * np.cos(2 * ang)
    lum = 0.04 + 0.5 * brillo ** 3 * (0.7 + 0.3 * hebra) + 0.03 * suave(dist, 0, 0.05)
    return gris(lum), np.full(forma, 0.2) + 0.05 * hebra, 0.5 + 0.02 * hebra


def kevlar(forma, cx, cy):
    """Kevlar (aramida): sarga 2/2 amarilla dorada, brillo sedoso."""
    alt, urd, fib = tejido(forma, cx, cy, 0.2, SARGA_2_2, 35201, hueco=0.08, fibra=0.6)
    lum = 0.42 + 0.22 * alt + 0.08 * fib + 0.05 * urd
    color = gris(lum) * np.array([1.3, 1.08, 0.35])
    return color, 0.45 - 0.08 * alt, alt


def disipador(forma, cx, cy, paso=0.4):
    """Disipador de aluminio: aletas paralelas con el canto cepillado y valles oscuros."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = _cuenta(tw, paso)
    f = (x % p) / p
    aleta = suave(0.3 - np.abs(f - 0.5), 0, 0.04)
    cepillo = estirado(forma, cx, cy, 0.02, 35301, 30.0, eje="y") - 0.5
    lum = 0.15 + 0.55 * aleta + 0.08 * cepillo * aleta
    return gris(lum), 0.4 - 0.1 * aleta, 0.05 + 0.9 * aleta, np.full(forma, 1.0)


def espuma_acustica(forma, cx, cy, paso=5.0):
    """Espuma acústica de pirámides: puntas en damero, celdillas de espuma."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = _cuenta(tw, paso), _cuenta(th, paso)
    u, v = (x % px) / px - 0.5, (y % py) / py - 0.5
    piramide = 1 - 2 * np.maximum(np.abs(u), np.abs(v))
    poro = ruido_cm(forma, cx, cy, 0.05, 35401, octavas=2) - 0.5
    lum = 0.25 + 0.35 * piramide + 0.08 * poro + 0.12 * (u - v)
    return gris(lum), 0.5 + 0.05 * poro, 0.05 + 0.9 * piramide + 0.03 * poro


def funda_trenzada(forma, cx, cy):
    """Funda trenzada de cable: hilos en diagonal cruzados (sarga a 45°), negro y gris."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = _cuenta(tw, 0.35)
    a = ((x + y) / p) % 2.0
    b = ((x - y) / p) % 2.0
    ia, ib = np.floor(a), np.floor(b)
    arriba = ((np.floor((x + y) / p) + np.floor((x - y) / p)) % 2) == 0
    fa = np.abs((a % 1.0) - 0.5)
    fb = np.abs((b % 1.0) - 0.5)
    hilo = np.where(arriba, 1 - 2 * fa, 1 - 2 * fb)
    fibra = np.where(arriba, np.sin((x - y) * 2 * math.pi / 0.02), np.sin((x + y) * 2 * math.pi / 0.02))
    tono = np.where(arriba, 0.28, 0.48)
    lum = tono * (0.6 + 0.4 * np.sqrt(np.clip(hilo, 0, 1))) + 0.03 * fibra
    del ia, ib
    return gris(lum), 0.45 + 0.05 * fibra, 0.3 + 0.5 * np.sqrt(np.clip(hilo, 0, 1)) + 0.1 * arriba


def remaches(forma, cx, cy):
    """Chapa remachada: filas de remaches de cabeza redonda y juntas de solape."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = _cuenta(tw, 5.0), _cuenta(th, 20.0)
    u = ((x % px) / px - 0.5) * px
    fila = y % py
    v = fila - py * 0.1
    d = np.hypot(u, v)
    cabeza = np.sqrt(np.clip(1 - (d / 0.8) ** 2, 0, 1))
    solape = suave(fila, 0.0, 0.3) * (1 - suave(fila, py * 0.2, py * 0.2 + 0.3))
    grano = _grano(forma, cx, cy, 35601, 0.1)
    mancha = ruido_cm(forma, cx, cy, 8.0, 35602, octavas=3) - 0.5
    lum = 0.5 + 0.12 * mancha + 0.05 * grano + 0.3 * cabeza - 0.2 * (d < 0.85) * (d > 0.75) - 0.1 * (1 - solape) * (fila < 0.4)
    return gris(lum), 0.45 + 0.05 * grano, 0.4 + 0.5 * cabeza + 0.05 * solape, np.full(forma, 1.0)


def panel_scifi(forma, cx, cy):
    """Panel de ciencia ficción: placas rectangulares con ranuras, tornillos y zonas rebajadas."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    rng = np.random.default_rng(35701)
    alto = np.full(forma, 0.5)
    ranura = np.zeros(forma)
    for _ in range(int(tw * th / 120.0)):
        x0, y0 = rng.uniform(0, tw), rng.uniform(0, th)
        w, h = rng.choice([4.0, 6.0, 8.0, 12.0]), rng.choice([3.0, 4.0, 6.0, 10.0])
        dz = rng.choice([-0.15, 0.1, 0.2])
        u, v = (x - x0) % tw, (y - y0) % th
        dentro = (u < w) & (v < h)
        borde = dentro & ((u < 0.12) | (u > w - 0.12) | (v < 0.12) | (v > h - 0.12))
        alto = np.where(dentro, 0.5 + dz, alto)
        ranura = np.maximum(ranura, borde)
    tornillo = np.zeros(forma)
    paso = _cuenta(tw, 6.0)
    d = np.hypot(((x - paso / 2) % paso) - paso / 2, ((y - paso / 2) % paso) - paso / 2)
    tornillo = (d < 0.2) * 1.0
    alto = np.where(ranura > 0, 0.2, alto) + 0.1 * tornillo
    grano = _grano(forma, cx, cy, 35702, 0.1)
    lum = 0.45 + 0.4 * (alto - 0.5) - 0.2 * ranura + 0.03 * grano + 0.1 * tornillo
    return gris(lum), 0.45 + 0.05 * grano, alto


def holografico(forma, cx, cy):
    """Lámina holográfica: arco iris que cambia con microrrelieve en estrías."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    giro = (ruido_cm(forma, cx, cy, 4.0, 35801, octavas=3) - 0.5) * 8
    fase = 2 * math.pi * 6 * y / th + giro
    color = 0.5 + 0.35 * np.stack([np.sin(fase), np.sin(fase + 2.1), np.sin(fase + 4.2)], axis=-1)
    estria = np.sin(2 * math.pi * 300 * y / th)
    return color, 0.2 + 0.02 * estria, 0.5 + 0.01 * estria, np.full(forma, 1.0)


def milimetrado(forma, cx, cy):
    """Papel milimetrado: retícula de 1 mm fina, cada 5 mm algo más marcada y cada centímetro gruesa."""
    x, y = rejilla(forma, cx, cy)

    def linea(c, paso, ancho):
        d = np.abs(((c + paso / 2) % paso) - paso / 2)
        return suave(ancho - d, 0, ancho * 0.5)

    l = np.maximum.reduce([0.35 * np.maximum(linea(x, 0.1, 0.006), linea(y, 0.1, 0.006)),
                           0.6 * np.maximum(linea(x, 0.5, 0.009), linea(y, 0.5, 0.009)),
                           1.0 * np.maximum(linea(x, 1.0, 0.014), linea(y, 1.0, 0.014))])
    fibra = _grano(forma, cx, cy, 35901, 0.03)
    papel = gris(0.62 + 0.02 * fibra, (1.02, 1.0, 0.95))
    tinta = np.array([0.95, 0.5, 0.3]) * 0.6
    color = papel * (1 - l[..., None]) + tinta * l[..., None]
    return color, np.full(forma, 0.5) + 0.02 * fibra, 0.5 + 0.01 * fibra


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.5, metal=0.0, **kw):
    def f(forma, cx, cy):
        r = funcion(forma, cx, cy, **kw)
        color = np.clip(r[0] * (0.5 / max(1e-6, float(r[0].mean()))), 0.0, 1.0)
        rug_ = np.clip(r[1] + (0.5 - float(np.mean(r[1]))), 0.0, 1.0)
        return (color, rug_) + tuple(r[2:])

    return dict(id=id_, funcion=f, nombre=nombre, familia="Técnico", tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=metal, recomendado_para=para)


ACABADOS = [
    _a("placa_circuito", pcb, "Placa de circuito impreso", (5.08, 5.08), 0.01, "#7a8a7a", ["circuito", "pcb",
       "electronica"], rug=0.4),
    _a("chapa_perforada", chapa_perforada, "Chapa perforada redonda", (16.0, 16.0),
       0.15, "#b8bcc0", ["perforada", "chapa", "fachada"], rug=0.35, metal=1.0),
    _a("rejilla_altavoz", rejilla_altavoz, "Rejilla de altavoz", (math.sqrt(3) * 0.12 * 40, 0.12 * 3 * 23), 0.05,
       "#4a4c50", ["altavoz", "rejilla", "bafle"], rug=0.45, metal=1.0),
    _a("malla_metalica", malla_metalica, "Malla metálica tejida", (8.0, 8.0), 0.15, "#b0b4b8", ["malla",
       "tela metalica", "tamiz"], rug=0.35, metal=1.0),
    _a("malla_mosquitera", malla_mosquitera, "Mosquitera", (4.8, 4.8), 0.02, "#7a7c80", ["mosquitera",
       "malla fina"]),
    _a("metal_expandido", metal_expandido, "Metal desplegado", (30.0, 30.0), 0.4, "#9a9ea2", ["desplegado",
       "expandido", "rejilla", "pasarela"], rug=0.45, metal=1.0),
    _a("panal_aluminio", panal_aluminio, "Panal de aluminio", (math.sqrt(3) * 0.5 * 20, 0.5 * 3 * 7), 0.8,
       "#c8ccd0", ["panal", "aluminio", "aeronautica"], rug=0.3, metal=1.0),
    _a("rejilla_ventilacion", rejilla_ventilacion, "Rejilla de ventilación", (30.0, 30.0), 0.3, "#d8d8d4",
       ["ventilacion", "rejilla", "ordenador"], rug=0.45),
    _a("panel_solar", panel_solar, "Panel solar", (31.2, 31.2), 0.02, "#6a7a9a", ["panel solar", "fotovoltaico"],
       rug=0.15),
    _a("pixeles", pixeles, "Pantalla (subpíxeles)", (1.2, 1.2), 0.001, "#9a9a9a", ["pantalla", "pixel", "lcd"],
       rug=0.15),
    _a("carbono_forjado", carbono_forjado, "Carbono forjado", (10.0, 10.0), 0.002, "#6a6a6a", ["carbono forjado",
       "fibra"], rug=0.2),
    _a("kevlar", kevlar, "Kevlar", (4.0, 4.0), 0.02, "#c8a83a", ["kevlar", "aramida"], rug=0.45),
    _a("disipador", disipador, "Disipador de aletas", (8.0, 8.0), 1.0, "#b8bcc0", ["disipador", "aletas",
       "radiador"], rug=0.35, metal=1.0),
    _a("espuma_acustica", espuma_acustica, "Espuma acústica de pirámides", (30.0, 30.0), 3.0, "#5a5a5e",
       ["espuma acustica", "estudio", "insonorizar"], rug=0.95),
    _a("funda_trenzada", funda_trenzada, "Funda trenzada de cable", (7.0, 7.0), 0.05, "#7a7a7a", ["trenzado",
       "cable", "funda"], rug=0.55),
    _a("chapa_remachada", remaches, "Chapa remachada", (40.0, 40.0), 0.3, "#8a8c90", ["remache", "barco",
       "avion", "tanque"], rug=0.45, metal=1.0),
    _a("panel_scifi", panel_scifi, "Panel de ciencia ficción", (60.0, 60.0), 1.0, "#9aa0a6", ["ciencia ficcion",
       "nave", "panel"], rug=0.4),
    _a("holografico", holografico, "Lámina holográfica", (10.0, 10.0), 0.001, "#d0d0d0", ["holografico",
       "tornasol", "embalaje"], rug=0.15, metal=1.0),
    _a("papel_milimetrado", milimetrado, "Papel milimetrado", (10.0, 10.0), 0.0, "#e8e6de", ["milimetrado",
       "plano", "papel"], rug=0.85),
]
