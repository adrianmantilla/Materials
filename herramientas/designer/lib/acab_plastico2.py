"""Acabados de plástico y goma (segundo lote): suelos de caucho, espumas, laminados, resinas, fibra de
vidrio, arcilla de modelar y masilla."""

import numpy as np

from acab_plastico import remolinos
from acab_terreno import esparcir
from superficie import (celdas, estirado, gris, hoyuelos, manchas_fractales, rayas, rejilla, ruido_cm,
                        salpicado, suave)


def _reticula(forma, cx, cy, paso, desfase=0.5):
    """Coordenadas locales (−0,5..0,5) dentro de una red de celdas con filas desplazadas."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px = tw / max(1, round(tw / paso))
    py = th / max(1, round(th / paso))
    fila = np.floor(y / py)
    u = ((x / px + desfase * (fila % 2)) % 1.0) - 0.5
    v = ((y / py) % 1.0) - 0.5
    return u, v


def neumatico(forma, cx, cy):
    """Goma de neumático: negra mate, con microgrietas, pelitos de moldeo y algún roce brillante."""
    grano = ruido_cm(forma, cx, cy, 0.015, 25001, octavas=2) - 0.5
    pelo = rayas(forma, cx, cy, 120, 0.4, 0.01, 25002)
    roce = suave(ruido_cm(forma, cx, cy, 2.0, 25003, octavas=3), 0.65, 0.8)
    color = gris(0.5 + 0.04 * grano + 0.05 * roce)
    return color, 0.5 + 0.05 * grano - 0.2 * roce, 0.5 + 0.3 * grano + 0.2 * pelo


def caucho_reciclado(forma, cx, cy):
    """Suelo de caucho reciclado (parques): gránulos negros con motas de colores (EPDM)."""
    ids, dist, valor = celdas(forma, cx, cy, 0.3, 25101, temblor=1.0, pesos=0.7)
    hueco = 1 - suave(dist, 0.0, 0.03)
    rng = np.random.default_rng(25102)
    pal = np.array([[0.5, 0.5, 0.5], [0.85, 0.30, 0.25], [0.30, 0.55, 0.85], [0.40, 0.75, 0.35]])
    tipo = rng.choice(len(pal), ids.max() + 1, p=[0.82, 0.06, 0.06, 0.06])[ids]
    color = pal[tipo] * (0.9 + 0.2 * valor[..., None]) * (1 - 0.5 * hueco[..., None])
    return color, 0.5 + 0.1 * hueco, 0.5 + 0.1 * (valor - 0.5) - 0.4 * hueco


def suelo_tacos(forma, cx, cy, paso=3.0):
    """Suelo de caucho de tacos redondos (andenes, gimnasios)."""
    u, v = _reticula(forma, cx, cy, paso, desfase=0.0)
    d = np.hypot(u, v)
    taco = suave(0.3 - d, 0.0, 0.03)
    grano = ruido_cm(forma, cx, cy, 0.02, 25201, octavas=2) - 0.5
    sucio = manchas_fractales(forma, cx, cy, 8.0, 25202, 0.2)
    color = gris(0.5 + 0.03 * grano - 0.06 * sucio * (1 - taco))
    return color, 0.5 + 0.05 * grano - 0.1 * taco, 0.25 + 0.6 * taco + 0.1 * grano


def burbuja(forma, cx, cy, paso=1.0):
    """Plástico de burbujas: cúpulas en red hexagonal con el plano arrugado entre ellas."""
    u, v = _reticula(forma, cx, cy, paso)
    d = np.hypot(u, v * 1.15)
    cupula = np.sqrt(np.clip(1 - (d / 0.42) ** 2, 0, 1))
    arruga = ruido_cm(forma, cx, cy, 0.3, 25301, octavas=2) - 0.5
    color = gris(0.5 + 0.03 * cupula)
    return color, 0.5 - 0.05 * cupula + 0.05 * arruga, 0.1 + 0.8 * cupula + 0.05 * arruga


def porexpan(forma, cx, cy):
    """Poliestireno expandido (porexpán): bolitas soldadas de 3-5 mm, mate y blanco."""
    _, dist, valor = celdas(forma, cx, cy, 0.4, 25401, temblor=1.0, pesos=0.4)
    bola = np.sqrt(suave(dist, 0.0, 0.18))
    hueco = 1 - suave(dist, 0.0, 0.02)
    color = gris(0.5 + 0.03 * (valor - 0.5) - 0.12 * hueco)
    return color, 0.5 + 0.05 * hueco, 0.3 + 0.5 * bola - 0.3 * hueco


def espuma_pu(forma, cx, cy):
    """Espuma de poliuretano (gomaespuma): celdas abiertas, huecos oscuros entre filamentos."""
    _, dist, _ = celdas(forma, cx, cy, 0.08, 25501, temblor=1.0, pesos=0.6)
    poro = suave(dist, 0.006, 0.03)
    color = gris(0.5 + 0.05 * (1 - poro) - 0.25 * poro)
    return color, 0.5 + 0.1 * poro, 0.6 - 0.5 * poro


def melamina(forma, cx, cy):
    """Melamina: lisa, satinada, con una textura de piel muy fina y algún golpe."""
    piel = ruido_cm(forma, cx, cy, 0.04, 25601, octavas=2) - 0.5
    golpe = salpicado(forma, cx, cy, 0.2, 25602, 0.004, borde=0.1)
    color = gris(0.5 + 0.01 * piel + 0.06 * golpe)
    return color, 0.5 + 0.04 * piel + 0.2 * golpe, 0.5 + 0.3 * piel - 0.4 * golpe


def moteado(forma, cx, cy, tam=0.05, densidad=0.15, colores=((0.30, 0.30, 0.30), (0.72, 0.72, 0.70)),
            semilla=25701):
    """Laminado o superficie sólida moteada (fórmica, corian): motas de dos tonos sobre fondo liso."""
    color = gris(np.full(forma, 0.5) + 0.02 * (ruido_cm(forma, cx, cy, 1.0, semilla, octavas=3) - 0.5))
    for k, c in enumerate(colores):
        m = salpicado(forma, cx, cy, tam, semilla + 1 + k, densidad / len(colores), borde=0.02)
        color = color * (1 - m[..., None]) + np.array(c) * m[..., None]
    fino = ruido_cm(forma, cx, cy, 0.02, semilla + 9) - 0.5
    return color, 0.5 + 0.02 * fino, 0.5 + 0.1 * fino


def escamas_epoxi(forma, cx, cy):
    """Suelo de resina epoxi con escamas (flakes) de colores bajo una capa brillante."""
    def perfil(u, v):
        return np.where((np.abs(u) < 1) & (np.abs(v) < 1) & (np.abs(u) + np.abs(v) < 1.4), 1.0, 0.0)

    alto, ancho = forma
    n = int(ancho * cx * alto * cy * 3.0)
    _, quien, _, _ = esparcir(forma, cx, cy, n, 0.3, 0.25, 25801, perfil)
    rng = np.random.default_rng(25802)
    pal = np.array([[0.62, 0.62, 0.60], [0.25, 0.25, 0.26], [0.50, 0.48, 0.44], [0.72, 0.70, 0.66]])
    tipo = rng.integers(0, len(pal), n + 1)[quien]
    hay = (quien >= 0)[..., None]
    color = np.where(hay, pal[tipo], 0.45)
    piel = ruido_cm(forma, cx, cy, 0.5, 25803, octavas=2) - 0.5
    return color, 0.5 + 0.02 * piel, 0.5 + 0.2 * piel


def reciclado(forma, cx, cy):
    """Plástico reciclado (tableros): manchas y vetas de colores mezclados, como mármol de colores."""
    a = estirado(forma, cx, cy, 2.5, 25901, 3.0, octavas=4)
    b = ruido_cm(forma, cx, cy, 1.5, 25902, octavas=3)
    pal = np.array([[0.65, 0.65, 0.65], [0.85, 0.40, 0.30], [0.35, 0.55, 0.85], [0.95, 0.85, 0.35],
                    [0.30, 0.65, 0.45], [0.25, 0.25, 0.28]])
    idx = np.clip((a * 4 + b * 2).astype(int) % len(pal), 0, len(pal) - 1)
    color = 0.6 * pal[idx] + 0.4 * 0.5
    mota = salpicado(forma, cx, cy, 0.05, 25903, 0.05, borde=0.02)
    color = color * (1 - 0.4 * mota[..., None])
    return color, np.full(forma, 0.5), 0.5 + 0.05 * (b - 0.5)


def esmerilado(forma, cx, cy):
    """Plástico translúcido esmerilado (táper, carpeta): grano mate fino y uniforme."""
    grano = ruido_cm(forma, cx, cy, 0.01, 26001, octavas=2) - 0.5
    return gris(0.5 + 0.02 * grano), 0.5 + 0.04 * grano, 0.5 + 0.35 * grano


def salpicadero(forma, cx, cy):
    """Plástico de salpicadero: grano imitación cuero, uniforme y mate."""
    _, dist, valor = celdas(forma, cx, cy, 0.12, 26101, temblor=1.0, pesos=0.4)
    surco = 1 - suave(dist, 0.0, 0.02)
    cojin = np.sqrt(suave(dist, 0.0, 0.05))
    color = gris(0.5 + 0.02 * (valor - 0.5) - 0.04 * surco)
    return color, 0.5 + 0.06 * surco, 0.3 + 0.4 * cojin - 0.2 * surco


def flujo(forma, cx, cy):
    """Plástico inyectado: líneas de flujo concéntricas desde el punto de inyección y líneas de unión."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    dx = (x - tw / 2 + tw / 2) % tw - tw / 2
    dy = (y - th / 2 + th / 2) % th - th / 2
    d = np.hypot(dx, dy)
    torcer = (ruido_cm(forma, cx, cy, 3.0, 26201, octavas=3) - 0.5) * 2.0
    linea = 0.5 + 0.5 * np.sin(2 * np.pi * (d + torcer) / 0.4)
    union = 1 - suave(np.abs(estirado(forma, cx, cy, 2.0, 26202, 10.0, eje="y") - 0.5), 0.0, 0.01)
    color = gris(0.5 + 0.02 * (linea - 0.5) - 0.03 * union)
    return color, 0.5 + 0.08 * (linea - 0.5) + 0.1 * union, 0.5 + 0.04 * (linea - 0.5) - 0.1 * union


