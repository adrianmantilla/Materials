"""Acabados de vidrio, agua y materiales translúcidos: el relieve y la rugosidad hacen casi todo.

La transparencia la da la receta de Materials (vidrio, agua); aquí van el esmerilado, el martelado,
gotas, vaho, polvo, huellas, ondas, espuma, ámbar y escarcha.
"""

import math

import numpy as np

from acab_terreno import esparcir
from superficie import (celdas, estirado, gris, grietas, hoyuelos, manchas_fractales, mezclar, rayas, rejilla,
                        ruido_cm, salpicado, suave)


def _ondas_periodicas(forma, cx, cy, ondas, semilla):
    """Suma de senos con un número entero de ondas en cada eje (repite seguro): (a, b, amplitud)."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    rng = np.random.default_rng(semilla)
    total = np.zeros(forma)
    for a, b, amp in ondas:
        total += amp * np.sin(2 * np.pi * (a * x / tw + b * y / th) + rng.uniform(0, 2 * np.pi))
    return total


def esmerilado(forma, cx, cy):
    """Vidrio esmerilado (al ácido o arenado): grano finísimo uniforme, mate."""
    grano = ruido_cm(forma, cx, cy, 0.008, 20001) - 0.5
    return gris(0.5 + 0.02 * grano), 0.5 + 0.05 * grano, 0.5 + 0.4 * grano


def martelado(forma, cx, cy, tam=1.2, semilla=20101):
    """Vidrio martelado / impreso: hoyuelos redondeados que se tocan (como golpes de martillo)."""
    _, dist, _ = celdas(forma, cx, cy, tam, semilla, temblor=0.8)
    cuenco = 1 - np.clip(dist / (tam * 0.5), 0, 1) ** 2
    return gris(np.full(forma, 0.5)), np.full(forma, 0.5), 0.5 + 0.4 * (0.5 - cuenco)


def catedral(forma, cx, cy):
    """Vidrio catedral: ondulación irregular y suave, con burbujas pequeñas atrapadas."""
    onda = ruido_cm(forma, cx, cy, 2.0, 20201, octavas=3) - 0.5
    burbuja = salpicado(forma, cx, cy, 0.05, 20202, 0.01, borde=0.02)
    return gris(0.5 + 0.05 * burbuja), np.full(forma, 0.5), 0.5 + 0.45 * onda


def estriado(forma, cx, cy, paso=1.0):
    """Vidrio acanalado (estriado): cañas verticales redondeadas."""
    x, _ = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    p = tw / max(1, round(tw / paso))
    f = (x % p) / p
    caña = np.sqrt(np.clip(np.sin(np.pi * f), 0, 1))
    return gris(np.full(forma, 0.5)), np.full(forma, 0.5), 0.1 + 0.8 * caña


def gotas(forma, cx, cy):
    """Gotas de agua sobre el cristal: gotas redondas de muchos tamaños y algún reguero que cae."""
    alto, ancho = forma
    area = ancho * cx * alto * cy
    grande, quien, _, _ = esparcir(forma, cx, cy, int(area / 6.0), 0.35, 0.3, 20301,
                                   lambda u, v: np.where(u * u + v * v < 1, np.sqrt(np.clip(1 - u * u - v * v, 0, 1)),
                                                         0.0), variar=0.7)
    chica = hoyuelos(forma, cx, cy, 0.04, 20302, 0.08)
    reguero = rayas(forma, cx, cy, int(area / 150) + 1, 15.0, 0.12, 20303, angulo=math.pi / 2, dispersion=0.15,
                    curva=0.05)
    agua = np.maximum(np.maximum(grande, 0.5 * chica), 0.7 * reguero)
    moja = suave(agua, 0.0, 0.05)
    color = gris(0.5 - 0.03 * moja)
    return color, 0.5 - 0.35 * moja, 0.3 + 0.7 * agua


def vaho(forma, cx, cy):
    """Vaho (condensación): microgotas que empañan el cristal, con zonas limpias de regueros."""
    micro = hoyuelos(forma, cx, cy, 0.015, 20401, 0.35)
    limpio = suave(estirado(forma, cx, cy, 0.4, 20402, 30.0, eje="y", octavas=2), 0.68, 0.72)
    nube = suave(ruido_cm(forma, cx, cy, 8.0, 20403, octavas=4), 0.3, 0.6)
    empaña = nube * (1 - limpio)
    color = gris(0.5 + 0.08 * empaña)
    return color, 0.5 + 0.4 * empaña, 0.5 + 0.3 * micro * empaña


def polvo(forma, cx, cy):
    """Cristal con polvo: velo mate en nubes, motas, y marcas de trapo en arco."""
    velo = ruido_cm(forma, cx, cy, 10.0, 20501, octavas=4)
    mota = salpicado(forma, cx, cy, 0.03, 20502, 0.02, borde=0.02)
    trapo = rayas(forma, cx, cy, 25, 30.0, 2.0, 20503, curva=0.3)
    capa = np.clip(suave(velo, 0.35, 0.7) - 0.6 * trapo, 0, 1)
    color = gris(0.5 + 0.12 * capa + 0.1 * mota, (1.0, 0.99, 0.97))
    return color, 0.5 + 0.45 * capa + 0.2 * mota, 0.5 + 0.05 * mota


def huellas(forma, cx, cy):
    """Huellas dactilares grasientas sobre cristal o metal pulido: crestas en óvalo."""
    alto, ancho = forma
    area = ancho * cx * alto * cy
    cima, quien, u, v = esparcir(forma, cx, cy, max(3, int(area / 60.0)), 1.1, 0.8, 20601,
                                 lambda u, v: np.where(u * u + v * v < 1, 1.0, 0.0))
    hay = quien >= 0
    r = np.sqrt(u * u + (v * 1.1) ** 2) + 0.03 * (ruido_cm(forma, cx, cy, 0.2, 20602) - 0.5)
    cresta = 0.5 + 0.5 * np.sin(2 * np.pi * r * 18.0)
    borde = suave(1 - np.sqrt(u * u + v * v), 0.0, 0.3)
    grasa = hay * cresta * borde
    return gris(0.5 + 0.05 * grasa), 0.5 + 0.35 * grasa, 0.5 + 0.02 * grasa


def rayado(forma, cx, cy):
    """Cristal arañado: rayas finísimas sueltas y en grupo (limpieza con estropajo)."""
    alto, ancho = forma
    area = ancho * cx * alto * cy
    sueltas = rayas(forma, cx, cy, int(area / 10), 8.0, 0.006, 20701)
    grupo = rayas(forma, cx, cy, int(area / 5), 4.0, 0.004, 20702, angulo=0.3, dispersion=0.3, curva=0.2)
    grupo = grupo * suave(ruido_cm(forma, cx, cy, 6.0, 20703, octavas=2), 0.5, 0.65)
    r = np.maximum(sueltas, grupo)
    return gris(0.5 + 0.1 * r), 0.5 + 0.4 * r, 0.5 - 0.3 * r


def roto(forma, cx, cy):
    """Cristal laminado roto: telaraña de grietas radiales y concéntricas alrededor de los impactos."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    red = np.zeros(forma)
    rng = np.random.default_rng(20801)
    for _ in range(2):
        x0, y0 = rng.uniform(0, tw), rng.uniform(0, th)
        dx = (x - x0 + tw / 2) % tw - tw / 2
        dy = (y - y0 + th / 2) % th - th / 2
        d = np.hypot(dx, dy) + 1e-3
        ang = np.arctan2(dy, dx)
        ruido = ruido_cm(forma, cx, cy, 2.0, 20802, octavas=3) - 0.5
        radial = np.exp(-(np.sin(14 * ang + 1.5 * ruido) * d / 0.2) ** 2)
        anillos = np.exp(-(np.sin(2 * np.pi * (d / 4.0) ** 0.8 + 2 * ruido) / 0.12) ** 2)
        alcance = suave(1 - d / (0.45 * min(tw, th)), 0.0, 0.3)
        red = np.maximum(red, np.maximum(radial, anillos * suave(np.sin(9 * ang + ruido * 3), 0.0, 0.3)) * alcance)
    finas = grietas(forma, cx, cy, 3.0, 20803, 0.02) * 0.3
    red = np.clip(red + finas, 0, 1)
    return gris(0.5 + 0.25 * red), 0.5 + 0.3 * red, 0.5 - 0.3 * red


