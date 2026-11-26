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


def guijarros(x, y, tile, celdas, semilla, tam=0.9):
    """Cantos rodados: una elipse al azar (tamaño, forma y giro) por celda; fuera de ellas, mortero (-1)."""
    nx, ny = celdas
    cw, ch = tile[0] / nx, tile[1] / ny
    rng = np.random.default_rng(semilla)
    jit = rng.uniform(-0.12, 0.12, (ny, nx, 2))
    eje_a = 0.5 * min(cw, ch) * tam * rng.uniform(0.85, 1.15, (ny, nx))
    eje_b = eje_a * rng.uniform(0.55, 0.9, (ny, nx))
    giro = rng.uniform(0, np.pi, (ny, nx))
    gx, gy = np.floor(x / cw).astype(np.int64), np.floor(y / ch).astype(np.int64)
    ids = np.full(x.shape, -1, dtype=np.int64)
    for i in range(-1, 2):
        for j in range(-1, 2):
            cx, cy = gx + i, gy + j
            mx, my = cx % nx, cy % ny
            dx = x - (cx + 0.5 + jit[my, mx, 0]) * cw
            dy = y - (cy + 0.5 + jit[my, mx, 1]) * ch
            c, s_ = np.cos(giro[my, mx]), np.sin(giro[my, mx])
            u, v = (c * dx + s_ * dy) / eje_a[my, mx], (-s_ * dx + c * dy) / eje_b[my, mx]
            dentro = (u * u + v * v < 1.0) & (ids < 0)
            ids = np.where(dentro, my * nx + mx, ids)
    return ids


def abanico(x, y, paso, adoquin, unica=False):
    """Adoquín en abanico (arcos que se solapan como escamas), cada arco partido en adoquines.

    Con ``unica`` cada arco es una sola pieza: tejas de escama.
    """
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
            if unica:
                anillo, tramo = np.zeros_like(anillo), np.zeros_like(tramo)
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


def octogono(x, y, lado, corte):
    """Octógonos con taco: baldosa de ``lado`` con las esquinas cortadas; en cada vértice de la red,
    un taco cuadrado girado 45° (semidiagonal ``corte``)."""
    i, j = np.floor(x / lado).astype(np.int64), np.floor(y / lado).astype(np.int64)
    u, v = x - i * lado, y - j * lado
    du, dv = np.minimum(u, lado - u), np.minimum(v, lado - v)
    taco = du + dv < corte
    vi = i + (u > lado / 2)
    vj = j + (v > lado / 2)
    return np.where(taco, _codigo(1, vi, vj), _codigo(0, i, j))


def punta_hungria(x, y, largo, ancho, angulo=45.0):
    """Parquet en punta de Hungría (chevron): columnas de tablillas inclinadas que se cortan en V."""
    a = math.radians(angulo)
    media = largo * math.cos(a)          # ancho horizontal de media columna
    alto = ancho / math.cos(a)           # alto vertical de una tablilla cortada en vertical
    col = np.floor(x / (2 * media)).astype(np.int64)
    s = x - col * 2 * media
    derecha = s >= media
    sube = np.where(derecha, 2 * media - s, s) * math.tan(a)
    fila = np.floor((y + sube) / alto).astype(np.int64)
    return _codigo(derecha.astype(np.int64), col, fila)


def paralelogramos(x, y, a1, a2):
    """Celdas de la red (a1, a2) tal cual: rombos, romboides."""
    det = a1[0] * a2[1] - a2[0] * a1[1]
    s = (a2[1] * x - a2[0] * y) / det
    t = (-a1[1] * x + a1[0] * y) / det
    return _codigo(0, np.floor(s).astype(np.int64), np.floor(t).astype(np.int64))


def triangulos(x, y, a1, a2):
    """Cada celda de la red (a1, a2) partida en dos triángulos por su diagonal (con a1 y a2 a 60°: equiláteros)."""
    det = a1[0] * a2[1] - a2[0] * a1[1]
    s = (a2[1] * x - a2[0] * y) / det
    t = (-a1[1] * x + a1[0] * y) / det
    c0, c1 = np.floor(s), np.floor(t)
    k = ((s - c0) + (t - c1) >= 1.0).astype(np.int64)
    return _codigo(k, c0.astype(np.int64), c1.astype(np.int64))


def estrella_cruz(x, y, lado, punta=0.48):
    """Estrella de ocho puntas en cada cuadrado de ``lado`` y cruces entre ellas (azulejo de estrella y cruz)."""
    i, j = np.floor(x / lado), np.floor(y / lado)
    u, v = x / lado - i - 0.5, y / lado - j - 0.5
    au, av = np.abs(u), np.abs(v)
    estrella = (au + av < punta) | (np.maximum(au, av) < punta / math.sqrt(2))
    ci, cj = i + (u > 0), j + (v > 0)  # la cruz se centra en la esquina más cercana
    return np.where(estrella, _codigo(0, i.astype(np.int64), j.astype(np.int64)),
                    _codigo(1, ci.astype(np.int64), cj.astype(np.int64)))


