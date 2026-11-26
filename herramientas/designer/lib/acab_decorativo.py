"""Acabados decorativos: pan de oro y plata, dorado envejecido, papeles pintados (damasco, rayas, flores),
capitoné, laca urushi, taracea, pintura patinada y esponjada, terciopelo aplastado, seda moaré, brocado,
encaje, esgrafiado, cuero repujado, papel washi, punto de cruz y rejilla de Viena.

Los adornos (damasco, brocado, esgrafiado, repujado, encaje) salen de ``_ornamento``: una suma de ondas
en coordenadas espejadas dentro de una red a medio salto, así son simétricos como los de verdad.
"""

import math

import numpy as np

from superficie import (TAFETAN, estirado, gris, manchas_fractales, rejilla, ruido_cm,
                        salpicado, suave, tejido)


def _cuenta(total, paso):
    return total / max(1, round(total / paso))


def _celda(forma, cx, cy, ancho, alto, medio_salto=True):
    """Coordenadas locales (−0,5..0,5) en una red de ``ancho × alto`` cm, con medio salto vertical."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    aw, ah = _cuenta(tw, ancho), _cuenta(th, alto)
    col = np.floor(x / aw)
    u = (x / aw) % 1.0 - 0.5
    v = (y / ah + (0.5 * (col % 2) if medio_salto else 0)) % 1.0 - 0.5
    return u, v


def _ornamento(forma, cx, cy, ancho, alto, semilla, finura=1.0, medio_salto=True):
    """Adorno simétrico (0-1) de tipo damasco en cada celda: ondas en (|u|, v) recortadas en medallón."""
    u, v = _celda(forma, cx, cy, ancho, alto, medio_salto)
    au = np.abs(u)
    rng = np.random.default_rng(semilla)
    f = np.zeros(u.shape)
    for _ in range(9):
        k1, k2 = rng.integers(1, 5) * finura, rng.integers(1, 6) * finura
        f += rng.uniform(0.5, 1.0) * np.cos(2 * math.pi * (k1 * au + k2 * v) + rng.uniform(0, 2 * math.pi))
    f = f / 9
    medallon = 1 - suave(np.hypot(au * 1.15, v * 0.95), 0.4, 0.5)
    tallo = suave(0.03 - au, 0, 0.01) * (np.abs(v) < 0.45)
    return np.clip(suave(f, -0.02, 0.03) * medallon + tallo, 0, 1)


def pan_de_oro(forma, cx, cy, plata=False):
    """Pan de oro o plata: hojas cuadradas solapadas con bordes visibles, arrugas y alguna falta."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = _cuenta(tw, 8.0)
    fila = np.floor(y / p)
    u = (x + 1.3 * fila) % p
    v = y % p
    borde = (suave(0.08 - np.minimum(u, p - u), 0, 0.04) + suave(0.08 - np.minimum(v, p - v), 0, 0.04)) > 0.1
    arruga = 1 - np.abs(2 * ruido_cm(forma, cx, cy, 1.0, 42001, octavas=4) - 1)
    falta = manchas_fractales(forma, cx, cy, 3.0, 42002, 0.04, detalle=0.6)
    lum = 0.72 + 0.12 * suave(arruga, 0.8, 1.0) - 0.1 * borde
    base = np.array([0.55, 0.25, 0.18]) if not plata else np.array([0.3, 0.3, 0.32])
    color = gris(lum) * (1 - falta[..., None]) + base * falta[..., None]
    rug = 0.25 + 0.1 * borde + 0.3 * falta
    return color, rug, 0.5 + 0.05 * arruga + 0.05 * borde, 1 - falta


