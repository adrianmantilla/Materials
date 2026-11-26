"""Acabados orgánicos: piel humana, labios, uñas, dientes, ojo, hueso, hoja, pétalo, concha, escamas."""

import math

import numpy as np

import patrones
from superficie import (celdas, distancia_interior, estirado, gris, grietas, hoyuelos, manchas_fractales,
                        mezclar, rayas, rejilla, ruido_cm, salpicado, suave)


def _diagonal(forma, cx, cy, tam, semilla, factor, angulo):
    """Ruido alargado en una dirección cualquiera: se gira la rejilla (aproximado con dos ejes)."""
    a = estirado(forma, cx, cy, tam, semilla, factor) - 0.5
    b = estirado(forma, cx, cy, tam, semilla + 1, factor, eje="y") - 0.5
    c, s = math.cos(angulo), math.sin(angulo)
    return c * c * a + s * s * b


def piel(forma, cx, cy, poro=0.018, densidad=0.10, arrugas=0.5, rojez=0.5, pecas=0.0, graso=0.0,
         rombo=0.0):
    """Piel humana: poros, microarrugas cruzadas, rojeces y (opcional) pecas o rombos del dorso de la mano."""
    x, y = rejilla(forma, cx, cy)
    poros = hoyuelos(forma, cx, cy, poro, 7101, densidad)
    a1 = estirado(forma, cx, cy, 0.01, 7102, 10.0) - 0.5
    a2 = estirado(forma, cx, cy, 0.01, 7103, 10.0, eje="y") - 0.5
    micro = 1 - suave(np.minimum(np.abs(a1), np.abs(a2)), 0.0, 0.05)
    mancha = ruido_cm(forma, cx, cy, 0.8, 7104, octavas=4) - 0.5
    capilar = ruido_cm(forma, cx, cy, 0.15, 7105, octavas=2) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.004, 7106) - 0.5
    lum = 0.5 + 0.05 * mancha - 0.06 * poros - 0.03 * micro * arrugas + 0.02 * grano
    color = np.dstack([lum * (1 + rojez * (0.10 * mancha + 0.05 * capilar)),
                       lum * (1 - rojez * (0.06 * mancha + 0.03 * capilar)),
                       lum * (1 - rojez * (0.05 * mancha + 0.02 * capilar))])
    altura = 0.55 - 0.35 * poros - 0.12 * micro * arrugas + 0.05 * grano
    if rombo:
        # Dorso de la mano y nudillos: surcos cruzados que forman rombos de ~1-2 mm.
        g1 = np.abs(((x + y) / 0.1875 + 0.4 * (mancha + capilar)) % 1.0 - 0.5)
        g2 = np.abs(((x - y) / 0.15 + 0.4 * capilar) % 1.0 - 0.5)
        surco = 1 - suave(np.minimum(g1, g2), 0.0, 0.08)
        altura = altura - 0.25 * rombo * surco
        color = color * (1 - 0.06 * rombo * surco[..., None])
    if pecas:
        p = salpicado(forma, cx, cy, 0.12, 7107, 0.08 * pecas, borde=0.06)
        color = color * (1 - p[..., None] * np.array([0.22, 0.32, 0.40]))
    rug = 0.5 + 0.08 * poros + 0.05 * micro * arrugas - 0.1 * graso * (0.5 + mancha) + 0.02 * grano
    return color, rug, altura


def piel_vieja(forma, cx, cy):
    """Piel envejecida: arrugas largas, manchas de sol y poros más abiertos."""
    color, rug, altura = piel(forma, cx, cy, poro=0.025, densidad=0.12, arrugas=1.0, rojez=0.4)
    surco = 1 - suave(np.abs(estirado(forma, cx, cy, 0.12, 7201, 6.0, octavas=2) - 0.5), 0.0, 0.025)
    sol = salpicado(forma, cx, cy, 0.35, 7202, 0.06, borde=0.08)
    color = color * (1 - surco[..., None] * 0.08) * (1 - sol[..., None] * np.array([0.12, 0.22, 0.30]))
    return color, rug + 0.05 * surco, altura - 0.3 * surco


