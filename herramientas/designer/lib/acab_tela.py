"""Acabados de telas, cuero, ante, pelo y moqueta."""

import math

import numpy as np

from superficie import (SARGA_2_1, SATEN_5, TAFETAN, celdas, estirado, gris, hoyuelos, manchas_fractales,
                        rejilla, ruido_cm, salpicado, suave, tejido)
import patrones


def _hilo_irregular(forma, cx, cy, paso, semilla, fuerza):
    """Engrosamientos del hilo (slub) a lo largo de urdimbre y trama."""
    u = estirado(forma, cx, cy, paso * 2, semilla, 15.0, eje="y") - 0.5
    t = estirado(forma, cx, cy, paso * 2, semilla + 1, 15.0, eje="x") - 0.5
    return fuerza * u, fuerza * t


def tela(forma, cx, cy, paso=0.04, patron=TAFETAN, hueco=0.12, slub=0.3, contraste=0.06, trama=0.0,
         pelusa=0.3, desgaste=0.0):
    """Tela de calada genérica: algodón, lino, lona, seda, satén, vaquero (``trama`` aclara la trama)."""
    h, urd, fib = tejido(forma, cx, cy, paso, patron, 5101, hueco=hueco)
    su, st = _hilo_irregular(forma, cx, cy, paso, 5102, slub)
    irregular = np.where(urd > 0.5, su, st)
    pel = ruido_cm(forma, cx, cy, paso * 0.3, 5103) - 0.5
    lavado = ruido_cm(forma, cx, cy, 3.0, 5104, octavas=3) - 0.5
    lum = (0.5 + contraste * (h - 0.6) + 0.08 * irregular + 0.03 * fib + 0.03 * pelusa * pel
           + trama * (0.5 - urd))
    if desgaste:
        claro = np.clip(desgaste * (lavado + 0.2) * 2, 0, 1) * urd
        lum = lum + 0.25 * claro
    color = gris(lum)
    rug = 0.5 + 0.05 * pel * pelusa + 0.03 * (1 - h)
    altura = 0.5 + 0.45 * (h - 0.6) + 0.1 * irregular + 0.05 * pelusa * pel
    return color, rug, altura


def punto(forma, cx, cy, ancho=0.4, alto=0.32, pelusa=0.6):
    """Punto de media (jersey): columnas de uves formadas por dos patas inclinadas."""
    x, y = rejilla(forma, cx, cy)
    i = np.floor(x / ancho)
    u = x / ancho - i - 0.5  # -0,5..0,5
    v = (y / alto) % 1.0
    # Cada pata es una elipse inclinada: izquierda (u<0) y derecha (u>0), en V hacia abajo.
    lado = np.sign(u)
    s = np.abs(u) - 0.25
    t = v - 0.5
    ang = math.radians(30)
    a = s * math.cos(ang) - lado * 0 + t * math.sin(ang)
    b = -s * math.sin(ang) + t * math.cos(ang)
    pata = np.sqrt(np.clip(1 - (a / 0.24) ** 2 - (b / 0.62) ** 2, 0, 1))
    fib = estirado(forma, cx, cy, 0.02, 5201, 4.0, eje="y") - 0.5
    pel = ruido_cm(forma, cx, cy, 0.03, 5202) - 0.5
    lum = 0.5 + 0.10 * (pata - 0.5) + 0.04 * fib + 0.04 * pelusa * pel
    color = gris(lum)
    rug = 0.5 + 0.05 * pelusa
    altura = 0.2 + 0.6 * pata + 0.08 * fib + 0.06 * pelusa * pel
    return color, rug, altura


