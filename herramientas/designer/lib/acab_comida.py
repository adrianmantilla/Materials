"""Acabados de fruta y comida: cítricos, manzana, plátano, fresa, uva, pan, queso, chocolate, carne..."""

import math

import numpy as np

import patrones
from superficie import (celdas, distancia_interior, estirado, gris, grietas, hoyuelos, manchas_fractales,
                        mezclar, rayas, rejilla, ruido_cm, salpicado, suave)


def citrico(forma, cx, cy, poro=0.07, cobertura=0.35):
    """Piel de naranja o limón: glándulas de aceite hundidas muy juntas y brillo ceroso."""
    _, dist, _v = celdas(forma, cx, cy, poro * 1.8, 9101, temblor=1.0)
    glandula = suave(dist / (poro * 0.9), 0.35 + 0.4 * (1 - cobertura), 1.0)
    bulto = ruido_cm(forma, cx, cy, 0.5, 9102, octavas=2) - 0.5
    mancha = ruido_cm(forma, cx, cy, 2.0, 9103, octavas=3) - 0.5
    color = np.dstack([0.5 + 0.04 * mancha, 0.5 + 0.06 * mancha, 0.5 + 0 * mancha]) * (1 - 0.08 * glandula[..., None])
    rug = 0.5 + 0.12 * glandula + 0.03 * bulto
    return color, rug, 0.55 - 0.4 * glandula + 0.15 * bulto


def manzana(forma, cx, cy):
    """Manzana: estrías de color verticales, lenticelas claras y cera."""
    estria = estirado(forma, cx, cy, 0.25, 9201, 8.0, eje="y", octavas=3) - 0.5
    lenticela = salpicado(forma, cx, cy, 0.04, 9202, 0.012, borde=0.05)
    mancha = ruido_cm(forma, cx, cy, 2.5, 9203, octavas=3) - 0.5
    lum = 0.5 + 0.10 * estria + 0.05 * mancha
    color = np.dstack([lum * (1 + 0.05 * mancha), lum * (1 - 0.08 * estria + 0.1 * mancha), lum])
    color = mezclar(color, (0.75, 0.68, 0.45), 0.7 * lenticela)
    rug = 0.5 + 0.06 * mancha + 0.1 * lenticela
    return color, rug, 0.5 + 0.08 * mancha + 0.1 * lenticela


def platano(forma, cx, cy, maduro=0.5):
    """Plátano: estrías longitudinales finas y motas de azúcar marrones."""
    estria = estirado(forma, cx, cy, 0.05, 9301, 25.0, eje="y", octavas=2) - 0.5
    mota = salpicado(forma, cx, cy, 0.12, 9302, 0.05 * maduro, borde=0.08)
    mota2 = salpicado(forma, cx, cy, 0.04, 9303, 0.04 * maduro, borde=0.06)
    m = np.maximum(mota, mota2)
    color = gris(0.5 + 0.015 * estria)
    color = color * (1 - m[..., None] * np.array([0.55, 0.65, 0.75]))
    rug = 0.5 + 0.02 * estria + 0.1 * m
    return color, rug, 0.5 + 0.1 * estria - 0.1 * m


def fresa(forma, cx, cy, paso=0.45):
    """Fresa: aquenios (pepitas) amarillos en hoyuelos ordenados al tresbolillo, piel brillante."""
    x, y = rejilla(forma, cx, cy)
    r = paso / math.sqrt(3)
    ids = patrones.red_voronoi(x, y, (math.sqrt(3) * r, 0.0), (math.sqrt(3) * r / 2, 1.5 * r))
    borde = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
    dist = distancia_interior(~borde, cx, cy, paso)
    # El centro de cada celda está lejos del borde: allí va el hoyuelo con la pepita.
    lejos = dist / max(1e-6, float(dist.max()))
    hoyo = suave(lejos, 0.55, 0.95)
    pepita = suave(lejos, 0.82, 0.92)
    mancha = ruido_cm(forma, cx, cy, 1.0, 9401, octavas=3) - 0.5
    color = gris(0.5 + 0.05 * mancha)
    color = mezclar(color * (1 - 0.15 * hoyo[..., None]), (0.85, 0.75, 0.30), 0.9 * pepita)
    rug = 0.5 + 0.15 * pepita + 0.05 * hoyo
    return color, rug, 0.6 - 0.35 * hoyo + 0.25 * pepita + 0.05 * mancha


