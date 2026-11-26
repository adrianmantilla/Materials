"""Piezas para fabricar acabados en numpy (todo a tamaño real en cm y sin costuras).

Cada acabado devuelve ``color`` (RGB alrededor de 0,5 = neutro: Materials multiplica la receta
por 2 × color), ``rugosidad`` (alrededor de 0,5: se suma −0,5 a la de la receta) y ``altura``
(alrededor de 0,5). Aquí están los ladrillos con que se construyen: ruidos alargados, rayas,
celdas, hoyuelos, tejidos y mezclas de color.
"""

import math

import numpy as np

from fabricar import distancia_interior, ruido_cm, suave  # noqa: F401  (se reexportan)
import patrones


def rejilla(forma, cx, cy):
    """Coordenadas x, y en cm del centro de cada píxel."""
    alto, ancho = forma
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    return (xx + 0.5) * cx, (yy + 0.5) * cy


def gris(lum, tinte=(1.0, 1.0, 1.0)):
    return np.dstack([lum * tinte[0], lum * tinte[1], lum * tinte[2]])


def mezclar(base, color, peso):
    return base * (1.0 - peso[..., None]) + np.asarray(color)[None, None, :] * peso[..., None]


def estirado(forma, cx, cy, tam_cm, semilla, factor, eje="x", octavas=1):
    """Ruido alargado ``factor`` veces a lo largo de ``eje`` (cepillado, fibra, veta)."""
    if eje == "x":
        return ruido_cm(forma, cx / factor, cy, tam_cm, semilla, octavas=octavas)
    return ruido_cm(forma, cx, cy / factor, tam_cm, semilla, octavas=octavas)


def salpicado(forma, cx, cy, tam_cm, semilla, cobertura, borde=0.03):
    """Manchas sueltas de ``tam_cm`` que cubren más o menos ``cobertura`` (0-1)."""
    r = ruido_cm(forma, cx, cy, tam_cm, semilla)
    corte = np.quantile(r, 1.0 - cobertura)
    return suave(r, corte, corte + borde)


def manchas_fractales(forma, cx, cy, tam_cm, semilla, cobertura, detalle=0.35):
    """Manchas de borde irregular (óxido, desconchones, líquenes): ruido grande + detalle."""
    r = ruido_cm(forma, cx, cy, tam_cm, semilla, octavas=4)
    r = r + detalle * (ruido_cm(forma, cx, cy, tam_cm / 8.0, semilla + 1, octavas=2) - 0.5)
    corte = np.quantile(r, 1.0 - cobertura)
    return suave(r, corte, corte + 0.015)


def hoyuelos(forma, cx, cy, tam_cm, semilla, cobertura):
    """Poros o hoyuelos redondeados (0 fuera, 1 en el fondo)."""
    r = ruido_cm(forma, cx, cy, tam_cm, semilla)
    corte = np.quantile(r, 1.0 - cobertura)
    t = np.clip((r - corte) / max(1e-6, float(r.max() - corte)), 0.0, 1.0)
    return np.sqrt(t)


def rayas(forma, cx, cy, n, largo_cm, ancho_cm, semilla, angulo=None, dispersion=math.pi, curva=0.0):
    """Rayas finas (arañazos): ``n`` segmentos al azar; ``angulo`` (rad) fija la dirección media.

    Devuelve 0-1 (intensidad de raya). Repite: cada raya se dibuja con las coordenadas envueltas.
    """
    alto, ancho = forma
    tw, th = ancho * cx, alto * cy
    rng = np.random.default_rng(semilla)
    salida = np.zeros(forma)
    for _ in range(int(n)):
        x0, y0 = rng.uniform(0, tw), rng.uniform(0, th)
        a = rng.uniform(0, math.pi) if angulo is None else angulo + rng.uniform(-dispersion / 2, dispersion / 2)
        largo = largo_cm * rng.uniform(0.3, 1.0)
        ancho_r = ancho_cm * rng.uniform(0.5, 1.2)
        fuerza = rng.uniform(0.3, 1.0)
        dx, dy = math.cos(a) * largo, math.sin(a) * largo
        margen = ancho_r * 2 + abs(curva) * largo
        i0 = int(math.floor((min(x0, x0 + dx) - margen) / cx))
        i1 = int(math.ceil((max(x0, x0 + dx) + margen) / cx))
        j0 = int(math.floor((min(y0, y0 + dy) - margen) / cy))
        j1 = int(math.ceil((max(y0, y0 + dy) + margen) / cy))
        ii = np.arange(i0, i1 + 1)
        jj = np.arange(j0, j1 + 1)
        px = (ii[None, :] + 0.5) * cx - x0
        py = (jj[:, None] + 0.5) * cy - y0
        t = np.clip((px * dx + py * dy) / (largo * largo), 0.0, 1.0)
        # Un poco de curva: la raya se desvía en perpendicular como una parábola.
        flecha = curva * largo * 4 * t * (1 - t)
        qx = px - (t * dx - flecha * math.sin(a))
        qy = py - (t * dy + flecha * math.cos(a))
        d = np.hypot(qx, qy)
        perfil = np.clip(1.0 - d / ancho_r, 0.0, 1.0) * fuerza * (1.0 - 0.6 * np.abs(2 * t - 1) ** 3)
        sub = np.ix_(jj % alto, ii % ancho)
        salida[sub] = np.maximum(salida[sub], perfil)
    return salida