def labios(forma, cx, cy):
    """Labios: surcos verticales finos, piel húmeda y algo de color irregular."""
    surco = 1 - suave(np.abs(estirado(forma, cx, cy, 0.05, 7301, 8.0, eje="y", octavas=2) - 0.5), 0, 0.04)
    mancha = ruido_cm(forma, cx, cy, 0.4, 7302, octavas=3) - 0.5
    seco = manchas_fractales(forma, cx, cy, 0.6, 7303, 0.2)
    lum = 0.5 + 0.06 * mancha - 0.035 * surco
    color = np.dstack([lum * (1 + 0.06 * mancha), lum * (1 - 0.04 * mancha), lum])
    rug = 0.5 - 0.1 + 0.2 * seco + 0.03 * surco
    return color, rug, 0.55 - 0.2 * surco + 0.1 * seco


def una(forma, cx, cy):
    """Uña: estrías longitudinales muy finas y brillo irregular."""
    estria = estirado(forma, cx, cy, 0.012, 7401, 30.0, eje="y", octavas=2) - 0.5
    velo = ruido_cm(forma, cx, cy, 0.4, 7402, octavas=3) - 0.5
    blanco = salpicado(forma, cx, cy, 0.08, 7403, 0.01, borde=0.06)
    color = gris(0.5 + 0.012 * estria + 0.03 * velo + 0.15 * blanco)
    rug = 0.5 + 0.05 * velo + 0.015 * estria
    return color, rug, 0.5 + 0.15 * estria


def diente(forma, cx, cy):
    """Esmalte dental: liso, con líneas de crecimiento horizontales muy suaves y algo de tono."""
    lineas = estirado(forma, cx, cy, 0.02, 7501, 25.0, octavas=2) - 0.5
    tono = ruido_cm(forma, cx, cy, 0.4, 7502, octavas=3) - 0.5
    grieta = rayas(forma, cx, cy, 6, 1.0, 0.003, 7503, angulo=math.pi / 2, dispersion=0.4)
    color = (np.dstack([0.5 + 0.04 * tono, 0.5 + 0.03 * tono, 0.5 + 0.01 * tono]) + 0.006 * lineas[..., None]
             - 0.04 * grieta[..., None])
    rug = 0.5 + 0.008 * lineas + 0.05 * grieta
    return color, rug, 0.5 + 0.06 * lineas


def esclerotica(forma, cx, cy):
    """Blanco del ojo: venitas rojas finas y ramificadas, húmedo."""
    venas = rayas(forma, cx, cy, 22, 0.5, 0.0035, 7601, curva=0.25)
    venas2 = rayas(forma, cx, cy, 8, 1.4, 0.006, 7602, curva=0.2)
    v = np.maximum(venas * 0.7, venas2)
    tono = ruido_cm(forma, cx, cy, 0.5, 7603, octavas=3) - 0.5
    base = gris(0.5 + 0.03 * tono, (1.0, 0.98, 0.95))
    color = mezclar(base, (0.42, 0.06, 0.06), 0.8 * v)
    rug = 0.5 + 0.0 * tono
    return color, rug, 0.5 + 0.1 * v


def hueso(forma, cx, cy):
    """Hueso: poros pequeños, fibras alargadas y manchas amarillentas."""
    fibra = estirado(forma, cx, cy, 0.03, 7701, 10.0, octavas=2) - 0.5
    poros = hoyuelos(forma, cx, cy, 0.03, 7702, 0.05)
    mancha = ruido_cm(forma, cx, cy, 1.0, 7703, octavas=3) - 0.5
    color = gris(0.5 + 0.05 * fibra + 0.06 * mancha - 0.12 * poros, (1.0, 0.97, 0.9))
    rug = 0.5 + 0.06 * poros + 0.03 * fibra
    return color, rug, 0.5 + 0.25 * fibra - 0.4 * poros


