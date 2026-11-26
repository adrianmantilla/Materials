"""Patrones de piezas que no son filas de rectángulos (espiga, hexágono, piedra irregular...).

Datos puros con numpy, sin Designer. Cada patrón es una función ``id(x, y)`` continua en cm que
dice a qué pieza pertenece cada punto y que repite exactamente con la medida de la imagen
(``tile_cm``). La junta sale de los cambios de pieza: así el ancho de junta es real (cm) y el
patrón no tiene costuras.

``forma(d, res)`` devuelve la máscara de piezas (True en la pieza) para la fábrica.
"""

import math

import numpy as np

CUBRE_MIN = 0.999  # fracción de la imagen que debe quedar asignada a alguna pieza


def _codigo(k, c0, c1):
    """Número de pieza, siempre positivo (los negativos significan «sin pieza»)."""
    return (np.asarray(k, dtype=np.int64) * 4_000_000_000_000 + (np.asarray(c0, dtype=np.int64) + 1_000_000) * 2_000_000
            + (np.asarray(c1, dtype=np.int64) + 1_000_000))


def _girar(x, y, angulo):
    c, s = math.cos(-math.radians(angulo)), math.sin(-math.radians(angulo))
    return c * x - s * y, s * x + c * y


def red_rectangulos(x, y, a1, a2, rects, angulo=0.0):
    """Teselación periódica por rectángulos: red (a1, a2) y rectángulos base (x, y, ancho, alto)."""
    u, v = _girar(x, y, angulo)
    det = a1[0] * a2[1] - a2[0] * a1[1]

    def coords(px, py):
        return (a2[1] * px - a2[0] * py) / det, (-a1[1] * px + a1[0] * py) / det

    # Cada rectángulo se lleva a la celda base (por su centro) y se mira cuántas celdas abarca.
    base, alcance = [], 1
    for rx, ry, rw, rh in rects:
        fs, ft = (math.floor(c) for c in coords(rx + rw / 2, ry + rh / 2))
        rx, ry = rx - fs * a1[0] - ft * a2[0], ry - fs * a1[1] - ft * a2[1]
        base.append((rx, ry, rw, rh))
        for qx, qy in ((rx, ry), (rx + rw, ry), (rx, ry + rh), (rx + rw, ry + rh)):
            alcance = max(alcance, *(int(math.ceil(abs(c))) + 1 for c in coords(qx, qy)))
    rects = base
    s = (a2[1] * u - a2[0] * v) / det
    t = (-a1[1] * u + a1[0] * v) / det
    c0, c1 = np.floor(s).astype(np.int64), np.floor(t).astype(np.int64)
    ids = np.full(u.shape, -1, dtype=np.int64)
    for i in range(-alcance, alcance + 1):
        for j in range(-alcance, alcance + 1):
            ox = (c0 + i) * a1[0] + (c1 + j) * a2[0]
            oy = (c0 + i) * a1[1] + (c1 + j) * a2[1]
            for k, (rx, ry, rw, rh) in enumerate(rects):
                qx, qy = u - ox - rx, v - oy - ry
                dentro = (qx >= 0) & (qx < rw) & (qy >= 0) & (qy < rh) & (ids < 0)
                if dentro.any():
                    ids[dentro] = _codigo(k, c0 + i, c1 + j)[dentro]
    return ids


def red_voronoi(x, y, a1, a2, alcance=2):
    """Celdas de Voronoi de una red regular (con a1 y a2 de igual largo a 60°: hexágonos)."""
    det = a1[0] * a2[1] - a2[0] * a1[1]
    s = (a2[1] * x - a2[0] * y) / det
    t = (-a1[1] * x + a1[0] * y) / det
    c0, c1 = np.floor(s).astype(np.int64), np.floor(t).astype(np.int64)
    mejor = np.full(x.shape, np.inf)
    ids = np.zeros(x.shape, dtype=np.int64)
    for i in range(-alcance + 1, alcance + 1):
        for j in range(-alcance + 1, alcance + 1):
            px = (c0 + i) * a1[0] + (c1 + j) * a2[0]
            py = (c0 + i) * a1[1] + (c1 + j) * a2[1]
            d = (x - px) ** 2 + (y - py) ** 2
            cerca = d < mejor
            mejor = np.where(cerca, d, mejor)
            ids = np.where(cerca, _codigo(0, c0 + i, c1 + j), ids)
    return ids


def voronoi_azar(x, y, tile, celdas, semilla, temblor=0.85, pesos=0.0, estirar=1.0):
    """Piedras: Voronoi de puntos al azar (uno por celda de una rejilla) que repite con el tile.

    ``pesos`` (0-1) da tamaños distintos (diagrama de potencias); ``estirar`` > 1 alarga en X.
    """
    nx, ny = celdas
    cw, ch = tile[0] / nx, tile[1] / ny
    rng = np.random.default_rng(semilla)
    jit = rng.uniform(-temblor / 2, temblor / 2, (ny, nx, 2))
    peso = rng.uniform(0, 1, (ny, nx)) * pesos * (min(cw, ch) ** 2) * 0.5
    gx, gy = np.floor(x / cw).astype(np.int64), np.floor(y / ch).astype(np.int64)
    mejor = np.full(x.shape, np.inf)
    ids = np.zeros(x.shape, dtype=np.int64)
    for i in range(-2, 3):
        for j in range(-2, 3):
            cx, cy = gx + i, gy + j
            mx, my = cx % nx, cy % ny
            px = (cx + 0.5 + jit[my, mx, 0]) * cw
            py = (cy + 0.5 + jit[my, mx, 1]) * ch
            d = ((x - px) / estirar) ** 2 + (y - py) ** 2 - peso[my, mx]
            cerca = d < mejor
            mejor = np.where(cerca, d, mejor)
            ids = np.where(cerca, my * nx + mx, ids)
    return ids


