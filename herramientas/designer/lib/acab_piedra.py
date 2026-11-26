"""Acabados de piedra y cerámica: mármoles, ónice, travertino, caliza, volcánicas, esmaltes y barro.

Cuando el acabado necesita mucho contraste (mármol negro con vetas blancas), la muestra es un gris
medio y el mapa de color va de muy oscuro a muy claro: Materials multiplica la receta por 2 × color.
"""

import numpy as np

from superficie import (celdas, estirado, gris, grietas, hoyuelos, manchas_fractales, mezclar, rejilla, ruido_cm,
                        salpicado, suave)


def _campo(forma, cx, cy, tam, semilla, giro=0.6):
    """Ruido retorcido (dominio deformado), base de vetas y bandas: periódico, 0-1 aprox."""
    a = ruido_cm(forma, cx, cy, tam, semilla, octavas=4)
    b = ruido_cm(forma, cx, cy, tam * 0.5, semilla + 1, octavas=3)
    c = ruido_cm(forma, cx, cy, tam * 0.15, semilla + 2, octavas=2)
    return a + giro * (b - 0.5) + 0.15 * (c - 0.5)


def _fase(forma, cx, cy, ondas, angulo_ondas=(1, 1)):
    """Fase lineal que repite: ``ondas`` vueltas en diagonal (a, b enteros) sobre la imagen."""
    x, y = rejilla(forma, cx, cy)
    a, b = angulo_ondas
    return np.pi * ondas * (a * x / (forma[1] * cx) + b * y / (forma[0] * cy))


def marmol(forma, cx, cy, fondo=0.55, veta=1.0, nube=0.06, n=3, ancho=0.06, finas=0.5, semilla=14001,
           color_veta=None, color_fondo=None, tam=30.0, giro=5.0, diagonal=(1, 1)):
    """Mármol: fondo con nubes, vetas largas que ondulan y se ramifican, y una red de vetas finas.

    Las vetas son isolíneas de una fase diagonal retorcida por ruido fractal (como el mármol que se
    pliega). ``fondo`` y ``veta`` son luminancias (0,5 = color de la receta); ``color_veta`` /
    ``color_fondo`` son multiplicadores RGB opcionales.
    """
    fase = _fase(forma, cx, cy, n, diagonal)
    torsion = _campo(forma, cx, cy, tam, semilla) - 0.5
    detalle = ruido_cm(forma, cx, cy, tam * 0.12, semilla + 3, octavas=3) - 0.5
    principal = np.exp(-(np.sin(fase + giro * torsion + 0.8 * detalle) / ancho) ** 2)
    ramal = np.exp(-(np.sin(2 * fase + giro * 1.3 * torsion + 2.5 * detalle + 1.0) / (ancho * 0.5)) ** 2)
    ramal = ramal * suave(ruido_cm(forma, cx, cy, tam * 0.3, semilla + 5, octavas=2), 0.5, 0.65)
    otra = _campo(forma, cx, cy, tam * 0.5, semilla + 9, giro=1.0) - 0.5
    fino = np.exp(-(np.sin(_fase(forma, cx, cy, n * 3, (1, -1)) + giro * 1.5 * otra) / (ancho * 0.25)) ** 2)
    mancha = ruido_cm(forma, cx, cy, tam * 0.6, semilla + 7, octavas=4) - 0.5
    v = np.clip(principal + 0.6 * ramal + finas * 0.5 * fino * suave(mancha, -0.1, 0.25), 0.0, 1.0)
    cf = np.asarray(color_fondo or (1.0, 0.995, 0.985))
    cv = np.asarray(color_veta or (1.0, 1.0, 1.0))
    base = gris(fondo + nube * mancha * 2) * cf[None, None, :]
    color = base * (1 - v[..., None]) + gris(np.full(forma, veta)) * cv[None, None, :] * v[..., None]
    grano = ruido_cm(forma, cx, cy, 0.05, semilla + 11) - 0.5
    return color + 0.01 * grano[..., None], 0.5 + 0.02 * grano + 0.03 * v, 0.5 + 0.03 * grano - 0.04 * v