def fieltro(forma, cx, cy):
    """Fieltro: fibras apelmazadas sin trama, con zonas más y menos densas."""
    fx = estirado(forma, cx, cy, 0.01, 5301, 8.0) - 0.5
    fy = estirado(forma, cx, cy, 0.01, 5302, 8.0, eje="y") - 0.5
    denso = ruido_cm(forma, cx, cy, 0.4, 5303, octavas=3) - 0.5
    pel = ruido_cm(forma, cx, cy, 0.01, 5304) - 0.5
    fibra = np.maximum(fx, fy)
    color = gris(0.5 + 0.06 * fibra + 0.05 * denso)
    rug = 0.5 + 0.04 * pel
    return color, rug, 0.5 + 0.3 * fibra + 0.25 * denso + 0.1 * pel


def terciopelo(forma, cx, cy, aplastado=0.4):
    """Terciopelo: pelo corto muy denso; las zonas aplastadas cambian de brillo."""
    zona = ruido_cm(forma, cx, cy, 2.5, 5401, octavas=3) - 0.5
    pel = ruido_cm(forma, cx, cy, 0.008, 5402) - 0.5
    marca = manchas_fractales(forma, cx, cy, 4.0, 5403, aplastado * 0.4)
    lum = 0.5 + 0.12 * zona + 0.04 * pel - 0.1 * marca
    color = gris(lum)
    rug = 0.5 + 0.08 * zona - 0.1 * marca + 0.03 * pel
    return color, rug, 0.5 + 0.2 * pel + 0.1 * zona


def rizo(forma, cx, cy, tam=0.12):
    """Rizo de toalla: bucles apretados que asoman en todas direcciones."""
    r = ruido_cm(forma, cx, cy, tam * 0.4, 5501, octavas=2)
    valor = ruido_cm(forma, cx, cy, tam * 3, 5503)
    bucle = suave(r, 0.35, 0.75) ** 0.7
    pel = ruido_cm(forma, cx, cy, 0.02, 5502) - 0.5
    color = gris(0.5 + 0.08 * (bucle - 0.5) + 0.04 * (valor - 0.5) + 0.03 * pel)
    rug = 0.5 + 0.04 * pel
    return color, rug, 0.25 + 0.55 * bucle + 0.1 * pel


def pique(forma, cx, cy, radio=0.07):
    """Tejido técnico deportivo (piqué/malla): panal de agujeritos regulares."""
    x, y = rejilla(forma, cx, cy)
    ids = patrones.red_voronoi(x, y, (math.sqrt(3) * radio, 0.0), (math.sqrt(3) * radio / 2, 1.5 * radio))
    borde = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
    from superficie import distancia_interior
    dist = distancia_interior(~borde, cx, cy, radio)
    hoyo = 1.0 - suave(dist, 0.0, radio * 0.55)
    agujero = 1.0 - hoyo
    fib = estirado(forma, cx, cy, 0.01, 5602, 5.0) - 0.5
    color = gris(0.5 - 0.12 * suave(agujero, 0.6, 0.9) + 0.03 * fib)
    rug = 0.5 + 0.03 * fib
    return color, rug, 0.3 + 0.5 * hoyo + 0.05 * fib


def moqueta(forma, cx, cy, paso=0.3):
    """Moqueta de bucle: filas de bucles con pelusa."""
    x, y = rejilla(forma, cx, cy)
    fila = np.floor(y / paso)
    u = (x / paso + 0.5 * (fila % 2)) % 1.0 - 0.5
    v = (y / paso) % 1.0 - 0.5
    bucle = np.sqrt(np.clip(1 - (u / 0.45) ** 2 - (v / 0.5) ** 2, 0, 1))
    pel = ruido_cm(forma, cx, cy, 0.02, 5701) - 0.5
    tono = ruido_cm(forma, cx, cy, 0.6, 5702, octavas=2) - 0.5
    color = gris(0.5 + 0.08 * (bucle - 0.5) + 0.06 * tono + 0.04 * pel)
    rug = 0.5 + 0.04 * pel
    return color, rug, 0.2 + 0.6 * bucle + 0.12 * pel