def abanico(x, y, paso, adoquin):
    """Adoquín en abanico (arcos que se solapan como escamas), cada arco partido en adoquines."""
    radio = 0.72 * paso
    fila = np.floor(y / (paso / 2)).astype(np.int64)
    ids = np.full(x.shape, -1, dtype=np.int64)
    # Delante va la fila de abajo (y mayor): se recorre de arriba abajo y se sobrescribe.
    for df in range(-2, 4):
        j = fila + df
        desfase = (j % 2) * paso / 2
        col = np.floor((x - desfase) / paso + 0.5).astype(np.int64)
        for dc in (-1, 0, 1):
            i = col + dc
            cx = i * paso + desfase
            cy = (j - 1) * (paso / 2)
            dx, dy = x - cx, y - cy
            r = np.hypot(dx, dy)
            dentro = r < radio
            anillo = np.floor((radio - r) / adoquin).astype(np.int64)
            rm = radio - (anillo + 0.5) * adoquin
            ang = np.arctan2(dx, dy)
            n = np.maximum(1, np.round(np.pi * rm / adoquin)).astype(np.int64)
            giro = (anillo * 0.618 + (i * 7 + j * 3) * 0.37) % 1.0  # juntas radiales sin alinear
            tramo = np.floor((ang / np.pi + 0.5) * n + giro).astype(np.int64)
            codigo = _codigo(np.clip(anillo, 0, 999) * 1000 + (tramo + 500) % 1000, i, j)
            ids = np.where(dentro, codigo, ids)
    return ids


def sillar_irregular(x, y, tile, semilla, alturas, anchos):
    """Sillería a hiladas de alto variable y piezas de ancho variable (random ashlar)."""
    rng = np.random.default_rng(semilla)
    rects = []
    yy = 0.0
    while yy < tile[1] - 1e-6:
        h = float(rng.choice(alturas))
        h = min(h, tile[1] - yy) if tile[1] - yy - h < min(alturas) - 1e-6 else h
        if tile[1] - yy - h < min(alturas) - 1e-6:
            h = tile[1] - yy
        xx = rng.uniform(0, tile[0])
        total = 0.0
        while total < tile[0] - 1e-6:
            w = rng.uniform(*anchos)
            if tile[0] - total - w < anchos[0]:
                w = tile[0] - total
            rects.append((xx + total, yy, w, h))
            total += w
        yy += h
    return red_rectangulos(x, y, (tile[0], 0.0), (0.0, tile[1]), rects)


def ids_de(d, x, y):
    p = d["patron"]
    tipo = p["tipo"]
    if tipo == "espiga":
        largo, ancho = p["largo"], p["ancho"]
        rects = [(0.0, 0.0, largo, ancho), (0.0, ancho, ancho, largo)]
        return red_rectangulos(x, y, (ancho, ancho), (largo, -largo), rects, angulo=p.get("angulo", 0.0))
    if tipo == "rectangulos":
        return red_rectangulos(x, y, tuple(p["a1"]), tuple(p["a2"]), [tuple(r) for r in p["rects"]],
                               angulo=p.get("angulo", 0.0))
    if tipo == "hexagono":
        r = p["radio"]
        return red_voronoi(x, y, (math.sqrt(3) * r, 0.0), (math.sqrt(3) * r / 2, 1.5 * r))
    if tipo == "voronoi":
        return voronoi_azar(x, y, d["tile_cm"], p["celdas"], p.get("semilla", 1), p.get("temblor", 0.85),
                            p.get("pesos", 0.0), p.get("estirar", 1.0))
    if tipo == "abanico":
        return abanico(x, y, p["paso"], p["adoquin"])
    if tipo == "sillar_irregular":
        return sillar_irregular(x, y, d["tile_cm"], p.get("semilla", 1), p["alturas"], p["anchos"])
    raise ValueError("patrón desconocido: " + tipo)


def forma(d, res, distancia):
    """Máscara de piezas (True) con juntas de ``junta_cm``. ``distancia``: la de fabricar.py."""
    alto = ancho = int(res)
    tw, th = d["tile_cm"]
    px, py = tw / ancho, th / alto
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    x, y = (xx + 0.5) * px, (yy + 0.5) * py
    ids = ids_de(d, x, y)
    cubierto = float((ids >= 0).mean())
    if cubierto < CUBRE_MIN:
        raise ValueError("{}: el patrón deja sin pieza el {:.2%} de la imagen".format(d["id"], 1 - cubierto))
    borde = (ids != ids_de(d, x + px, y)) | (ids != ids_de(d, x, y + py))
    junta = d["junta_cm"]
    dist = distancia(~borde, px, py, max(junta, 2.0 * max(px, py)))
    # Una junta de menos de dos píxeles se rompería en diagonal y pegaría piezas.
    mascara = dist >= max(junta / 2.0, 0.75 * max(px, py))
    redondeo = d["patron"].get("redondeo", 0.0)
    if redondeo > 0:
        # Esquinas redondeadas (cantos rodados, mampuestos): desenfocar y volver a umbralizar.
        # Solo quita (esquinas salientes); nunca cierra una junta estrecha.
        mascara = mascara & (desenfocar(mascara.astype(np.float64), px, py, redondeo) > 0.5)
    return mascara


def desenfocar(a, px, py, sigma_cm):
    """Desenfoque gaussiano que repite (FFT) con ``sigma_cm`` medido en cm en cada eje."""
    fy = np.fft.fftfreq(a.shape[0], d=py)[:, None]
    fx = np.fft.fftfreq(a.shape[1], d=px)[None, :]
    filtro = np.exp(-2.0 * (np.pi * sigma_cm) ** 2 * (fx ** 2 + fy ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * filtro))