def onice(forma, cx, cy):
    """Ónice: bandas concéntricas onduladas de miel a crema, con zonas más claras (translúcidas)."""
    campo = _campo(forma, cx, cy, 25.0, 14101, giro=0.9)
    banda = 0.5 + 0.5 * np.sin(2 * np.pi * 6.0 * campo)
    fina = 0.5 + 0.5 * np.sin(2 * np.pi * 23.0 * campo + 2.0)
    lum = 0.42 + 0.14 * banda + 0.04 * fina
    claro = suave(ruido_cm(forma, cx, cy, 15.0, 14102, octavas=3), 0.55, 0.75)
    color = gris(lum, (1.08, 1.0, 0.82))
    color = mezclar(color, (0.62, 0.60, 0.52), 0.6 * claro)
    grieta = grietas(forma, cx, cy, 12.0, 14103, 0.04) * suave(ruido_cm(forma, cx, cy, 10.0, 14104), 0.5, 0.6)
    color = color * (1 - 0.25 * grieta[..., None])
    return color, 0.5 + 0.03 * grieta, 0.5 - 0.05 * grieta


def travertino(forma, cx, cy):
    """Travertino: bandas horizontales y huecos alargados (sin rellenar), tono crema."""
    banda = estirado(forma, cx, cy, 1.5, 14201, 8.0, octavas=3) - 0.5
    hueco_r = estirado(forma, cx, cy, 0.5, 14202, 4.0, octavas=2)
    corte = np.quantile(hueco_r, 0.93)
    hueco = suave(hueco_r, corte, corte + 0.02)
    grano = ruido_cm(forma, cx, cy, 0.06, 14203, octavas=2) - 0.5
    color = gris(0.5 + 0.12 * banda + 0.03 * grano - 0.18 * hueco, (1.03, 1.0, 0.92))
    return color, 0.5 + 0.05 * grano + 0.15 * hueco, 0.6 + 0.1 * grano - 0.5 * hueco


def caliza(forma, cx, cy):
    """Caliza con fósiles: grano fino, conchas y trozos de concha más claros, alguna mancha ocre."""
    grano = ruido_cm(forma, cx, cy, 0.04, 14301, octavas=2) - 0.5
    _, dist, valor = celdas(forma, cx, cy, 0.8, 14302, temblor=1.0, pesos=0.7)
    concha = (valor > 0.82) * suave(dist, 0.03, 0.12)
    anillos = 0.5 + 0.5 * np.sin(dist * 60.0)
    ocre = manchas_fractales(forma, cx, cy, 6.0, 14303, 0.15)
    color = gris(0.5 + 0.05 * grano + 0.07 * concha * (0.6 + 0.4 * anillos), (1.02, 1.0, 0.95))
    color = mezclar(color, (0.56, 0.48, 0.36), 0.25 * ocre)
    return color, 0.5 + 0.06 * grano - 0.05 * concha, 0.5 + 0.3 * grano + 0.15 * concha


def basalto(forma, cx, cy):
    """Basalto: oscuro y de grano muy fino, con vacuolas (burbujas) sueltas y algún cristal verdoso."""
    grano = ruido_cm(forma, cx, cy, 0.03, 14401, octavas=2) - 0.5
    burbuja = hoyuelos(forma, cx, cy, 0.12, 14402, 0.04)
    olivino = salpicado(forma, cx, cy, 0.06, 14403, 0.015, borde=0.02)
    mancha = ruido_cm(forma, cx, cy, 5.0, 14404, octavas=3) - 0.5
    color = gris(0.5 + 0.05 * grano + 0.05 * mancha - 0.25 * burbuja)
    color = mezclar(color, (0.45, 0.55, 0.30), 0.6 * olivino)
    return color, 0.5 + 0.05 * grano + 0.1 * burbuja, 0.5 + 0.25 * grano - 0.5 * burbuja