def celdas(forma, cx, cy, tam_cm, semilla, temblor=0.9, pesos=0.0, estirar=1.0):
    """Voronoi que repite: (ids, distancia al borde en cm, valor al azar 0-1 por celda)."""
    alto, ancho = forma
    tile = (ancho * cx, alto * cy)
    x, y = rejilla(forma, cx, cy)
    nc = (max(2, int(round(tile[0] / tam_cm))), max(2, int(round(tile[1] / tam_cm))))
    ids = patrones.voronoi_azar(x, y, tile, nc, semilla, temblor=temblor, pesos=pesos, estirar=estirar)
    borde = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
    dist = distancia_interior(~borde, cx, cy, tam_cm)
    valor = np.random.default_rng(semilla + 99).uniform(0, 1, nc[0] * nc[1])[ids]
    return ids, dist, valor


def grietas(forma, cx, cy, tam_cm, semilla, ancho_cm, temblor=0.9):
    """Red de grietas (barro seco, craquelado): 1 en la grieta."""
    _, dist, _ = celdas(forma, cx, cy, tam_cm, semilla, temblor=temblor)
    ondula = (ruido_cm(forma, cx, cy, tam_cm / 4.0, semilla + 7) - 0.5) * ancho_cm
    return 1.0 - suave(dist + ondula, 0.0, ancho_cm)


def tejido(forma, cx, cy, paso_cm, patron, semilla, hueco=0.12, fibra=0.6):
    """Tejido de calada: ``patron`` matriz (filas × columnas) con 1 donde la urdimbre (vertical)
    va por encima. Devuelve (altura 0-1, es_urdimbre 0/1, fibra -0,5..0,5).

    La imagen debe medir un número entero de repeticiones del patrón (paso × columnas).
    """
    x, y = rejilla(forma, cx, cy)
    m = np.asarray(patron)
    filas, cols = m.shape
    i, j = np.floor(x / paso_cm).astype(np.int64), np.floor(y / paso_cm).astype(np.int64)
    fx, fy = x / paso_cm - i, y / paso_cm - j
    arriba = m[j % filas, i % cols] > 0
    # Perfil de hilo redondo con un poco de hueco entre hilos.
    def perfil(f):
        g = np.clip((f - hueco / 2) / (1 - hueco), 0.0, 1.0)
        return np.sqrt(np.clip(np.sin(np.pi * g), 0.0, 1.0))
    # El hilo que va encima baja hacia donde se mete por debajo (vecinos del patrón).
    urd = perfil(fx)
    tra = perfil(fy)
    antes_u = m[(j - 1) % filas, i % cols] > 0
    despues_u = m[(j + 1) % filas, i % cols] > 0
    caida_u = 1.0 - 0.35 * ((~antes_u) * (1 - fy) ** 2 + (~despues_u) * fy ** 2)
    antes_t = m[j % filas, (i - 1) % cols] > 0
    despues_t = m[j % filas, (i + 1) % cols] > 0
    caida_t = 1.0 - 0.35 * (antes_t * (1 - fx) ** 2 + despues_t * fx ** 2)
    h_u = 0.55 + 0.45 * urd * caida_u
    h_t = 0.55 + 0.45 * tra * caida_t
    altura = np.where(arriba, h_u, h_t) * np.where(arriba, urd > 0, tra > 0)
    fib_u = estirado(forma, cx, cy, paso_cm * 0.15, semilla, 6.0, eje="y") - 0.5
    fib_t = estirado(forma, cx, cy, paso_cm * 0.15, semilla + 1, 6.0, eje="x") - 0.5
    fib = np.where(arriba, fib_u, fib_t)
    altura = altura + fibra * 0.15 * fib
    return altura, arriba.astype(np.float64), fib


TAFETAN = [[1, 0], [0, 1]]
SARGA_2_1 = [[1, 1, 0], [0, 1, 1], [1, 0, 1]]
SARGA_2_2 = [[1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 1], [1, 0, 0, 1]]
SATEN_5 = [[1, 0, 0, 0, 0], [0, 0, 1, 0, 0], [0, 0, 0, 0, 1], [0, 1, 0, 0, 0], [0, 0, 0, 1, 0]]


def tinte(rgb_objetivo, rgb_base=(0.5, 0.5, 0.5)):
    """Multiplicador (alrededor de 0,5) que lleva un color base a otro: para óxido, pátina..."""
    return tuple(0.5 * o / max(b, 1e-3) for o, b in zip(rgb_objetivo, rgb_base))