def goma_rombos(forma, cx, cy, paso=1.2):
    """Goma antideslizante de rombos (alfombrilla, escalón): rombos en relieve en red."""
    x, y = rejilla(forma, cx, cy)
    tw, th = forma[1] * cx, forma[0] * cy
    px = tw / max(1, round(tw / paso))
    py = th / max(1, round(th / (paso * 0.6)))
    u = ((x / px) % 1.0) - 0.5
    v = ((y / py) % 1.0) - 0.5
    rombo = suave(0.4 - (np.abs(u) + np.abs(v)), 0.0, 0.05)
    grano = ruido_cm(forma, cx, cy, 0.02, 26301) - 0.5
    return gris(0.5 + 0.03 * grano), 0.5 + 0.05 * grano, 0.2 + 0.6 * rombo + 0.08 * grano


def acrilico(forma, cx, cy):
    """Metacrilato pulido: casi espejo, con remolinos finos de pulido."""
    return remolinos(forma, cx, cy, n=300)


def arcilla(forma, cx, cy):
    """Arcilla de modelar: marcas de espátula, huellas de dedos y grumos, todo mate."""
    espatula = rayas(forma, cx, cy, 60, 2.5, 0.25, 26401, curva=0.3)
    borde = rayas(forma, cx, cy, 60, 2.5, 0.02, 26401, curva=0.3)
    dedo = hoyuelos(forma, cx, cy, 0.8, 26402, 0.12)
    grumo = ruido_cm(forma, cx, cy, 0.15, 26403, octavas=3) - 0.5
    color = gris(0.5 + 0.03 * grumo - 0.04 * dedo)
    altura = 0.5 + 0.25 * grumo - 0.25 * espatula + 0.2 * borde - 0.3 * dedo
    return color, 0.5 - 0.1 * espatula + 0.03 * grumo, altura


