"""Acabados de metal (segundo lote): metales nobles, corten, damasco, mecanizados, pátinas y corrosión."""

import numpy as np

from acab_metal import ACERO, COBRE, _rel, cepillado, martele, pulido_rayado, satinado
from superficie import (celdas, estirado, gris, hoyuelos, manchas_fractales, rayas, rejilla, ruido_cm,
                        salpicado, suave)


def corten(forma, cx, cy):
    """Acero corten: pátina de óxido estable, densa y aterciopelada, con churretes y zonas oscuras."""
    tono = ruido_cm(forma, cx, cy, 8.0, 22001, octavas=5) - 0.5
    chorro = estirado(forma, cx, cy, 1.0, 22002, 15.0, eje="y", octavas=3) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.03, 22003, octavas=2) - 0.5
    lum = 0.5 + 0.12 * tono - 0.1 * chorro + 0.06 * grano
    color = gris(lum) * np.array([1.0, 0.95, 0.9])
    return color, 0.5 + 0.05 * grano + 0.05 * tono, 0.5 + 0.3 * grano, np.zeros(forma)


def anodizado(forma, cx, cy):
    """Aluminio anodizado de color: satinado fino con un leve velado del baño."""
    return satinado(forma, cx, cy)


def pulido(forma, cx, cy):
    """Metal noble pulido a espejo: arañazos finísimos de uso, en remolinos de limpieza."""
    return pulido_rayado(forma, cx, cy, n=400, largo=3.0, ancho=0.004, fuerza=0.2)


def bronce(forma, cx, cy):
    """Bronce patinado (estatua): marrón oscuro, verdín en los huecos y brillo donde se toca."""
    bulto = ruido_cm(forma, cx, cy, 1.2, 22101, octavas=5)
    grano = ruido_cm(forma, cx, cy, 0.04, 22102, octavas=2) - 0.5
    hueco = (1 - suave(bulto, 0.25, 0.42)) * suave(ruido_cm(forma, cx, cy, 6.0, 22103, octavas=3), 0.4, 0.7)
    alto = suave(bulto, 0.68, 0.85)
    marron = _rel((0.20, 0.12, 0.07), COBRE)
    verde = _rel((0.25, 0.45, 0.35), COBRE)
    color = np.ones(forma + (3,)) * marron
    color = color * (1 - hueco[..., None]) + verde * hueco[..., None]
    color = color * (1 - alto[..., None]) + gris(np.full(forma, 0.48)) * alto[..., None]
    color = color * (1 + 0.2 * grano[..., None])
    metal = np.clip(0.4 + 0.6 * alto - 0.4 * hueco, 0, 1)
    rug = 0.5 + 0.15 * hueco - 0.2 * alto + 0.05 * grano
    return color, rug, 0.5 + 0.4 * (bulto - 0.5) + 0.1 * grano, metal