def dorado_envejecido(forma, cx, cy):
    """Dorado envejecido: oro gastado en los relieves que deja ver el bol rojo y suciedad en los huecos."""
    relieve = ruido_cm(forma, cx, cy, 2.0, 42101, octavas=5)
    gastado = suave(relieve, 0.55, 0.62) * suave(ruido_cm(forma, cx, cy, 5.0, 42102, octavas=3), 0.45, 0.6)
    sucio = 1 - suave(relieve, 0.3, 0.5)
    lum = 0.72 - 0.4 * sucio
    color = gris(lum) * (1 - gastado[..., None]) + np.array([0.6, 0.22, 0.15]) * gastado[..., None]
    return color, 0.35 + 0.3 * gastado + 0.2 * sucio, 0.3 + 0.4 * relieve, (1 - gastado) * (1 - 0.6 * sucio)


def papel_damasco(forma, cx, cy):
    """Papel pintado de damasco: adorno simétrico mate sobre fondo satinado del mismo tono, algo más oscuro."""
    orn = _ornamento(forma, cx, cy, 26.0, 36.0, 42201)
    fibra = ruido_cm(forma, cx, cy, 0.05, 42202, octavas=2) - 0.5
    lum = 0.42 + 0.3 * orn + 0.02 * fibra
    return gris(lum), 0.35 + 0.3 * orn, 0.5 + 0.03 * orn


def papel_rayas(forma, cx, cy):
    """Papel pintado de rayas: rayas verticales anchas y finas, en dos tonos con filete."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = _cuenta(tw, 12.0)
    f = (x % p) / p
    ancha = f < 0.5
    filete = np.abs(f - 0.75) < 0.02
    fibra = ruido_cm(forma, cx, cy, 0.05, 42301, octavas=2) - 0.5
    lum = np.where(ancha, 0.62, 0.48) - 0.25 * filete + 0.02 * fibra
    color = gris(lum) * np.where(ancha[..., None], np.array([1.0, 1.0, 0.95]), np.array([0.9, 1.05, 1.0]))
    return color, np.full(forma, 0.6), np.full(forma, 0.5)


def papel_flores(forma, cx, cy):
    """Papel pintado de florecillas: ramitos pequeños repetidos a medio salto sobre fondo claro."""
    u, v = _celda(forma, cx, cy, 8.0, 8.0)
    r = np.hypot(u, v) * 8.0
    ang = np.arctan2(v, u)
    petalo = r < (0.9 + 0.6 * np.abs(np.cos(2.5 * ang)))
    centro = r < 0.45
    hoja = (np.abs(v * 8.0 - 2.2 + 0.4 * np.abs(u * 8.0)) < 0.35) & (np.abs(u * 8.0) < 1.6) & ~petalo
    color = gris(np.full(forma, 0.78), (1.02, 1.0, 0.94))
    color = np.where(petalo[..., None], np.array([0.85, 0.45, 0.5]), color)
    color = np.where(centro[..., None], np.array([0.95, 0.8, 0.35]), color)
    color = np.where(hoja[..., None], np.array([0.45, 0.62, 0.4]), color)
    return color, np.full(forma, 0.6), np.full(forma, 0.5)


def capitone(forma, cx, cy):
    """Capitoné: cuero acolchado en rombos con botones hundidos y pliegues entre botones."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px, py = _cuenta(tw, 12.0), _cuenta(th, 16.0)
    a = (x / px + y / py) % 1.0 - 0.5
    b = (x / px - y / py) % 1.0 - 0.5
    cojin = np.cos(math.pi * a) * np.cos(math.pi * b)
    ua, vb = (x / px) % 1.0, (y / py) % 1.0
    d1 = np.hypot((ua - 0.5) * px, (vb - 0.5) * py)
    d2 = np.hypot(np.minimum(ua, 1 - ua) * px, np.minimum(vb, 1 - vb) * py)
    boton = np.minimum(d1, d2)
    hundido = 1 - suave(boton, 0.6, 2.5)
    pliegue = suave(0.03 - np.abs(a), 0, 0.02) + suave(0.03 - np.abs(b), 0, 0.02)
    grano = ruido_cm(forma, cx, cy, 0.05, 42601, octavas=2) - 0.5
    alt = 0.2 + 0.7 * cojin - 0.4 * hundido
    lum = 0.42 + 0.25 * cojin - 0.2 * hundido - 0.1 * pliegue + 0.02 * grano
    lum = np.where(boton < 0.6, 0.55, lum)
    return gris(lum), 0.4 + 0.1 * hundido, np.clip(alt, 0, 1)