def uva(forma, cx, cy):
    """Uva o ciruela: piel lisa con «pruina» (velo blanquecino mate) en manchas."""
    velo = np.clip((ruido_cm(forma, cx, cy, 0.8, 9501, octavas=4) - 0.35) * 2.5, 0, 1)
    grano = ruido_cm(forma, cx, cy, 0.01, 9502) - 0.5
    color = gris(0.5 + 0.12 * velo + 0.02 * grano)
    rug = 0.5 - 0.2 + 0.4 * velo
    return color, rug, 0.5 + 0.05 * grano


def tomate(forma, cx, cy):
    """Tomate o pimiento: piel muy brillante y lisa, con leves manchas de maduración."""
    mancha = ruido_cm(forma, cx, cy, 2.0, 9601, octavas=3) - 0.5
    onda = ruido_cm(forma, cx, cy, 0.8, 9602, octavas=2) - 0.5
    color = np.dstack([0.5 + 0.03 * mancha, 0.5 + 0.08 * mancha, 0.5 + 0 * mancha])
    return color, 0.5 + 0.03 * mancha, 0.5 + 0.2 * onda


def aguacate(forma, cx, cy):
    """Aguacate: piel granulosa con bultitos oscuros."""
    bulto = ruido_cm(forma, cx, cy, 0.12, 9701, octavas=2) - 0.5
    grande = ruido_cm(forma, cx, cy, 0.6, 9702, octavas=2) - 0.5
    lum = 0.5 + 0.12 * bulto + 0.05 * grande
    color = np.dstack([lum, lum * (1 + 0.05 * bulto), lum])
    return color, 0.5 + 0.05 * bulto, 0.5 + 0.45 * bulto + 0.2 * grande


def kiwi(forma, cx, cy):
    """Kiwi: piel parda con pelusa corta y erizada."""
    pelo = estirado(forma, cx, cy, 0.01, 9801, 5.0, eje="y", octavas=2) - 0.5
    pelo2 = estirado(forma, cx, cy, 0.01, 9802, 5.0) - 0.5
    mancha = ruido_cm(forma, cx, cy, 0.6, 9803, octavas=3) - 0.5
    p = np.maximum(pelo, pelo2)
    color = gris(0.5 + 0.12 * p + 0.06 * mancha)
    return color, 0.5 + 0.05 * p, 0.5 + 0.4 * p + 0.1 * mancha


def melon(forma, cx, cy):
    """Melón cantalupo: red de corcho en relieve sobre piel lisa."""
    red = grietas(forma, cx, cy, 0.7, 9901, 0.07)
    fino = grietas(forma, cx, cy, 0.25, 9902, 0.025)
    mancha = ruido_cm(forma, cx, cy, 2.0, 9903, octavas=3) - 0.5
    r = np.maximum(red, 0.6 * fino)
    color = mezclar(gris(0.5 + 0.06 * mancha), (0.62, 0.58, 0.45), 0.8 * r)
    return color, 0.5 + 0.25 * r, 0.4 + 0.45 * r + 0.05 * mancha


def corteza_pan(forma, cx, cy, tostado=0.6):
    """Corteza de pan: burbujas, grietas, tostado irregular y harina."""
    burbuja = hoyuelos(forma, cx, cy, 0.25, 10001, 0.12)
    bulto = ruido_cm(forma, cx, cy, 0.6, 10002, octavas=3) - 0.5
    grieta = grietas(forma, cx, cy, 1.8, 10003, 0.05) * suave(ruido_cm(forma, cx, cy, 3.0, 10005), 0.4, 0.6)
    harina = manchas_fractales(forma, cx, cy, 1.5, 10004, 0.15)
    tueste = np.clip(0.5 + bulto * 1.5, 0, 1) * tostado
    lum = 0.5 - 0.2 * tueste + 0.15 * grieta - 0.05 * burbuja
    color = np.dstack([lum, lum * (1 - 0.15 * tueste), lum * (1 - 0.3 * tueste)])
    color = mezclar(color, (0.75, 0.72, 0.66), 0.6 * harina)
    rug = 0.5 + 0.1 * harina - 0.08 * tueste
    return color, rug, 0.55 + 0.35 * bulto - 0.3 * grieta - 0.2 * burbuja