def cera(forma, cx, cy, huellas=0.0):
    """Cera, jabón o plastilina: superficie blanda con abolladuras y (opcional) huellas de dedos."""
    abolla = ruido_cm(forma, cx, cy, 1.2, 7801, octavas=3) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.01, 7802) - 0.5
    r = rayas(forma, cx, cy, 8, 1.5, 0.008, 7803, curva=0.15) * 0.5
    color = gris(0.5 + 0.03 * abolla)
    altura = 0.5 + 0.35 * abolla + 0.05 * grano - 0.15 * r
    rug = 0.5 + 0.04 * grano + 0.1 * r
    if huellas:
        x, y = rejilla(forma, cx, cy)
        dedo = salpicado(forma, cx, cy, 0.9, 7804, 0.25 * huellas, borde=0.1)
        crestas = 0.5 + 0.5 * np.sin(2 * np.pi * (np.hypot(x % 3.0 - 1.5, (y % 3.0 - 1.5) * 1.3)
                                                    + 0.6 * abolla) / 0.045)
        altura = altura - 0.25 * dedo + 0.1 * dedo * crestas
        rug = rug + 0.05 * dedo
    return color, rug, altura


def hoja(forma, cx, cy, celda=1.2):
    """Hoja verde de cerca: nervios ramificados en relieve, células y brillo de cutícula."""
    nervio = grietas(forma, cx, cy, celda, 7901, 0.03)
    fino = grietas(forma, cx, cy, celda / 3.5, 7902, 0.012)
    celula = ruido_cm(forma, cx, cy, 0.01, 7903) - 0.5
    mancha = ruido_cm(forma, cx, cy, 1.5, 7904, octavas=3) - 0.5
    lum = 0.5 + 0.06 * mancha + 0.10 * nervio + 0.05 * fino + 0.02 * celula
    color = np.dstack([lum * (1 + 0.05 * nervio), lum * (1 + 0.02 * mancha), lum * (1 - 0.05 * nervio)])
    rug = 0.5 + 0.05 * nervio + 0.03 * celula + 0.04 * mancha
    return color, rug, 0.45 + 0.3 * nervio + 0.15 * fino + 0.08 * celula


def petalo(forma, cx, cy):
    """Pétalo: venas finas paralelas, células aterciopeladas y color más intenso en las venas."""
    vena = 1 - suave(np.abs(estirado(forma, cx, cy, 0.04, 8001, 12.0, eje="y") - 0.5), 0.0, 0.05)
    celula = ruido_cm(forma, cx, cy, 0.006, 8002) - 0.5
    mancha = ruido_cm(forma, cx, cy, 0.6, 8003, octavas=3) - 0.5
    color = gris(0.5 + 0.06 * mancha - 0.06 * vena + 0.03 * celula)
    rug = 0.5 + 0.03 * celula
    return color, rug, 0.5 + 0.2 * vena + 0.15 * celula


def concha(forma, cx, cy):
    """Concha marina: costillas radiales, líneas de crecimiento y bandas de color."""
    x, y = rejilla(forma, cx, cy)
    th = forma[0] * cy
    tw = forma[1] * cx
    onda = ruido_cm(forma, cx, cy, 2.0, 8101, octavas=2) - 0.5
    crecimiento = estirado(forma, cx, cy, 0.05, 8102, 15.0, octavas=2) - 0.5
    k = max(1, round(tw / 0.6))
    costilla = 0.5 + 0.5 * np.cos(2 * np.pi * (x * k / tw + 0.3 * onda))
    kb = max(1, round(th / 1.5))
    banda = 0.5 + 0.5 * np.sin(2 * np.pi * (y * kb / th + 0.8 * onda))
    lum = 0.5 + 0.10 * (banda - 0.5) + 0.04 * costilla + 0.04 * crecimiento
    color = np.dstack([lum * (1 + 0.06 * (banda - 0.5)), lum, lum * (1 - 0.08 * (banda - 0.5))])
    rug = 0.5 + 0.04 * crecimiento
    return color, rug, 0.3 + 0.4 * costilla + 0.25 * crecimiento