def laca_urushi(forma, cx, cy):
    """Laca urushi: rojo profundo muy pulido, gastado en zonas que dejan ver la capa negra de debajo."""
    gastado = manchas_fractales(forma, cx, cy, 6.0, 42701, 0.15, detalle=0.5)
    borde = manchas_fractales(forma, cx, cy, 6.0, 42701, 0.2, detalle=0.5) * (1 - gastado)
    lum = 0.55 - 0.45 * gastado - 0.12 * borde
    color = gris(lum) * (np.array([1.5, 0.35, 0.3]) * (1 - gastado[..., None]) + np.array([1.0, 1.0, 1.0]) *
                         gastado[..., None])
    return color, 0.15 + 0.05 * gastado, np.full(forma, 0.5)


def taracea(forma, cx, cy):
    """Taracea: estrellas y rombos de maderas de tres tonos y hueso, encajadas en una red."""
    u, v = _celda(forma, cx, cy, 6.0, 6.0, medio_salto=False)
    au, av = np.abs(u), np.abs(v)
    estrella = (au + av < 0.32) | ((au < 0.08) & (av < 0.45)) | ((av < 0.08) & (au < 0.45))
    rombo = (np.abs(au - 0.5) + np.abs(av - 0.5) < 0.2)
    hueso = (np.abs(au + av - 0.32) < 0.025)
    veta = estirado(forma, cx, cy, 0.3, 42801, 6.0, octavas=2) - 0.5
    color = np.where(estrella[..., None], np.array([0.75, 0.55, 0.32]), np.array([0.42, 0.26, 0.16]))
    color = np.where(rombo[..., None], np.array([0.2, 0.12, 0.08]), color)
    color = np.where(hueso[..., None], np.array([0.92, 0.88, 0.78]), color)
    color = color * (1 + 0.15 * veta[..., None])
    return color, np.full(forma, 0.35), 0.5 + 0.01 * veta


def pintura_patinada(forma, cx, cy):
    """Pintura patinada (decapé): pintura clara lijada en los cantos que deja ver la madera y otra capa."""
    veta = estirado(forma, cx, cy, 1.0, 42901, 10.0, octavas=4)
    lijado = suave(ruido_cm(forma, cx, cy, 4.0, 42902, octavas=4) + 0.3 * (veta - 0.5), 0.62, 0.7)
    capa = suave(ruido_cm(forma, cx, cy, 4.0, 42903, octavas=4), 0.55, 0.6) * (1 - lijado)
    pincel = estirado(forma, cx, cy, 0.2, 42904, 12.0) - 0.5
    lum = 0.78 + 0.03 * pincel
    color = gris(lum, (1.0, 1.0, 0.95))
    color = color * (1 - capa[..., None]) + np.array([0.5, 0.62, 0.65]) * capa[..., None]
    madera = gris(0.45 + 0.1 * (veta - 0.5)) * np.array([1.25, 0.95, 0.65])
    color = color * (1 - lijado[..., None]) + madera * lijado[..., None]
    return color, 0.65 + 0.1 * lijado, 0.5 + 0.03 * pincel - 0.05 * lijado + 0.03 * (veta - 0.5)