def pomez(forma, cx, cy, tam=0.12, color_rgb=(1.0, 1.0, 0.96)):
    """Piedra pómez / volcánica porosa: muchísimos poros de varios tamaños."""
    _, dist, valor = celdas(forma, cx, cy, tam, 14501, temblor=1.0, pesos=0.8)
    poro = 1 - suave(dist, 0.0, tam * 0.45)
    poro = poro * (valor > 0.25)
    fino = hoyuelos(forma, cx, cy, tam * 0.25, 14502, 0.2)
    grano = ruido_cm(forma, cx, cy, 0.03, 14503) - 0.5
    lum = 0.52 + 0.05 * grano - 0.2 * poro - 0.08 * fino
    return gris(lum, color_rgb), 0.5 + 0.1 * poro, 0.6 - 0.45 * poro - 0.15 * fino + 0.1 * grano


def obsidiana(forma, cx, cy):
    """Obsidiana: vidrio volcánico negro y brillante, con ondas de fractura concoidea y bandas de flujo."""
    campo = _campo(forma, cx, cy, 8.0, 14601, giro=0.8)
    onda = 0.5 + 0.5 * np.sin(2 * np.pi * 9.0 * campo)
    flujo = estirado(forma, cx, cy, 1.0, 14602, 10.0, octavas=3) - 0.5
    color = gris(0.5 + 0.06 * flujo + 0.02 * onda)
    return color, 0.5 + 0.02 * onda, 0.5 + 0.25 * (onda - 0.5)


def cuarcita(forma, cx, cy):
    """Cuarcita: capas claras de grano de azúcar, brillitos y alguna banda de óxido."""
    capa = estirado(forma, cx, cy, 2.0, 14701, 5.0, octavas=4) - 0.5
    _, dist, valor = celdas(forma, cx, cy, 0.15, 14702, temblor=1.0)
    brillo = (valor > 0.9).astype(float)
    oxido = suave(estirado(forma, cx, cy, 3.0, 14703, 12.0, octavas=3), 0.62, 0.72)
    color = gris(0.52 + 0.05 * capa + 0.06 * (valor - 0.5), (1.0, 0.99, 0.97))
    color = mezclar(color, (0.60, 0.42, 0.28), 0.4 * oxido)
    junta = 1 - suave(dist, 0.0, 0.01)
    return color, 0.5 - 0.15 * brillo + 0.05 * junta, 0.5 + 0.1 * (valor - 0.5) - 0.1 * junta


def granito_rosa(forma, cx, cy):
    """Granito rosa pulido: cristales grandes de feldespato rosa, cuarzo gris y mica negra."""
    ids, dist, valor = celdas(forma, cx, cy, 0.5, 14801, temblor=1.0, pesos=0.5)
    tipo = np.digitize(valor, [0.5, 0.78, 0.9])  # feldespato, cuarzo, feldespato claro, mica
    pal = np.array([[0.62, 0.40, 0.36], [0.48, 0.47, 0.47], [0.68, 0.55, 0.50], [0.12, 0.12, 0.12]])
    tono = 0.9 + 0.2 * (np.random.default_rng(14802).uniform(0, 1, ids.max() + 1)[ids])
    color = pal[tipo] * tono[..., None]
    grano = ruido_cm(forma, cx, cy, 0.03, 14803) - 0.5
    return color + 0.02 * grano[..., None], 0.5 + 0.02 * grano, 0.5 + 0.02 * grano


def esmalte(forma, cx, cy, ondas=0.3, poros=0.02, motas=0.0, semilla=15001):
    """Cerámica esmaltada: lisa y brillante, con ondulación suave, algún poro (pinhole) y motas."""
    onda = ruido_cm(forma, cx, cy, 3.0, semilla, octavas=2) - 0.5
    acumula = ruido_cm(forma, cx, cy, 1.5, semilla + 1, octavas=3) - 0.5
    poro = hoyuelos(forma, cx, cy, 0.02, semilla + 2, poros) if poros else np.zeros(forma)
    mota = salpicado(forma, cx, cy, 0.03, semilla + 3, motas, borde=0.02) if motas else np.zeros(forma)
    color = gris(0.5 + 0.05 * acumula - 0.1 * poro)
    color = mezclar(color, (0.22, 0.18, 0.15), 0.8 * mota)
    return color, 0.5 + 0.2 * poro, 0.5 + ondas * onda - 0.2 * poro