def cuero(forma, cx, cy, grano=0.25, arrugas=1.0, brillo=0.0):
    """Cuero de flor: celdas del grano con surcos, poros y arrugas grandes."""
    _, dist, valor = celdas(forma, cx, cy, grano, 5801, temblor=1.0, pesos=0.5)
    surco = 1.0 - suave(dist, 0.0, grano * 0.12)
    cojin = np.sqrt(suave(dist, 0.0, grano * 0.45))
    poro = hoyuelos(forma, cx, cy, 0.03, 5802, 0.04)
    arr = estirado(forma, cx, cy, 0.4, 5803, 3.0, octavas=2) - 0.5
    pliegue = 1 - suave(np.abs(arr), 0.0, 0.06)
    tono = ruido_cm(forma, cx, cy, 3.0, 5804, octavas=3) - 0.5
    roce = manchas_fractales(forma, cx, cy, 5.0, 5805, 0.15) * brillo
    lum = 0.5 + 0.06 * tono - 0.10 * surco - 0.08 * poro - 0.06 * pliegue * arrugas + 0.03 * (valor - 0.5)
    color = gris(lum)
    rug = 0.5 + 0.12 * surco + 0.05 * poro - 0.1 * roce + 0.03 * tono
    altura = 0.35 + 0.3 * cojin - 0.15 * surco - 0.2 * poro - 0.2 * pliegue * arrugas + 0.1 * arr
    return color, rug, altura


def ante(forma, cx, cy):
    """Ante: pelusa corta y marcas de pasar la mano (más claro o más oscuro según el pelo)."""
    pel = ruido_cm(forma, cx, cy, 0.008, 5901, octavas=2) - 0.5
    marca = estirado(forma, cx, cy, 1.0, 5902, 4.0, octavas=2) - 0.5
    zona = ruido_cm(forma, cx, cy, 3.0, 5903, octavas=3) - 0.5
    lum = 0.5 + 0.10 * np.tanh(4 * marca) * 0.6 + 0.06 * zona + 0.05 * pel
    color = gris(lum)
    rug = 0.5 + 0.04 * pel
    return color, rug, 0.5 + 0.2 * pel + 0.05 * marca


def pelo(forma, cx, cy, largo=12.0):
    """Pelo corto (peluche, animal): mechones que siguen una dirección que ondula."""
    flujo = ruido_cm(forma, cx, cy, 4.0, 6001, octavas=2) - 0.5
    hebra = estirado(forma, cx, cy, 0.012, 6002, largo, eje="y", octavas=2) - 0.5
    hebra2 = estirado(forma, cx, cy, 0.02, 6003, largo * 0.6, eje="y") - 0.5
    mechon = ruido_cm(forma, cx, cy, 0.5, 6004, octavas=2) - 0.5
    lum = 0.5 + 0.14 * hebra + 0.08 * hebra2 + 0.08 * mechon + 0.04 * flujo
    color = gris(lum)
    rug = 0.5 + 0.05 * hebra
    return color, rug, 0.5 + 0.35 * hebra + 0.2 * mechon


def ripstop(forma, cx, cy, paso=0.03, rejilla_cm=0.5):
    """Nailon ripstop: tafetán fino con un hilo más grueso cada medio centímetro."""
    color, rug, altura = tela(forma, cx, cy, paso=paso, contraste=0.04, slub=0.1, pelusa=0.1)
    x, y = rejilla(forma, cx, cy)
    linea = np.maximum(1 - suave(np.abs((x % rejilla_cm) - rejilla_cm / 2), paso * 0.6, paso * 1.2),
                       1 - suave(np.abs((y % rejilla_cm) - rejilla_cm / 2), paso * 0.6, paso * 1.2))
    color = color * (1 + 0.06 * linea[..., None])
    return color, rug - 0.05 * linea, altura + 0.2 * linea


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.8, familia="Tela", **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