def terciopelo_aplastado(forma, cx, cy):
    """Terciopelo aplastado: el pelo tumbado en vetas irregulares cambia de tono con la luz."""
    vetas = ruido_cm(forma, cx, cy, 3.0, 43001, octavas=5)
    brillo = suave(1 - np.abs(2 * vetas - 1), 0.6, 0.95)
    pelo = ruido_cm(forma, cx, cy, 0.02, 43002, octavas=2) - 0.5
    lum = 0.38 + 0.35 * brillo + 0.04 * pelo
    return gris(lum), 0.7 - 0.25 * brillo, 0.5 + 0.03 * pelo


def seda_moare(forma, cx, cy):
    """Seda moaré: aguas onduladas que brillan sobre un tafetán fino."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    giro = (ruido_cm(forma, cx, cy, 6.0, 43101, octavas=4) - 0.5) * 30
    agua = 0.5 + 0.5 * np.sin(2 * math.pi * round(th / 0.8) * y / th + giro)
    alt, urd, fib = tejido(forma, cx, cy, 0.04, TAFETAN, 43102, hueco=0.05, fibra=0.3)
    lum = 0.45 + 0.2 * agua + 0.05 * (alt - 0.5)
    return gris(lum), 0.4 - 0.15 * agua, 0.5 + 0.05 * (alt - 0.5)


def brocado(forma, cx, cy):
    """Brocado: adorno tejido con hilo dorado brillante sobre seda de color mate."""
    orn = _ornamento(forma, cx, cy, 14.0, 20.0, 43201, finura=1.4)
    alt, urd, fib = tejido(forma, cx, cy, 0.05, TAFETAN, 43202, hueco=0.05, fibra=0.4)
    hilo = estirado(forma, cx, cy, 0.03, 43203, 5.0) - 0.5
    fondo = gris(np.full(forma, 0.42)) * np.array([1.35, 0.55, 0.55])
    oro = gris(0.72 + 0.1 * hilo) * np.array([1.2, 1.0, 0.55])
    color = fondo * (1 - orn[..., None]) + oro * orn[..., None]
    return color, 0.6 - 0.3 * orn, 0.45 + 0.1 * orn + 0.03 * (alt - 0.5), 0.9 * orn


def encaje(forma, cx, cy):
    """Encaje: malla fina de hilo con motivos tupidos y calados; los huecos dejan ver negro."""
    orn = _ornamento(forma, cx, cy, 6.0, 8.0, 43301, finura=1.6)
    x, y = rejilla(forma, cx, cy)
    p = 0.25
    a = np.abs(((x + y) % p) - p / 2) < 0.02
    b = np.abs(((x - y) % p) - p / 2) < 0.02
    red = (a | b).astype(float)
    hilo = np.clip(orn + red, 0, 1)
    lum = np.where(hilo > 0.5, 0.82, 0.08)
    return gris(lum, (1.0, 0.99, 0.95)), 0.75, 0.2 + 0.6 * hilo


def esgrafiado(forma, cx, cy):
    """Esgrafiado: revoco de dos capas; el adorno raspado deja ver la capa de abajo, más oscura."""
    orn = _ornamento(forma, cx, cy, 40.0, 40.0, 43401, medio_salto=False)
    arena = ruido_cm(forma, cx, cy, 0.04, 43402, octavas=2) - 0.5
    lum = np.where(orn > 0.5, 0.42, 0.66) + 0.04 * arena
    color = gris(lum) * np.where(orn[..., None] > 0.5, np.array([1.1, 0.95, 0.85]), np.array([1.0, 0.99, 0.95]))
    return color, np.full(forma, 0.85), 0.55 - 0.12 * orn + 0.04 * arena


def cuero_repujado(forma, cx, cy):
    """Cuero repujado: adorno en relieve con el fondo punteado y más oscuro."""
    orn = _ornamento(forma, cx, cy, 10.0, 14.0, 43501, finura=1.2)
    punteado = salpicado(forma, cx, cy, 0.04, 43502, 0.3, borde=0.02) * (1 - orn)
    grano = ruido_cm(forma, cx, cy, 0.05, 43503, octavas=2) - 0.5
    lum = 0.32 + 0.3 * orn - 0.06 * punteado + 0.03 * grano
    color = gris(lum) * np.array([1.3, 0.95, 0.65])
    return color, 0.55 - 0.1 * orn, 0.35 + 0.35 * orn - 0.05 * punteado + 0.02 * grano


def papel_washi(forma, cx, cy):
    """Papel washi: fibras largas y visibles en una hoja translúcida con nubes de pasta."""
    from superficie import rayas
    fibra = rayas(forma, cx, cy, forma[1] * cx * forma[0] * cy * 1.5, 3.0, 0.035, 43601, curva=0.4)
    nube = ruido_cm(forma, cx, cy, 2.0, 43602, octavas=4) - 0.5
    lum = 0.7 + 0.12 * nube + 0.12 * fibra
    return gris(lum, (1.02, 1.0, 0.94)), np.full(forma, 0.75), 0.5 + 0.05 * fibra + 0.03 * nube


def punto_cruz(forma, cx, cy):
    """Punto de cruz: cruces de hilo de colores sobre tela de Aída cuadriculada, con un dibujo pixelado."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = _cuenta(tw, 0.18)
    i, j = np.floor(x / p), np.floor(y / p)
    u, v = (x % p) / p - 0.5, (y % p) / p - 0.5
    cruz = (np.abs(u - v) < 0.14) | (np.abs(u + v) < 0.14)
    bloque = 12
    bi, bj = np.floor(i / bloque), np.floor(j / bloque)
    du, dv = (i % bloque) - bloque / 2 + 0.5, (j % bloque) - bloque / 2 + 0.5
    rombo = (np.abs(du) + np.abs(dv)) < 4
    dibujo = rombo | ((bi + bj) % 2 == 0) & (np.abs(du) < 1) & (np.abs(dv) < 5)
    hilo = cruz & dibujo
    aida = 0.7 + 0.05 * ((np.abs(u) > 0.4) | (np.abs(v) > 0.4))
    color = gris(aida, (1.02, 1.0, 0.94))
    tono = np.where(((bi + bj) % 2 == 0)[..., None], np.array([0.75, 0.15, 0.2]), np.array([0.15, 0.3, 0.6]))
    color = np.where(hilo[..., None], tono, color)
    return color, np.full(forma, 0.7), 0.45 + 0.15 * hilo