def masilla(forma, cx, cy):
    """Masilla lijada: manchas de masilla más clara sobre la imprimación, rayas de lija y poros."""
    parche = manchas_fractales(forma, cx, cy, 6.0, 26501, 0.35, detalle=0.4)
    lija = estirado(forma, cx, cy, 0.01, 26502, 30.0) - 0.5
    lija2 = estirado(forma, cx, cy, 0.01, 26503, 30.0, eje="y") - 0.5
    poro = hoyuelos(forma, cx, cy, 0.04, 26504, 0.03) * parche
    color = gris(0.5 + 0.12 * parche - 0.1 * poro, (1.0, 0.99, 0.96))
    rug = 0.5 + 0.05 * (lija + lija2) + 0.1 * parche
    return color, rug, 0.5 + 0.15 * (lija + lija2) - 0.3 * poro + 0.05 * parche


def fibra_vidrio(forma, cx, cy):
    """Fibra de vidrio (mat de hilos cortados bajo resina): mechones de fibras rectas en todas direcciones."""
    def perfil(u, v):
        return np.where((np.abs(u) < 1) & (np.abs(v) < 1), 1 - np.abs(v), 0.0)

    alto, ancho = forma
    n = int(ancho * cx * alto * cy * 1.2)
    cima, quien, _, _ = esparcir(forma, cx, cy, n, 2.5, 0.06, 26601, perfil, variar=0.3)
    hay = quien >= 0
    tono = np.random.default_rng(26602).uniform(0.9, 1.1, n + 1)[quien]
    color = gris(np.where(hay, 0.55 * tono, 0.45))
    return color, 0.5 + 0.03 * hay, 0.5 + 0.15 * cima


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.4, familia="Plástico y goma", **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