def queso(forma, cx, cy, ojos=1.0):
    """Queso curado: ojos redondos, cristales y corte con marcas de cuchillo."""
    x, y = rejilla(forma, cx, cy)
    ojo = hoyuelos(forma, cx, cy, 0.6, 10101, 0.06 * ojos)
    cristal = salpicado(forma, cx, cy, 0.02, 10102, 0.01, borde=0.05)
    corte = estirado(forma, cx, cy, 0.08, 10103, 20.0) - 0.5
    mancha = ruido_cm(forma, cx, cy, 2.0, 10104, octavas=3) - 0.5
    color = gris(0.5 + 0.04 * mancha + 0.1 * cristal - 0.08 * ojo)
    rug = 0.5 + 0.05 * cristal - 0.15 * ojo
    return color, rug, 0.55 - 0.5 * ojo + 0.05 * corte + 0.03 * cristal


def chocolate(forma, cx, cy, blanqueado=0.3):
    """Chocolate: liso y brillante con marcas del molde y algo de «floración» blanquecina."""
    flor = manchas_fractales(forma, cx, cy, 1.5, 10201, 0.12 * blanqueado / 0.3)
    r = rayas(forma, cx, cy, 40, 2.0, 0.01, 10202, curva=0.2)
    onda = ruido_cm(forma, cx, cy, 1.0, 10203, octavas=2) - 0.5
    color = gris(0.5 + 0.12 * flor - 0.02 * r)
    rug = 0.5 + 0.3 * flor + 0.1 * r + 0.02 * onda
    return color, rug, 0.5 + 0.15 * onda - 0.15 * r


def carne(forma, cx, cy, asada=False):
    """Carne: fibras musculares, vetas de grasa blanca; asada, costra oscura y agrietada."""
    fibra = estirado(forma, cx, cy, 0.04, 10301, 15.0, octavas=2) - 0.5
    grasa = suave(estirado(forma, cx, cy, 0.5, 10302, 1.8, octavas=4), 0.7, 0.76)
    hum = ruido_cm(forma, cx, cy, 1.0, 10303, octavas=3) - 0.5
    lum = 0.5 + 0.08 * fibra + 0.05 * hum
    color = gris(lum)
    color = mezclar(color, (0.95, 0.85, 0.78), 0.85 * grasa)
    rug = 0.5 - 0.15 + 0.06 * fibra + 0.1 * grasa
    altura = 0.5 + 0.3 * fibra + 0.1 * grasa
    if asada:
        costra = grietas(forma, cx, cy, 0.5, 10304, 0.04)
        quemado = np.clip(0.5 + 1.5 * hum, 0, 1)
        color = color * (0.55 - 0.25 * quemado[..., None]) * (1 - 0.3 * costra[..., None])
        rug = rug + 0.25
        altura = altura - 0.2 * costra + 0.15 * hum
    return color, rug, altura


def cascara_huevo(forma, cx, cy, motas=0.0):
    """Cáscara de huevo: poros finísimos, superficie mate y (huevo moreno) motas."""
    poro = hoyuelos(forma, cx, cy, 0.008, 10401, 0.05)
    bulto = ruido_cm(forma, cx, cy, 0.1, 10402, octavas=2) - 0.5
    mancha = ruido_cm(forma, cx, cy, 1.0, 10403, octavas=3) - 0.5
    color = gris(0.5 + 0.03 * mancha - 0.05 * poro)
    if motas:
        m = salpicado(forma, cx, cy, 0.05, 10404, 0.05 * motas, borde=0.08)
        color = color * (1 - m[..., None] * np.array([0.3, 0.4, 0.5]))
    return color, 0.5 + 0.05 * poro, 0.5 + 0.2 * bulto - 0.3 * poro


def caramelo(forma, cx, cy):
    """Caramelo duro o glaseado: vidrioso, con burbujitas y alguna raya."""
    burbuja = salpicado(forma, cx, cy, 0.03, 10501, 0.01, borde=0.06)
    onda = ruido_cm(forma, cx, cy, 0.6, 10502, octavas=2) - 0.5
    r = rayas(forma, cx, cy, 10, 1.0, 0.004, 10503) * 0.5
    color = gris(0.5 + 0.06 * burbuja + 0.02 * onda)
    return color, 0.5 + 0.12 * r + 0.05 * burbuja, 0.5 + 0.25 * onda - 0.1 * r