def rejilla_viena(forma, cx, cy):
    """Rejilla de Viena: tejido de caña en octógonos, con huecos y tiras planas brillantes."""
    x, y = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = _cuenta(tw, 1.4)
    u, v = (x % p) / p - 0.5, (y % p) / p - 0.5
    h = (np.abs(u) < 0.06) | (np.abs(v) < 0.06)
    d1 = np.abs(((x + y) / p) % 1.0 - 0.5) < 0.05
    d2 = np.abs(((x - y) / p) % 1.0 - 0.5) < 0.05
    tira = h | d1 | d2
    fibra = estirado(forma, cx, cy, 0.02, 43801, 6.0) - 0.5
    lum = np.where(tira, 0.65 + 0.05 * fibra, 0.2)
    color = gris(lum) * np.where(tira[..., None], np.array([1.2, 1.05, 0.7]), 1.0)
    return color, np.where(tira, 0.4, 0.9), np.where(tira, 0.6 + 0.1 * (d1 | d2), 0.0)


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.5, metal=0.0, familia="Decorativo", **kw):
    def f(forma, cx, cy):
        r = funcion(forma, cx, cy, **kw)
        color = np.clip(r[0] * (0.5 / max(1e-6, float(r[0].mean()))), 0.0, 1.0)
        rug_ = np.clip(np.broadcast_to(np.asarray(r[1], dtype=np.float64), forma), 0.0, 1.0)
        rug_ = np.clip(rug_ + (0.5 - float(rug_.mean())), 0.0, 1.0)
        return (color, rug_) + tuple(r[2:])

    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=metal, recomendado_para=para)