def damasco(forma, cx, cy):
    """Acero de Damasco: capas plegadas que se ven como bandas onduladas claras y oscuras."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    giro = ruido_cm(forma, cx, cy, 2.0, 22201, octavas=4) - 0.5
    paso = th / max(1, round(th / 0.25))
    capa = 0.5 + 0.5 * np.sin(2 * np.pi * (y + 1.5 * giro) / paso)
    capa = suave(capa, 0.3, 0.7)
    color = gris(0.38 + 0.2 * capa)
    return color, 0.5 + 0.08 * (1 - capa), 0.5 + 0.1 * capa


def granallado(forma, cx, cy):
    """Acero granallado (chorro de bolas): hoyitos finísimos por todas partes, mate uniforme."""
    _, dist, valor = celdas(forma, cx, cy, 0.04, 22301, temblor=1.0)
    hoyo = 1 - suave(dist, 0.0, 0.02)
    color = gris(0.5 + 0.03 * (valor - 0.5))
    return color, 0.5 + 0.1 * (valor - 0.5), 0.5 + 0.4 * (0.5 - hoyo)


def termocoloreado(forma, cx, cy):
    """Metal con colores de revenido (soldadura, escape): bandas pajizo, bronce, azul, alrededor de manchas."""
    calor = ruido_cm(forma, cx, cy, 6.0, 22401, octavas=4)
    t = np.clip((calor - 0.35) * 2.2, 0, 1)
    paleta = np.array([[0.5, 0.5, 0.5], [0.62, 0.52, 0.30], [0.55, 0.35, 0.25], [0.40, 0.25, 0.45],
                       [0.25, 0.35, 0.60], [0.45, 0.50, 0.55]])
    pos = t * (len(paleta) - 1)
    i = np.clip(np.floor(pos).astype(int), 0, len(paleta) - 2)
    f = (pos - i)[..., None]
    color = paleta[i] * (1 - f) + paleta[i + 1] * f
    grano = ruido_cm(forma, cx, cy, 0.012, 22402, octavas=2) - 0.5
    return color, 0.5 + 0.06 * grano, 0.5 + 0.2 * grano


def zinc(forma, cx, cy):
    """Zinc patinado (cubierta de titanio-zinc): gris azulado mate con vetas de lluvia."""
    vela = estirado(forma, cx, cy, 2.0, 22501, 20.0, eje="y", octavas=3) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.02, 22502, octavas=2) - 0.5
    blanco = manchas_fractales(forma, cx, cy, 10.0, 22503, 0.08)
    color = gris(0.5 + 0.06 * vela + 0.03 * grano + 0.12 * blanco, (0.98, 1.0, 1.03))
    return color, 0.5 + 0.06 * vela + 0.2 * blanco, 0.5 + 0.2 * grano, np.full(forma, 0.6) - 0.4 * blanco


def martillado(forma, cx, cy):
    """Cobre o latón martillado a mano: golpes de bola de tamaño variable, brillos en los bordes."""
    color, rug, altura = martele(forma, cx, cy, tam=1.4)
    grano = ruido_cm(forma, cx, cy, 0.5, 22601, octavas=3) - 0.5
    return color * (1 + 0.08 * grano[..., None]), rug + 0.04 * grano, altura


def laton(forma, cx, cy):
    """Latón pulido con manchas de deslustre (más oscuras y rojizas) y huellas."""
    color, rug, altura = pulido_rayado(forma, cx, cy, n=250, largo=2.5, ancho=0.004, fuerza=0.15)
    mancha = manchas_fractales(forma, cx, cy, 3.0, 22701, 0.25, detalle=0.5)
    color = color * (1 - 0.3 * mancha[..., None]) * np.where(mancha[..., None] > 0.5, [1.02, 0.95, 0.9], 1.0)
    return color, rug + 0.15 * mancha, altura


def aluminio_fundido(forma, cx, cy):
    """Aluminio fundido: piel granulada de molde de arena, gris claro, con alguna burbuja."""
    grano = ruido_cm(forma, cx, cy, 0.03, 22801, octavas=2) - 0.5
    burbuja = hoyuelos(forma, cx, cy, 0.06, 22802, 0.02)
    mancha = ruido_cm(forma, cx, cy, 4.0, 22803, octavas=3) - 0.5
    color = gris(0.5 + 0.06 * grano + 0.05 * mancha - 0.15 * burbuja)
    return color, 0.5 + 0.1 * grano + 0.1 * burbuja, 0.5 + 0.4 * grano - 0.4 * burbuja


def pavonado(forma, cx, cy):
    """Acero pavonado: negro azulado satinado, desgastado hacia el gris en los cantos y roces."""
    color, rug, altura = satinado(forma, cx, cy)
    roce = suave(ruido_cm(forma, cx, cy, 2.0, 22901, octavas=4), 0.68, 0.8)
    color = color * (1 + 0.6 * roce[..., None])
    return color, rug - 0.05 * roce, altura


def cromo(forma, cx, cy):
    """Cromo pulido: espejo casi perfecto con muy pocos arañazos y manchas de cal."""
    r = rayas(forma, cx, cy, 60, 2.0, 0.003, 23001)
    cal = salpicado(forma, cx, cy, 0.15, 23002, 0.02, borde=0.08)
    color = gris(0.5 - 0.02 * r + 0.03 * cal)
    return color, 0.5 + 0.2 * r + 0.4 * cal, 0.5 - 0.1 * r


def perlado(forma, cx, cy, paso=0.6):
    """Perlado (perlage, «ojo de perdiz»): círculos cepillados solapados en filas, típico de relojería."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px = tw / max(1, round(tw / paso))
    py = th / max(1, round(th / paso))
    nx, ny = int(round(tw / px)), int(round(th / py))
    estria = np.zeros(forma)
    capa = np.full(forma, -1.0)
    for j in range(ny):
        for i in range(nx):
            cxp, cyp = (i + 0.5 * (j % 2)) * px, j * py
            dx = (x - cxp + tw / 2) % tw - tw / 2
            dy = (y - cyp + th / 2) % th - th / 2
            d = np.hypot(dx, dy)
            dentro = d < 0.6 * paso * 1.2
            orden = j * nx + i
            poner = dentro & (orden > capa)
            ang = np.arctan2(dy, dx)
            e = 0.5 + 0.5 * np.sin(ang * 40 + d * 80)
            estria = np.where(poner, e * (0.6 + 0.4 * d / (0.72 * paso)), estria)
            capa = np.where(poner, orden, capa)
    color = gris(0.5 + 0.06 * (estria - 0.5))
    return color, 0.5 + 0.15 * (estria - 0.5), 0.5 + 0.2 * (estria - 0.5)