def craquelado(forma, cx, cy):
    """Esmalte craquelado: red de grietas finas teñidas de oscuro bajo un brillo uniforme."""
    grande = grietas(forma, cx, cy, 2.0, 15101, 0.012)
    pequena = grietas(forma, cx, cy, 0.7, 15102, 0.008) * 0.6
    red = np.clip(grande + pequena, 0, 1)
    color, rug, altura = esmalte(forma, cx, cy, ondas=0.15, poros=0.0, semilla=15103)
    color = color * (1 - 0.35 * red[..., None])
    return color, rug + 0.03 * red, altura - 0.05 * red


def gres(forma, cx, cy):
    """Gres moteado: esmalte satinado con motas de hierro marrón que lo atraviesan."""
    color, rug, altura = esmalte(forma, cx, cy, ondas=0.2, poros=0.03, motas=0.025, semilla=15201)
    halo = salpicado(forma, cx, cy, 0.08, 15203, 0.04, borde=0.08)
    color = mezclar(color, (0.42, 0.36, 0.30), 0.3 * halo)
    return color, rug, altura


def terracota(forma, cx, cy):
    """Barro cocido sin esmaltar: mate, grano fino, chamota y marcas de alisado."""
    grano = ruido_cm(forma, cx, cy, 0.03, 15301, octavas=2) - 0.5
    chamota = salpicado(forma, cx, cy, 0.04, 15302, 0.03, borde=0.03)
    alisado = estirado(forma, cx, cy, 0.3, 15303, 12.0, octavas=2) - 0.5
    cal = manchas_fractales(forma, cx, cy, 4.0, 15304, 0.08)
    color = gris(0.5 + 0.05 * grano + 0.05 * alisado + 0.06 * chamota)
    color = mezclar(color, (0.62, 0.58, 0.52), 0.3 * cal)
    return color, 0.5 + 0.05 * grano - 0.05 * alisado, 0.5 + 0.3 * grano + 0.1 * alisado + 0.1 * chamota


def esmalte_reactivo(forma, cx, cy):
    """Esmalte reactivo: chorrea hacia abajo y cambia de color donde se acumula (azul a marrón)."""
    x, y = rejilla(forma, cx, cy)
    cae = estirado(forma, cx, cy, 0.4, 15401, 10.0, eje="y", octavas=4)
    nube = ruido_cm(forma, cx, cy, 2.0, 15402, octavas=4)
    grosor = np.clip(0.6 * cae + 0.6 * nube - 0.1, 0, 1)
    claro = (0.42, 0.58, 0.74)
    oscuro = (0.36, 0.24, 0.16)
    color = mezclar(gris(np.full(forma, 1.0)) * np.asarray(claro), oscuro, 1 - suave(grosor, 0.35, 0.7))
    moteado = salpicado(forma, cx, cy, 0.05, 15403, 0.06, borde=0.04) * suave(grosor, 0.5, 0.8)
    color = mezclar(color, (0.70, 0.74, 0.76), 0.5 * moteado)
    return color, 0.5 + 0.05 * (1 - grosor), 0.5 + 0.2 * (grosor - 0.5)


def loza_desconchada(forma, cx, cy):
    """Loza vieja: esmalte blanco con desconchones que dejan ver el bizcocho y grietas de uso."""
    color, rug, altura = craquelado(forma, cx, cy)
    salta = manchas_fractales(forma, cx, cy, 2.0, 15501, 0.06, detalle=0.5)
    bizcocho = gris(0.5 + 0.04 * (ruido_cm(forma, cx, cy, 0.03, 15502) - 0.5), (1.0, 0.92, 0.82))
    color = color * (1 - salta[..., None]) + 0.62 * bizcocho * salta[..., None]
    return color, rug + 0.35 * salta, altura - 0.3 * salta


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.5, familia="Piedra", **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