def quitina(forma, cx, cy):
    """Caparazón de insecto: punteado fino, reflejos que cambian de tono y brillo duro."""
    punto = hoyuelos(forma, cx, cy, 0.02, 8201, 0.06)
    reflejo = ruido_cm(forma, cx, cy, 0.8, 8202, octavas=3) - 0.5
    color = np.dstack([0.5 + 0.06 * reflejo, 0.5 - 0.02 * reflejo, 0.5 + 0.08 * reflejo]) * (
        1 - 0.15 * punto[..., None])
    rug = 0.5 + 0.08 * punto
    return color, rug, 0.55 - 0.4 * punto


def coral(forma, cx, cy, tam=0.35):
    """Coral: pólipos (copitas con borde) muy juntos."""
    _, dist, valor = celdas(forma, cx, cy, tam, 8301, temblor=0.9)
    copa = suave(dist, 0.0, tam * 0.1) * (1 - suave(dist, tam * 0.15, tam * 0.35))
    fondo = 1 - suave(dist, tam * 0.15, tam * 0.4)
    grano = ruido_cm(forma, cx, cy, 0.02, 8302) - 0.5
    color = gris(0.5 + 0.05 * (valor - 0.5) - 0.08 * (1 - fondo) + 0.03 * grano)
    rug = 0.5 + 0.04 * grano
    return color, rug, 0.35 + 0.35 * copa + 0.2 * fondo + 0.1 * grano


def escamas(forma, cx, cy, radio=0.35):
    """Escamas de reptil: escamas abombadas en tresbolillo con borde oscuro."""
    x, y = rejilla(forma, cx, cy)
    ids = patrones.red_voronoi(x, y, (math.sqrt(3) * radio, 0.0), (math.sqrt(3) * radio / 2, 1.5 * radio))
    borde = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
    dist = distancia_interior(~borde, cx, cy, radio)
    cupula = np.sqrt(suave(dist, 0.0, radio * 0.8))
    from fabricar import etiquetar
    lab, n = etiquetar(dist > 0)  # numeración que respeta la repetición
    valor = np.random.default_rng(8401).uniform(0, 1, max(n, 1))[np.maximum(lab, 0)]
    grano = ruido_cm(forma, cx, cy, 0.01, 8402) - 0.5
    patron = ruido_cm(forma, cx, cy, 2.0, 8403, octavas=2) - 0.5
    color = gris(0.5 + 0.10 * (valor - 0.5) + 0.14 * np.tanh(4 * patron) - 0.12 * (1 - cupula) + 0.02 * grano)
    rug = 0.5 - 0.06 * cupula + 0.03 * grano
    return color, rug, 0.2 + 0.7 * cupula + 0.05 * grano


def piel_elefante(forma, cx, cy):
    """Piel gruesa de animal (elefante, rinoceronte): red de surcos profundos y arrugas."""
    surco = grietas(forma, cx, cy, 0.8, 8501, 0.06)
    fino = grietas(forma, cx, cy, 0.25, 8502, 0.02)
    bulto = ruido_cm(forma, cx, cy, 0.4, 8503, octavas=2) - 0.5
    color = gris(0.5 - 0.12 * surco - 0.05 * fino + 0.05 * bulto)
    rug = 0.5 + 0.05 * surco
    return color, rug, 0.6 - 0.45 * surco - 0.15 * fino + 0.15 * bulto