ACABADOS = [
    _a("pan_de_oro", pan_de_oro, "Pan de oro", (32.0, 32.0), 0.01, "#e8b850", ["pan de oro", "dorado", "retablo"],
       rug=0.25, metal=1.0),
    _a("pan_de_plata", pan_de_oro, "Pan de plata", (32.0, 32.0), 0.01, "#d8d8dc", ["pan de plata", "plateado"],
       rug=0.25, metal=1.0, plata=True),
    _a("dorado_envejecido", dorado_envejecido, "Dorado envejecido", (20.0, 20.0), 0.2, "#c8a050", ["dorado",
       "marco antiguo", "barroco"], rug=0.35, metal=1.0),
    _a("papel_damasco", papel_damasco, "Papel pintado de damasco", (52.0, 72.0), 0.01, "#8a7a9a", ["damasco",
       "papel pintado", "clasico"]),
    _a("papel_rayas", papel_rayas, "Papel pintado de rayas", (48.0, 48.0), 0.0, "#c8c0a8", ["rayas",
       "papel pintado"], rug=0.7),
    _a("papel_flores", papel_flores, "Papel pintado de florecillas", (32.0, 32.0), 0.0, "#c8c0b0", ["flores",
       "papel pintado", "vintage"], rug=0.7),
    _a("capitone", capitone, "Capitoné", (48.0, 48.0), 3.0, "#5a3a2a", ["capitone", "chester", "sofa"], rug=0.45),
    _a("laca_urushi", laca_urushi, "Laca urushi", (30.0, 30.0), 0.0, "#8a2018", ["urushi", "laca", "japones"],
       rug=0.1),
    _a("taracea", taracea, "Taracea", (24.0, 24.0), 0.01, "#9a7050", ["taracea", "marqueteria", "incrustacion"],
       rug=0.3),
    _a("pintura_patinada", pintura_patinada, "Pintura patinada (decapé)", (40.0, 40.0), 0.05, "#d8d4c8",
       ["decape", "patinado", "vintage"], rug=0.65),
    _a("terciopelo_aplastado", terciopelo_aplastado, "Terciopelo aplastado", (20.0, 20.0), 0.02, "#6a2a5a",
       ["terciopelo", "aplastado"], rug=0.7),
    _a("seda_moare", seda_moare, "Seda moaré", (16.0, 16.0), 0.005, "#8a9ab0", ["moare", "seda", "tafetan"],
       rug=0.35),
    _a("brocado", brocado, "Brocado", (28.0, 40.0), 0.03, "#9a9a9a", ["brocado", "tapiceria", "lujo"], rug=0.5),
    _a("encaje", encaje, "Encaje", (12.0, 16.0), 0.05, "#e8e4d8", ["encaje", "puntilla", "visillo"], rug=0.8),
    _a("esgrafiado", esgrafiado, "Esgrafiado", (80.0, 80.0), 0.2, "#c8b898", ["esgrafiado", "segovia",
       "fachada"], rug=0.9),
    _a("cuero_repujado", cuero_repujado, "Cuero repujado", (20.0, 28.0), 0.2, "#8a5a3a", ["repujado", "cuero",
       "silla de montar"]),
    _a("papel_washi", papel_washi, "Papel washi", (15.0, 15.0), 0.02, "#e8e2d0", ["washi", "papel japones",
       "farol"], rug=0.8),
    _a("punto_cruz", punto_cruz, "Punto de cruz", (8.64, 8.64), 0.03, "#c8c4b8", ["punto de cruz", "bordado"],
       rug=0.8),
    _a("rejilla_viena", rejilla_viena, "Rejilla de Viena", (14.0, 14.0), 0.1, "#c8a870", ["rejilla", "viena",
       "silla thonet", "rattan"], rug=0.5),
]