C = "Cerámica"
ACABADOS = [
    _a("marmol_carrara", marmol, "Mármol de Carrara", (100.0, 100.0), 0.02, "#e8e6e2", ["carrara", "marmol blanco"],
       rug=0.2, fondo=0.55, veta=0.40, ancho=0.05, finas=0.6, color_veta=(0.97, 0.98, 1.0)),
    _a("marmol_negro", marmol, "Mármol negro Marquina", (100.0, 100.0), 0.02, "#8c8c8c",
       ["marquina", "marmol negro"], rug=0.2, fondo=0.10, veta=0.95, nube=0.02, n=2, giro=3.0, ancho=0.04, finas=0.8,
       semilla=14011),
    _a("marmol_verde", marmol, "Mármol verde (serpentina)", (80.0, 80.0), 0.02, "#6f8a78",
       ["marmol verde", "serpentina"], rug=0.2, fondo=0.35, veta=0.75, nube=0.15, n=3, ancho=0.10, giro=3.5, finas=1.0,
       color_fondo=(0.75, 1.05, 0.85), semilla=14021, tam=15.0),
    _a("marmol_rosa", marmol, "Mármol rosa", (100.0, 100.0), 0.02, "#d8b0a2", ["marmol rosa", "rosa portugal"],
       rug=0.2, fondo=0.5, veta=0.62, nube=0.1, ancho=0.07, color_veta=(1.0, 0.98, 0.96), semilla=14031),
    _a("onice", onice, "Ónice", (60.0, 60.0), 0.02, "#d8b37a", ["onice", "onix"], rug=0.15),
    _a("travertino", travertino, "Travertino", (60.0, 60.0), 0.3, "#d6c4a4", ["travertino"], rug=0.6),
    _a("caliza_fosiles", caliza, "Caliza con fósiles", (40.0, 40.0), 0.1, "#cfc4ae", ["caliza", "piedra de"],
       rug=0.65),
    _a("basalto", basalto, "Basalto", (40.0, 40.0), 0.15, "#4a4a4c", ["basalto", "piedra negra"], rug=0.65),
    _a("piedra_pomez", pomez, "Piedra pómez", (20.0, 20.0), 0.4, "#c8c4b8", ["pomez", "volcanica"], rug=0.9),
    _a("tezontle", pomez, "Piedra volcánica roja", (30.0, 30.0), 0.6, "#8a3a2a", ["tezontle", "lava roja",
       "volcanica roja"], rug=0.9, tam=0.3, color_rgb=(1.05, 0.95, 0.9)),
    _a("obsidiana", obsidiana, "Obsidiana", (30.0, 30.0), 0.05, "#2a2a2e", ["obsidiana", "vidrio volcanico"],
       rug=0.08),
    _a("cuarcita", cuarcita, "Cuarcita", (30.0, 30.0), 0.08, "#d8d2c8", ["cuarcita"], rug=0.45),
    _a("granito_rosa", granito_rosa, "Granito rosa pulido", (40.0, 40.0), 0.01, "#9a8a86",
       ["granito rosa", "porriño"], rug=0.2),
    _a("ceramica_esmaltada", esmalte, "Cerámica esmaltada", (30.0, 30.0), 0.02, "#2f6a8a",
       ["ceramica", "esmaltad", "taza", "jarron"], rug=0.08, familia=C),
    _a("porcelana", esmalte, "Porcelana", (20.0, 20.0), 0.01, "#f2f2f0", ["porcelana", "plato"], rug=0.06,
       familia=C, ondas=0.08, poros=0.0),
    _a("ceramica_craquelada", craquelado, "Esmalte craquelado", (20.0, 20.0), 0.01, "#d8d0b8",
       ["craquelad", "raku"], rug=0.1, familia=C),
    _a("gres_moteado", gres, "Gres moteado", (20.0, 20.0), 0.02, "#d6cdb8", ["gres", "stoneware"], rug=0.35,
       familia=C),
    _a("terracota", terracota, "Barro cocido (terracota)", (30.0, 30.0), 0.05, "#b8643e",
       ["terracota", "barro", "maceta"], rug=0.85, familia=C),
    _a("esmalte_reactivo", esmalte_reactivo, "Esmalte reactivo", (20.0, 20.0), 0.03, "#8a8a8a",
       ["esmalte reactivo", "ceramica artesana"], rug=0.12, familia=C),
    _a("loza_desconchada", loza_desconchada, "Loza desconchada", (20.0, 20.0), 0.05, "#eeeae0",
       ["loza", "desconchad", "lavabo viejo"], rug=0.15, familia=C),
]