def ondas(x, y, ancho, alto, amplitud, periodo):
    """Piezas de ``ancho × alto`` en filas cuyos bordes horizontales ondulan (seno de ``periodo``)."""
    yy = y + amplitud * np.sin(2 * math.pi * x / periodo)
    fila = np.floor(yy / alto)
    col = np.floor((x + 0.5 * ancho * (fila % 2)) / ancho)
    return _codigo(0, col.astype(np.int64), fila.astype(np.int64))


def _centro_hex(x, y, radio):
    """Centro del hexágono (vértice arriba, lado ``radio``) que contiene cada punto."""
    a1, a2 = (math.sqrt(3) * radio, 0.0), (math.sqrt(3) * radio / 2, 1.5 * radio)
    det = a1[0] * a2[1] - a2[0] * a1[1]
    s = (a2[1] * x - a2[0] * y) / det
    t = (-a1[1] * x + a1[0] * y) / det
    c0, c1 = np.floor(s).astype(np.int64), np.floor(t).astype(np.int64)
    mejor = np.full(x.shape, np.inf)
    i0, j0 = np.zeros_like(c0), np.zeros_like(c1)
    for i in range(-1, 3):
        for j in range(-1, 3):
            px = (c0 + i) * a1[0] + (c1 + j) * a2[0]
            py = (c0 + i) * a1[1] + (c1 + j) * a2[1]
            d = (x - px) ** 2 + (y - py) ** 2
            cerca = d < mejor
            mejor = np.where(cerca, d, mejor)
            i0, j0 = np.where(cerca, c0 + i, i0), np.where(cerca, c1 + j, j0)
    px = i0 * a1[0] + j0 * a2[0]
    py = i0 * a1[1] + j0 * a2[1]
    return i0, j0, px, py


def sector_cubo(x, y, radio):
    """0, 1 o 2: cuál de los tres rombos del hexágono (las tres caras del cubo)."""
    _, _, px, py = _centro_hex(x, y, radio)
    ang = np.degrees(np.arctan2(y - py, x - px))
    return (np.floor(((ang - 30.0) % 360.0) / 120.0)).astype(np.int64) % 3


def circulos(x, y, radio, circulo):
    """Círculos de radio ``circulo`` centrados en una red hexagonal (mosaico penny); fuera, junta."""
    i0, j0, px, py = _centro_hex(x, y, radio)
    dentro = (x - px) ** 2 + (y - py) ** 2 < circulo ** 2
    return np.where(dentro, _codigo(0, i0, j0), -1)


def cubos(x, y, radio):
    """Cubos en perspectiva (tumbling blocks): cada hexágono partido en tres rombos."""
    i0, j0, px, py = _centro_hex(x, y, radio)
    ang = np.degrees(np.arctan2(y - py, x - px))
    sector = (np.floor(((ang - 30.0) % 360.0) / 120.0)).astype(np.int64) % 3
    return _codigo(sector, i0, j0)


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
    if tipo == "guijarros":
        return guijarros(x, y, d["tile_cm"], p["celdas"], p.get("semilla", 1), p.get("tam", 0.9))
    if tipo == "abanico":
        return abanico(x, y, p["paso"], p["adoquin"], p.get("unica", False))
    if tipo == "sillar_irregular":
        return sillar_irregular(x, y, d["tile_cm"], p.get("semilla", 1), p["alturas"], p["anchos"])
    if tipo == "octogono":
        return octogono(x, y, p["lado"], p["corte"])
    if tipo == "red_voronoi":
        return red_voronoi(x, y, tuple(p["a1"]), tuple(p["a2"]), alcance=p.get("alcance", 3))
    if tipo == "paralelogramos":
        return paralelogramos(x, y, tuple(p["a1"]), tuple(p["a2"]))
    if tipo == "cubos":
        return cubos(x, y, p["radio"])
    if tipo == "triangulos":
        return triangulos(x, y, tuple(p["a1"]), tuple(p["a2"]))
    if tipo == "estrella_cruz":
        return estrella_cruz(x, y, p["lado"], p.get("punta", 0.48))
    if tipo == "ondas":
        return ondas(x, y, p["ancho"], p["alto"], p["amplitud"], p["periodo"])
    if tipo == "circulos":
        return circulos(x, y, p["radio"], p["circulo"])
    if tipo == "punta_hungria":
        return punta_hungria(x, y, p["largo"], p["ancho"], p.get("angulo", 45.0))
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
    if cubierto < CUBRE_MIN and d["patron"]["tipo"] not in ("guijarros", "circulos") and not d["patron"].get("huecos"):
        raise ValueError("{}: el patrón deja sin pieza el {:.2%} de la imagen".format(d["id"], 1 - cubierto))
    borde = (ids != ids_de(d, x + px, y)) | (ids != ids_de(d, x, y + py))
    junta = d["junta_cm"]
    dist = distancia(~borde, px, py, max(junta, 3.0 * max(px, py)))
    # Una junta de menos de dos píxeles se rompería en diagonal y pegaría piezas.
    mascara = (dist >= max(junta / 2.0, 1.2 * max(px, py))) & (ids >= 0)
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