def agua_ondas(forma, cx, cy):
    """Superficie de agua con ondas de viento: trenes de ondas cruzados más una ondulación fina."""
    base = _ondas_periodicas(forma, cx, cy, [(3, 1, 0.5), (2, -3, 0.3), (5, 2, 0.2), (7, -6, 0.12),
                                             (11, 4, 0.08)], 20901)
    fino = ruido_cm(forma, cx, cy, 2.0, 20902, octavas=3) - 0.5
    return gris(np.full(forma, 0.5)), np.full(forma, 0.5), 0.5 + 0.25 * base / 1.2 + 0.2 * fino


def agua_lluvia(forma, cx, cy):
    """Charco con lluvia: anillos que se abren desde cada gota y se cruzan."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    rng = np.random.default_rng(21001)
    h = np.zeros(forma)
    for _ in range(int(tw * th / 40)):
        x0, y0 = rng.uniform(0, tw), rng.uniform(0, th)
        radio = rng.uniform(0.5, 6.0)
        dx = (x - x0 + tw / 2) % tw - tw / 2
        dy = (y - y0 + th / 2) % th - th / 2
        d = np.hypot(dx, dy)
        h += np.sin(2 * np.pi * (d - radio) / 0.5) * np.exp(-((d - radio) / 0.6) ** 2) * (2.0 / (1.0 + radio))
    fino = ruido_cm(forma, cx, cy, 3.0, 21002, octavas=2) - 0.5
    return gris(np.full(forma, 0.5)), np.full(forma, 0.5), 0.5 + 0.3 * np.tanh(h) + 0.05 * fino


def agua_corriente(forma, cx, cy):
    """Agua que corre (río, canal): ondulaciones alargadas en la dirección de la corriente."""
    a = estirado(forma, cx, cy, 1.5, 21101, 5.0, octavas=4) - 0.5
    b = estirado(forma, cx, cy, 0.4, 21102, 3.0, octavas=2) - 0.5
    return gris(np.full(forma, 0.5)), np.full(forma, 0.5), 0.5 + 0.6 * a + 0.2 * b


def espuma(forma, cx, cy, tam=0.4, semilla=21201, sucia=0.0):
    """Espuma (de mar o de jabón): burbujas apretadas, más claras en las paredes."""
    _, dist, valor = celdas(forma, cx, cy, tam, semilla, temblor=1.0, pesos=0.8)
    chica_d = celdas(forma, cx, cy, tam * 0.3, semilla + 1, temblor=1.0)[1]
    cupula = np.sqrt(suave(dist, 0.0, tam * 0.5))
    pared = 1 - suave(np.minimum(dist, chica_d * 2), 0.0, tam * 0.06)
    color = gris(0.5 + 0.1 * pared - 0.05 * (1 - cupula) - 0.15 * sucia * (valor - 0.5))
    return color, 0.5 - 0.2 * cupula + 0.2 * pared, 0.2 + 0.7 * cupula + 0.1 * chica_d.clip(0, 0.1) * 10


def ambar(forma, cx, cy):
    """Ámbar o resina: tonos miel en nubes, burbujas y alguna inclusión oscura, pulido."""
    nube = ruido_cm(forma, cx, cy, 2.0, 21301, octavas=4) - 0.5
    flujo = estirado(forma, cx, cy, 0.5, 21302, 6.0, octavas=3) - 0.5
    burbuja = salpicado(forma, cx, cy, 0.04, 21303, 0.015, borde=0.02)
    inclusion = salpicado(forma, cx, cy, 0.15, 21304, 0.008, borde=0.05)
    color = gris(0.5 + 0.18 * nube + 0.06 * flujo + 0.15 * burbuja, (1.1, 0.98, 0.75))
    color = mezclar(color, (0.15, 0.10, 0.06), 0.7 * inclusion)
    return color, 0.5 + 0.02 * nube, 0.5 + 0.02 * nube


def escarcha(forma, cx, cy):
    """Escarcha en el cristal: helechos de hielo que se ramifican (crestas de ruido) y un velo blanco."""
    total = np.zeros(forma)
    for k, (tam, peso) in enumerate(((3.0, 0.6), (1.0, 0.4), (0.3, 0.3))):
        r = ruido_cm(forma, cx, cy, tam, 21401 + k, octavas=2)
        total += peso * np.clip(1 - np.abs(2 * r - 1) * 6, 0, 1)
    velo = manchas_fractales(forma, cx, cy, 8.0, 21410, 0.5, detalle=0.6)
    hielo = np.clip(total * (0.4 + 0.6 * velo), 0, 1)
    return gris(0.5 + 0.35 * hielo, (0.97, 0.99, 1.02)), 0.5 + 0.4 * hielo, 0.5 + 0.3 * hielo


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.05, familia="Vidrio", **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


A = "Agua"
ACABADOS = [
    _a("vidrio_esmerilado", esmerilado, "Vidrio esmerilado", (5.0, 5.0), 0.002, "#d8e0e4", ["esmerilado",
       "mate", "translucido"], rug=0.5),
    _a("vidrio_martelado", martelado, "Vidrio martelado", (20.0, 20.0), 0.1, "#c8d8dc", ["martelado", "impreso"]),
    _a("vidrio_catedral", catedral, "Vidrio catedral", (30.0, 30.0), 0.1, "#b8ccc4", ["catedral", "vidriera",
       "antiguo"]),
    _a("vidrio_estriado", estriado, "Vidrio acanalado", (20.0, 20.0), 0.2, "#c8d8dc", ["acanalado", "estriado",
       "reeded"]),
    _a("vidrio_gotas", gotas, "Gotas en el cristal", (20.0, 20.0), 0.15, "#b0c0c8", ["gotas", "lluvia",
       "ventana mojada"]),
    _a("vidrio_vaho", vaho, "Cristal empañado", (40.0, 40.0), 0.01, "#c8d0d4", ["vaho", "empañad",
       "condensacion"]),
    _a("vidrio_polvo", polvo, "Cristal con polvo", (60.0, 60.0), 0.002, "#b8c0c4", ["polvo", "cristal sucio"]),
    _a("vidrio_huellas", huellas, "Huellas en el cristal", (20.0, 20.0), 0.002, "#b8c0c4", ["huellas",
       "pantalla", "dactilar"]),
    _a("vidrio_rayado", rayado, "Cristal rayado", (20.0, 20.0), 0.002, "#b8c0c4", ["rayado", "arañado"]),
    _a("vidrio_roto", roto, "Cristal laminado roto", (60.0, 60.0), 0.05, "#b8c4c8", ["roto", "parabrisas",
       "impacto"]),
    _a("agua_ondas", agua_ondas, "Agua con ondas", (200.0, 200.0), 3.0, "#3a5a6a", ["agua", "lago", "mar",
       "piscina"], familia=A),
    _a("agua_lluvia", agua_lluvia, "Charco con lluvia", (40.0, 40.0), 0.2, "#4a5458", ["charco", "lluvia"],
       familia=A),
    _a("agua_corriente", agua_corriente, "Agua corriente", (100.0, 100.0), 2.0, "#3e5a58", ["rio", "corriente",
       "canal"], familia=A),
    _a("espuma_mar", espuma, "Espuma de mar", (20.0, 20.0), 0.4, "#e8ecec", ["espuma", "ola"], rug=0.4,
       familia=A, sucia=0.5),
    _a("espuma_jabon", espuma, "Espuma de jabón", (10.0, 10.0), 0.3, "#f2f4f6", ["jabon", "burbujas", "baño"],
       rug=0.2, familia=A, tam=0.25, semilla=21211),
    _a("ambar", ambar, "Ámbar / resina", (10.0, 10.0), 0.01, "#c08030", ["ambar", "resina", "epoxi"], rug=0.08),
    _a("escarcha", escarcha, "Escarcha en el cristal", (20.0, 20.0), 0.02, "#c8d4dc", ["escarcha", "helad",
       "hielo"], rug=0.3),
]