ACABADOS = [
    _a("neumatico", neumatico, "Goma de neumático", (10.0, 10.0), 0.02, "#2a2a2a", ["neumatico", "rueda",
       "caucho"], rug=0.8),
    _a("caucho_reciclado", caucho_reciclado, "Caucho reciclado", (20.0, 20.0), 0.1, "#3a3a3a",
       ["caucho reciclado", "parque infantil", "epdm"], rug=0.9),
    _a("suelo_tacos", suelo_tacos, "Suelo de caucho de tacos", (30.0, 30.0), 0.3, "#3a3c40",
       ["tacos", "anden", "gimnasio", "suelo de caucho"], rug=0.7),
    _a("plastico_burbuja", burbuja, "Plástico de burbujas", (10.0, 10.0), 0.4, "#d8e4e8", ["burbujas",
       "embalaje"], rug=0.15),
    _a("porexpan", porexpan, "Porexpán", (10.0, 10.0), 0.1, "#f0f0ec", ["porexpan", "poliestireno",
       "corcho blanco"], rug=0.9),
    _a("gomaespuma", espuma_pu, "Gomaespuma", (5.0, 5.0), 0.1, "#e0c860", ["gomaespuma", "espuma",
       "esponja", "poliuretano"], rug=0.95),
    _a("melamina", melamina, "Melamina", (40.0, 40.0), 0.005, "#e8e6e0", ["melamina", "mueble", "estanteria"],
       rug=0.35),
    _a("formica_moteada", moteado, "Fórmica moteada", (20.0, 20.0), 0.002, "#c8c0b0", ["formica", "encimera",
       "laminado"], rug=0.3),
    _a("corian", moteado, "Superficie sólida (tipo Corian)", (30.0, 30.0), 0.002, "#e8e6e2",
       ["solid surface", "encimera", "lavabo"], rug=0.2, tam=0.03, densidad=0.08,
       colores=((0.42, 0.42, 0.42), (0.58, 0.56, 0.52)), semilla=25751),
    _a("resina_escamas", escamas_epoxi, "Resina epoxi con escamas", (20.0, 20.0), 0.005, "#9a9a9a",
       ["epoxi", "resina", "garaje", "flakes"], rug=0.15),
    _a("plastico_reciclado", reciclado, "Plástico reciclado", (30.0, 30.0), 0.005, "#9a9a9a", ["reciclado",
       "tablero de plastico"], rug=0.45),
    _a("plastico_esmerilado", esmerilado, "Plástico translúcido esmerilado", (5.0, 5.0), 0.003, "#e0e4e6",
       ["tupper", "translucido", "carpeta"], rug=0.5),
    _a("salpicadero", salpicadero, "Plástico de salpicadero", (6.0, 6.0), 0.02, "#2a2c2e", ["salpicadero",
       "coche", "interior"], rug=0.7),
    _a("plastico_inyectado", flujo, "Plástico inyectado (líneas de flujo)", (20.0, 20.0), 0.003, "#3a6ac0",
       ["inyectado", "juguete", "carcasa"], rug=0.25),
    _a("goma_rombos", goma_rombos, "Goma antideslizante de rombos", (12.0, 12.0), 0.2, "#2a2a2c",
       ["antideslizante", "alfombrilla", "rombos"], rug=0.75),
    _a("metacrilato", acrilico, "Metacrilato pulido", (20.0, 20.0), 0.001, "#e0e8ec", ["metacrilato",
       "acrilico", "plexiglas"], rug=0.05),
    _a("arcilla_modelar", arcilla, "Arcilla de modelar", (15.0, 15.0), 0.3, "#a08070", ["arcilla", "modelar",
       "escultura", "boceto"], rug=0.85, familia="Cerámica"),
    _a("masilla_lijada", masilla, "Masilla lijada", (30.0, 30.0), 0.01, "#9a9a96", ["masilla", "imprimacion",
       "lijad", "maqueta"], rug=0.8),
    _a("fibra_vidrio", fibra_vidrio, "Fibra de vidrio", (20.0, 20.0), 0.02, "#d8d4c0", ["fibra de vidrio",
       "poliester", "barca"], rug=0.3),
]