def fresado(forma, cx, cy, paso=1.5, avance=0.05):
    """Superficie fresada (planeado): arcos de la fresa, uno por avance, en pasadas paralelas."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    p = th / max(1, round(th / paso))
    f = tw / max(1, round(tw / avance))
    yc = (np.floor(y / p) + 0.5) * p
    radio = 0.6 * p
    arco = radio - np.sqrt(np.clip(radio ** 2 - (y - yc) ** 2, 0, None))
    marca = 0.5 + 0.5 * np.sin(2 * np.pi * (x + arco) / f)
    borde = np.exp(-((np.abs(y - yc) - p / 2) / (0.03 * p)) ** 2)
    color = gris(0.5 + 0.04 * (marca - 0.5) - 0.03 * borde)
    return color, 0.5 + 0.18 * (marca - 0.5), 0.5 + 0.25 * (marca - 0.5) - 0.1 * borde


def picado(forma, cx, cy):
    """Hierro picado por la corrosión: crateres profundos, óxido en el fondo y metal gris arriba."""
    crater = hoyuelos(forma, cx, cy, 0.6, 23201, 0.3)
    fino = hoyuelos(forma, cx, cy, 0.12, 23202, 0.2)
    grano = ruido_cm(forma, cx, cy, 0.03, 23203, octavas=2) - 0.5
    oxido = suave(crater + 0.5 * fino, 0.2, 0.6)
    rojo = _rel((0.30, 0.13, 0.06), ACERO)
    color = gris(np.full(forma, 0.45) + 0.04 * grano)
    color = color * (1 - oxido[..., None]) + rojo * oxido[..., None]
    return color, 0.6 + 0.3 * oxido + 0.05 * grano, 0.55 - 0.5 * crater - 0.2 * fino + 0.1 * grano, 1 - oxido


def oxido_rayado(forma, cx, cy):
    """Chapa oxidada con arañazos y roces que dejan ver el metal brillante."""
    roce = np.maximum(rayas(forma, cx, cy, 300, 6.0, 0.03, 23301, curva=0.1),
                      rayas(forma, cx, cy, 80, 3.0, 0.15, 23302, angulo=0.2, dispersion=0.4))
    tono = ruido_cm(forma, cx, cy, 3.0, 23303, octavas=4) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.03, 23304, octavas=2) - 0.5
    rojo = _rel((0.30, 0.13, 0.06), ACERO) * (1 + 0.5 * tono[..., None] + 0.2 * grano[..., None])
    limpio = suave(roce, 0.2, 0.5)
    color = rojo * (1 - limpio[..., None]) + gris(np.full(forma, 0.5)) * limpio[..., None]
    return color, 0.85 - 0.5 * limpio + 0.05 * grano, 0.5 + 0.2 * grano - 0.15 * limpio, limpio


def estano(forma, cx, cy):
    """Estaño / peltre: gris apagado, satinado, con abolladuras suaves y arañazos de uso."""
    abolla = hoyuelos(forma, cx, cy, 1.5, 23401, 0.15)
    color, rug, altura = cepillado(forma, cx, cy, tam=0.02, fuerza=0.06, rayas_n=200)
    return color, rug + 0.1, altura - 0.3 * abolla


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.3, metal=1.0, **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia="Metal", tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=metal, recomendado_para=para)


ACABADOS = [
    _a("acero_corten", corten, "Acero corten", (100.0, 100.0), 0.05, "#7a3e22", ["corten", "acero patinable"],
       rug=0.8, metal=0.0),
    _a("aluminio_anodizado", anodizado, "Aluminio anodizado de color", (10.0, 10.0), 0.003, "#3a6ea8",
       ["anodizado", "aluminio de color"], rug=0.35),
    _a("oro_pulido", pulido, "Oro pulido", (10.0, 10.0), 0.002, "#ffc65c", ["oro", "dorado", "joya"], rug=0.08),
    _a("oro_cepillado", cepillado, "Oro cepillado", (10.0, 10.0), 0.005, "#f0bc58", ["oro cepillado",
       "dorado mate"], rug=0.3),
    _a("plata_pulida", pulido, "Plata pulida", (10.0, 10.0), 0.002, "#e8e8e6", ["plata", "plateado"], rug=0.08),
    _a("bronce_patinado", bronce, "Bronce patinado", (40.0, 40.0), 0.3, "#c08a5a", ["bronce", "estatua"],
       rug=0.4),
    _a("acero_damasco", damasco, "Acero de Damasco", (10.0, 10.0), 0.005, "#9a9a9c", ["damasco", "cuchillo",
       "katana"], rug=0.25),
    _a("acero_granallado", granallado, "Acero granallado", (5.0, 5.0), 0.004, "#a0a2a4", ["granallado",
       "arenado", "chorreado"], rug=0.55),
    _a("metal_termocoloreado", termocoloreado, "Metal con color de revenido", (20.0, 20.0), 0.002, "#a8a8a8",
       ["revenido", "escape", "soldadura", "titanio"], rug=0.3),
    _a("zinc_patinado", zinc, "Zinc patinado", (100.0, 100.0), 0.01, "#8c939a", ["zinc", "titanio zinc",
       "cubierta"], rug=0.6),
    _a("cobre_martillado", martillado, "Cobre martillado", (20.0, 20.0), 0.15, "#d08a64", ["cobre martillado",
       "cazo"], rug=0.25),
    _a("laton_pulido", laton, "Latón pulido", (15.0, 15.0), 0.002, "#e0b860", ["laton", "pomo", "tirador"],
       rug=0.12),
    _a("aluminio_fundido", aluminio_fundido, "Aluminio fundido", (15.0, 15.0), 0.03, "#b8babc",
       ["aluminio fundido", "carter", "llanta"], rug=0.5),
    _a("acero_pavonado", pavonado, "Acero pavonado", (10.0, 10.0), 0.003, "#3a3e48", ["pavonado", "arma"], rug=0.35),
    _a("cromo_pulido", cromo, "Cromo pulido", (20.0, 20.0), 0.001, "#e0e2e4", ["cromo", "grifo", "espejo"],
       rug=0.03),
    _a("metal_perlado", perlado, "Perlado (relojería)", (6.0, 6.0), 0.002, "#c8c8c6", ["perlado", "perlage",
       "reloj", "mecanizado"], rug=0.2),
    _a("metal_fresado", fresado, "Metal fresado", (15.0, 15.0), 0.003, "#b0b2b4", ["fresado", "mecanizado",
       "aluminio"], rug=0.25),
    _a("hierro_picado", picado, "Hierro picado por la corrosión", (20.0, 20.0), 0.3, "#7a7c7e",
       ["picado", "corrosion", "barco"], rug=0.6),
    _a("oxido_rayado", oxido_rayado, "Óxido con roces", (40.0, 40.0), 0.05, "#8a8c8e", ["oxido rayado",
       "roce", "contenedor"], rug=0.4),
    _a("estano", estano, "Estaño / peltre", (15.0, 15.0), 0.05, "#9a9c9a", ["estaño", "peltre", "jarra"],
       rug=0.4),
]