def mantequilla(forma, cx, cy):
    """Mantequilla o crema untada: pasadas de cuchillo suaves."""
    pasada = estirado(forma, cx, cy, 0.6, 10601, 5.0, octavas=2) - 0.5
    borde = 1 - suave(np.abs(pasada), 0.0, 0.03)
    grano = ruido_cm(forma, cx, cy, 0.02, 10602) - 0.5
    color = gris(0.5 + 0.03 * pasada)
    return color, 0.5 + 0.06 * borde + 0.02 * grano, 0.5 + 0.35 * pasada + 0.1 * borde


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.4, familia="Comida", **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


F = "Fruta"
ACABADOS = [
    _a("piel_naranja", citrico, "Piel de naranja", (6.0, 6.0), 0.06, "#e07a1f", ["naranja", "mandarina"],
       rug=0.35, familia=F),
    _a("piel_limon", citrico, "Piel de limón", (6.0, 6.0), 0.05, "#e3cf3a", ["limon", "lima"], rug=0.3,
       familia=F, poro=0.05, cobertura=0.28),
    _a("piel_manzana", manzana, "Piel de manzana", (6.0, 6.0), 0.01, "#a3201f", ["manzana", "pera"], rug=0.3,
       familia=F),
    _a("piel_platano", platano, "Piel de plátano", (8.0, 8.0), 0.02, "#e3c23a", ["platano", "banana"],
       rug=0.4, familia=F),
    _a("piel_fresa", fresa, "Piel de fresa", (math.sqrt(3) * 0.45 / math.sqrt(3) * 12, 1.5 * 0.45 / math.sqrt(3) * 14),
       0.06, "#c3162a", ["fresa", "frambuesa"], rug=0.3, familia=F),
    _a("piel_uva", uva, "Piel de uva o ciruela", (3.0, 3.0), 0.005, "#4b2340", ["uva", "ciruela", "arandano"],
       rug=0.3, familia=F),
    _a("piel_tomate", tomate, "Piel de tomate", (6.0, 6.0), 0.01, "#c92a1c", ["tomate", "pimiento", "cereza"],
       rug=0.15, familia=F),
    _a("piel_aguacate", aguacate, "Piel de aguacate", (6.0, 6.0), 0.08, "#2f3a1f", ["aguacate"], rug=0.6,
       familia=F),
    _a("piel_kiwi", kiwi, "Piel de kiwi", (4.0, 4.0), 0.03, "#7a5b38", ["kiwi", "melocoton"], rug=0.85,
       familia=F),
    _a("piel_melon", melon, "Piel de melón", (8.0, 8.0), 0.15, "#a6a067", ["melon", "cantalupo"], rug=0.6,
       familia=F),
    _a("corteza_pan", corteza_pan, "Corteza de pan", (10.0, 10.0), 0.2, "#c88b4a", ["pan", "corteza de pan",
       "bolleria"], rug=0.7),
    _a("corteza_pan_tostada", corteza_pan, "Corteza de pan tostada", (10.0, 10.0), 0.2, "#8a5226",
       ["corteza de pan tostada", "tostada"], rug=0.7, tostado=1.0),
    _a("queso_curado", queso, "Queso con ojos", (10.0, 10.0), 0.3, "#e8cf7a", ["queso"], rug=0.5),
    _a("chocolate", chocolate, "Chocolate", (8.0, 8.0), 0.01, "#4a2a1a", ["chocolate", "cacao"], rug=0.25),
    _a("carne_cruda", carne, "Carne cruda", (8.0, 8.0), 0.05, "#9c2b2b", ["carne cruda", "filete"], rug=0.3),
    _a("carne_asada", carne, "Carne asada", (8.0, 8.0), 0.08, "#8a4a2a", ["carne asada", "asado"], rug=0.5,
       asada=True),
    _a("cascara_huevo", cascara_huevo, "Cáscara de huevo", (4.0, 4.0), 0.01, "#e9e2d4", ["huevo", "cascara"],
       rug=0.6),
    _a("cascara_huevo_moreno", cascara_huevo, "Cáscara de huevo moreno", (4.0, 4.0), 0.01, "#c08a5c",
       ["huevo moreno"], rug=0.6, motas=1.0),
    _a("caramelo", caramelo, "Caramelo duro", (4.0, 4.0), 0.01, "#b8461f", ["caramelo", "glaseado", "gominola"],
       rug=0.1),
    _a("mantequilla", mantequilla, "Mantequilla untada", (8.0, 8.0), 0.05, "#f0d98a", ["mantequilla", "crema",
       "nata"], rug=0.45),
]