def _a(id_, funcion, nombre, familia, tile, relieve, muestra, para, rug=0.5, **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


H, O = "Cuerpo humano", "Orgánico"
ACABADOS = [
    _a("piel_cara", piel, "Piel de la cara", H, (3.0, 3.0), 0.02, "#d9a587", ["piel clara", "piel media", "piel",
       "cara"], rug=0.45),
    _a("piel_nariz", piel, "Piel de nariz y frente (poro abierto)", H, (3.0, 3.0), 0.025, "#c98f6f",
       ["nariz", "frente", "piel"], rug=0.4, poro=0.028, densidad=0.14, graso=1.0),
    _a("piel_pecas", piel, "Piel con pecas", H, (4.0, 4.0), 0.02, "#e2b296", ["pecas", "piel clara"], rug=0.45,
       pecas=1.0),
    _a("piel_cuerpo", piel, "Piel del cuerpo", H, (4.0, 4.0), 0.015, "#b57a58", ["piel media", "brazo", "cuerpo"],
       rug=0.5, poro=0.012, densidad=0.05, arrugas=0.3, rojez=0.3),
    _a("piel_mano", piel, "Piel del dorso de la mano", H, (3.0, 3.0), 0.03, "#8d5a3c", ["mano", "piel oscura",
       "nudillo"], rug=0.5, rombo=1.0, densidad=0.06),
    _a("piel_envejecida", piel_vieja, "Piel envejecida", H, (4.0, 4.0), 0.04, "#cf9c80", ["piel vieja",
       "anciano", "arruga"], rug=0.5),
    _a("labios", labios, "Labios", H, (2.0, 2.0), 0.02, "#b5615e", ["labio", "boca"], rug=0.35),
    _a("una", una, "Uña", H, (1.5, 1.5), 0.005, "#e3b3a6", ["uña", "una", "garra"], rug=0.2),
    _a("diente", diente, "Esmalte dental", H, (1.0, 1.0), 0.003, "#ece4d0", ["diente", "esmalte", "colmillo"],
       rug=0.2),
    _a("esclerotica", esclerotica, "Blanco del ojo", H, (2.0, 2.0), 0.002, "#efe9e2", ["ojo", "esclerotica"],
       rug=0.1),
    _a("hueso", hueso, "Hueso", O, (4.0, 4.0), 0.03, "#ddd2b8", ["hueso", "craneo", "marfil"], rug=0.55),
    _a("cera", cera, "Cera de vela", O, (6.0, 6.0), 0.03, "#efe5cf", ["cera", "vela", "jabon"], rug=0.4),
    _a("plastilina", cera, "Plastilina con huellas", O, (6.0, 6.0), 0.06, "#4f86c6", ["plastilina", "arcilla de modelar",
       "clay"], rug=0.6, huellas=1.0),
    _a("hoja_verde", hoja, "Hoja verde", O, (6.0, 6.0), 0.03, "#4b7a32", ["hoja", "planta", "follaje"], rug=0.45),
    _a("petalo", petalo, "Pétalo", O, (3.0, 3.0), 0.01, "#c83a5a", ["petalo", "flor"], rug=0.6),
    _a("concha", concha, "Concha marina", O, (6.0, 6.0), 0.05, "#e0cdb0", ["concha", "nacar", "almeja"], rug=0.4),
    _a("caparazon", quitina, "Caparazón de insecto", O, (3.0, 3.0), 0.01, "#1d3b2a", ["caparazon", "escarabajo",
       "insecto"], rug=0.2),
    _a("coral", coral, "Coral", O, (10.0, 10.0), 0.15, "#e07a5f", ["coral"], rug=0.7),
    _a("escamas_reptil", escamas, "Escamas de reptil", O, (math.sqrt(3) * 0.35 * 20, 0.35 * 3 * 10), 0.06,
       "#5d6b3a", ["escama", "serpiente", "reptil", "lagarto", "dragon"], rug=0.4),
    _a("piel_elefante", piel_elefante, "Piel gruesa arrugada", O, (10.0, 10.0), 0.2, "#7b746c",
       ["elefante", "rinoceronte", "piel gruesa"], rug=0.8),
]