C = "Cuero y pelo"
ACABADOS = [
    _a("algodon", tela, "Algodón (tafetán)", (4.0, 4.0), 0.03, "#d9d4c8", ["algodon", "camiseta", "sabana"]),
    _a("lino", tela, "Lino", (6.0, 6.0), 0.04, "#cdbf9f", ["lino"], paso=0.06, slub=0.8, hueco=0.18,
       contraste=0.1),
    _a("lona", tela, "Lona", (8.0, 8.0), 0.06, "#8f8668", ["lona", "toldo", "mochila"], paso=0.1, slub=0.4,
       hueco=0.08, contraste=0.1),
    _a("arpillera", tela, "Arpillera (yute)", (12.0, 12.0), 0.15, "#9c8259", ["arpillera", "yute", "saco"],
       paso=0.25, slub=1.2, hueco=0.32, contraste=0.2, pelusa=0.8),
    _a("vaquero", tela, "Vaquero (sarga)", (6.0, 6.0), 0.03, "#2f4a74", ["vaquero", "denim", "tejano"],
       paso=0.05, patron=SARGA_2_1, slub=0.5, trama=0.35, desgaste=0.6, contraste=0.05),
    _a("seda", tela, "Seda", (2.0, 2.0), 0.005, "#b03a48", ["seda"], rug=0.35, paso=0.0125, slub=0.6,
       contraste=0.08, pelusa=0.05),
    _a("saten", tela, "Satén", (2.0, 2.0), 0.005, "#c9c2d8", ["saten", "raso"], rug=0.3, paso=0.02,
       patron=SATEN_5, slub=0.2, contraste=0.15, pelusa=0.05),
    _a("nailon_ripstop", ripstop, "Nailon ripstop", (6.0, 6.0), 0.01, "#d4492a",
       ["nailon", "poliester", "chubasquero", "tienda de campaña"], rug=0.45),
    _a("punto_lana", punto, "Punto de lana", (8.0, 8.0), 0.15, "#7a3b3b", ["lana", "jersey", "punto"]),
    _a("fieltro", fieltro, "Fieltro", (6.0, 6.0), 0.04, "#5c6f56", ["fieltro"], rug=0.9),
    _a("terciopelo", terciopelo, "Terciopelo", (20.0, 20.0), 0.01, "#5b1a2b", ["terciopelo", "pana"], rug=0.7),
    _a("rizo_toalla", rizo, "Rizo de toalla", (6.0, 6.0), 0.12, "#e7e3da", ["toalla", "albornoz", "rizo"],
       rug=0.95),
    _a("pique_deportivo", pique, "Tejido deportivo de panal", (3 ** 0.5 * 0.07 * 35, 4.2), 0.03, "#20232a",
       ["poliester deportivo", "malla", "deportiv"], rug=0.6),
    _a("moqueta_bucle", moqueta, "Moqueta de bucle", (12.0, 12.0), 0.2, "#6d6a63", ["moqueta", "alfombra"],
       rug=0.95),
    _a("cuero_flor", cuero, "Cuero", (20.0, 20.0), 0.05, "#5a3a24", ["cuero", "piel", "cinturon"], rug=0.55,
       familia=C),
    _a("cuero_granulado", cuero, "Cuero granulado grueso", (20.0, 20.0), 0.08, "#1c1c1c",
       ["cuero negro", "bolso", "sofa"], rug=0.6, familia=C, grano=0.5),
    _a("cuero_liso", cuero, "Cuero liso brillante", (20.0, 20.0), 0.02, "#2a1a12",
       ["cuero brillante", "zapato", "charol"], rug=0.25, familia=C, grano=0.12, arrugas=0.5, brillo=1.0),
    _a("piel_sintetica", cuero, "Piel sintética", (20.0, 20.0), 0.03, "#3b2b23", ["piel sintetica", "polipiel",
       "skai"], rug=0.45, familia=C, grano=0.18, arrugas=0.2),
    _a("ante", ante, "Ante", (20.0, 20.0), 0.01, "#9a6b45", ["ante", "gamuza"], rug=0.9, familia=C),
    _a("pelo_corto", pelo, "Pelo corto", (10.0, 10.0), 0.08, "#8c6a4a", ["pelo", "peluche", "piel de animal"],
       rug=0.8, familia=C),
]
