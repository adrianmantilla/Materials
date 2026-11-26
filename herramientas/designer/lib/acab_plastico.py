"""Acabados de pinturas, lacas, plásticos, gomas y fibra de carbono."""

import math

import numpy as np

from superficie import (SARGA_2_2, TAFETAN, celdas, estirado, gris, hoyuelos, manchas_fractales, rayas,
                        rejilla, ruido_cm, salpicado, suave, tejido)


def piel_naranja(forma, cx, cy, tam=0.25, fuerza=1.0):
    """Pintura de coche o esmalte: «piel de naranja» muy suave y algo de polvo atrapado."""
    piel = ruido_cm(forma, cx, cy, tam, 3101, octavas=2) - 0.5
    polvo = salpicado(forma, cx, cy, 0.01, 3102, 0.002)
    color = gris(0.5 - 0.03 * polvo)
    rug = 0.5 + 0.02 * piel * fuerza + 0.1 * polvo
    altura = 0.5 + 0.4 * piel * fuerza + 0.3 * polvo
    return color, rug, altura


def metalizada(forma, cx, cy, escama=0.012, brillo=0.25):
    """Pintura metalizada: escamas de aluminio que brillan cada una a su manera bajo el barniz."""
    _, dist, valor = celdas(forma, cx, cy, escama, 3201, temblor=1.0)
    piel = ruido_cm(forma, cx, cy, 0.25, 3202, octavas=2) - 0.5
    destello = suave(valor, 1.0 - brillo, 1.0)
    color = gris(0.5 + 0.10 * (valor - 0.5) + 0.12 * destello)
    rug = 0.5 - 0.08 * destello + 0.04 * (valor - 0.5)
    altura = 0.5 + 0.3 * piel
    return color, rug, altura


def remolinos(forma, cx, cy, n=500):
    """Laca o pintura muy brillante con micro arañazos en remolino (lavados) y polvo."""
    r = rayas(forma, cx, cy, n, 3.0, 0.004, 3301, curva=0.35)
    polvo = salpicado(forma, cx, cy, 0.01, 3302, 0.003)
    velo = ruido_cm(forma, cx, cy, 6.0, 3303, octavas=3) - 0.5
    color = gris(0.5 - 0.02 * r - 0.02 * polvo)
    rug = 0.5 + 0.22 * r + 0.12 * polvo + 0.04 * velo
    altura = 0.5 - 0.15 * r + 0.2 * polvo
    return color, rug, altura


def pintura_polvo(forma, cx, cy):
    """Pintura en polvo (epoxi al horno): textura fina y uniforme, satinada."""
    grano = ruido_cm(forma, cx, cy, 0.04, 3401, octavas=2) - 0.5
    bulto = ruido_cm(forma, cx, cy, 0.15, 3402) - 0.5
    color = gris(0.5 + 0.02 * grano)
    rug = 0.5 + 0.05 * grano
    altura = 0.5 + 0.3 * grano + 0.2 * bulto
    return color, rug, altura


def pincelada(forma, cx, cy, ancho=3.0):
    """Pintura o barniz dado a brocha: surcos de las cerdas en tramos y algún grumo."""
    x, y = rejilla(forma, cx, cy)
    tramo = ruido_cm(forma, cx, cy, ancho * 3, 3501, octavas=2) - 0.5
    cerdas = estirado(forma, cx, cy, 0.03, 3502, 40.0) - 0.5
    carga = estirado(forma, cx, cy, ancho * 0.6, 3503, 6.0) - 0.5
    grumo = salpicado(forma, cx, cy, 0.08, 3504, 0.004)
    color = gris(0.5 + 0.04 * carga + 0.02 * cerdas)
    rug = 0.5 + 0.06 * cerdas - 0.05 * carga + 0.1 * grumo
    altura = 0.5 + 0.35 * cerdas * (0.6 + 0.4 * np.sign(tramo)) + 0.15 * carga + 0.3 * grumo
    return color, rug, altura


def chorretones(forma, cx, cy):
    """Pintura con chorretones (gotas que escurren hacia abajo)."""
    alto, ancho = forma
    x, y = rejilla(forma, cx, cy)
    th = alto * cy
    rng = np.random.default_rng(3601)
    salida = np.zeros(forma)
    for _ in range(12):
        x0, y0 = rng.uniform(0, ancho * cx), rng.uniform(0, th)
        largo, grueso = rng.uniform(4, 16), rng.uniform(0.3, 0.8)
        dx = (x - x0 + ancho * cx / 2) % (ancho * cx) - ancho * cx / 2
        dy = (y - y0) % th
        t = np.clip(dy / largo, 0, 1)
        w = grueso * (1 - 0.6 * t) + 0.2 * grueso * suave(t, 0.85, 1.0) * (dy < largo)
        gota = np.clip(1 - np.abs(dx) / np.maximum(w, 1e-3), 0, 1) * (dy < largo * 1.04)
        salida = np.maximum(salida, np.sqrt(gota))
    piel = ruido_cm(forma, cx, cy, 0.25, 3602) - 0.5
    color = gris(0.5 - 0.04 * salida)
    rug = 0.5 - 0.06 * salida + 0.02 * piel
    altura = 0.45 + 0.4 * salida + 0.1 * piel
    return color, rug, altura


def vdi(forma, cx, cy, tam=0.02, fuerza=1.0):
    """Plástico con textura de molde (electroerosión VDI): fina, media o gruesa según ``tam``."""
    grano = ruido_cm(forma, cx, cy, tam, 3701, octavas=2) - 0.5
    hoyo = hoyuelos(forma, cx, cy, tam * 1.5, 3702, 0.25)
    brillo = salpicado(forma, cx, cy, 2.0, 3703, 0.08, borde=0.1)  # zonas manoseadas
    color = gris(0.5 + 0.03 * grano + 0.02 * brillo)
    rug = 0.5 + 0.08 * fuerza * grano - 0.12 * brillo
    altura = 0.5 + fuerza * (0.35 * grano - 0.3 * hoyo) * (1 - 0.5 * brillo)
    return color, rug, altura


def plastico_usado(forma, cx, cy):
    """Plástico liso usado: rozaduras mates, arañazos y alguna marca blanca de golpe."""
    r = rayas(forma, cx, cy, 260, 4.0, 0.01, 3801, curva=0.2)
    roce = manchas_fractales(forma, cx, cy, 3.0, 3802, 0.12)
    golpe = salpicado(forma, cx, cy, 0.15, 3803, 0.004)
    velo = ruido_cm(forma, cx, cy, 6.0, 3804, octavas=3) - 0.5
    color = gris(0.5 + 0.04 * r + 0.06 * golpe + 0.02 * velo)
    rug = 0.5 + 0.18 * r + 0.15 * roce + 0.1 * golpe + 0.04 * velo
    altura = 0.5 - 0.2 * r - 0.2 * golpe
    return color, rug, altura


def impresion_3d(forma, cx, cy, capa=0.02):
    """Plástico de impresión 3D (FDM): líneas de capa horizontales y alguna capa irregular."""
    _, y = rejilla(forma, cx, cy)
    alto = forma[0] * cy
    capa = alto / max(1, round(alto / capa))  # número entero de capas: repite
    t = (y / capa) % 1.0
    perfil = np.sqrt(np.clip(np.sin(np.pi * t), 0, 1))
    irregular = estirado(forma, cx, cy, 0.2, 3901, 20.0) - 0.5
    color = gris(0.5 + 0.05 * (perfil - 0.5) + 0.03 * irregular)
    rug = 0.5 + 0.06 * (1 - perfil)
    altura = 0.3 + 0.5 * perfil + 0.15 * irregular
    return color, rug, altura


def goma(forma, cx, cy, punteado=0.0):
    """Goma o neumático: mate, grano fino, restos del desmoldeante y (opcional) punteado."""
    grano = ruido_cm(forma, cx, cy, 0.015, 4001, octavas=2) - 0.5
    velo = ruido_cm(forma, cx, cy, 3.0, 4002, octavas=3) - 0.5
    polvo = manchas_fractales(forma, cx, cy, 2.0, 4003, 0.15)
    color = gris(0.5 + 0.03 * grano + 0.08 * polvo + 0.03 * velo)
    rug = 0.5 + 0.06 * grano + 0.08 * polvo
    altura = 0.5 + 0.3 * grano
    if punteado:
        x, y = rejilla(forma, cx, cy)
        p = punteado
        d = np.hypot((x % p) - p / 2, (y % p) - p / 2) / (p * 0.3)
        boton = np.sqrt(np.clip(1 - d * d, 0, 1))
        altura = altura * 0.4 + 0.55 * boton
        rug = rug - 0.05 * boton
    return color, rug, altura


def silicona(forma, cx, cy):
    """Silicona o plástico blando: superficie sedosa con ondulaciones muy suaves."""
    onda = ruido_cm(forma, cx, cy, 1.0, 4101, octavas=2) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.03, 4102) - 0.5
    color = gris(0.5 + 0.02 * onda)
    rug = 0.5 + 0.03 * grano + 0.03 * onda
    return color, rug, 0.5 + 0.35 * onda + 0.1 * grano


def carbono(forma, cx, cy, patron=SARGA_2_2, paso=0.3):
    """Fibra de carbono: mechas tejidas que reflejan distinto según su dirección, bajo resina."""
    h, urd, fib = tejido(forma, cx, cy, paso, patron, 4201, hueco=0.04, fibra=0.3)
    color = gris(0.5 + 0.10 * (urd - 0.5) + 0.03 * fib)
    rug = 0.5 + 0.10 * (urd - 0.5) + 0.03 * fib
    return color, rug, 0.5 + 0.25 * (h - 0.5)


def cinta_aislante(forma, cx, cy):
    """Vinilo de cinta aislante: grano finísimo y bandas longitudinales leves."""
    banda = estirado(forma, cx, cy, 0.3, 4301, 30.0) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.01, 4302) - 0.5
    color = gris(0.5 + 0.02 * banda)
    rug = 0.5 + 0.06 * banda + 0.03 * grano
    return color, rug, 0.5 + 0.2 * grano + 0.1 * banda


def espuma(forma, cx, cy, tam=0.06):
    """Espuma (EVA, goma eva, foam): celdas pequeñas abiertas en la superficie."""
    _, dist, valor = celdas(forma, cx, cy, tam, 4401, temblor=1.0)
    poro = 1.0 - suave(dist, 0.0, tam * 0.35)
    color = gris(0.5 - 0.06 * (1 - suave(dist, 0, tam * 0.5)) + 0.02 * (valor - 0.5))
    rug = 0.5 + 0.06 * poro
    return color, rug, 0.6 - 0.4 * (1 - suave(dist, 0.0, tam * 0.45))


def _a(id_, funcion, nombre, familia, tile, relieve, muestra, para, rug=0.3, metal=0.0, **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=metal, recomendado_para=para)


P, PL = "Pintura", "Plástico y goma"
ACABADOS = [
    _a("pintura_piel_naranja", piel_naranja, "Esmalte con piel de naranja", P, (20.0, 20.0), 0.004, "#a01818",
       ["pintura de coche", "esmalte", "laca", "pintura satinada"], rug=0.12),
    _a("pintura_metalizada", metalizada, "Pintura metalizada", P, (6.0, 6.0), 0.003, "#8a9099",
       ["metalizad", "perlad"], rug=0.2, metal=0.6),
    _a("laca_remolinos", remolinos, "Laca con remolinos de lavado", P, (20.0, 20.0), 0.002, "#121212",
       ["laca", "piano", "pintura de coche negra", "lacad"], rug=0.06),
    _a("pintura_polvo", pintura_polvo, "Pintura en polvo", P, (10.0, 10.0), 0.01, "#2d4f3a",
       ["pintura en polvo", "epoxi", "chapa pintada"], rug=0.45),
    _a("pintura_brocha", pincelada, "Pintura a brocha", P, (40.0, 40.0), 0.02, "#d8d2c2",
       ["brocha", "barniz", "pintada", "pintura de juguete"], rug=0.4),
    _a("pintura_chorretones", chorretones, "Pintura con chorretones", P, (60.0, 60.0), 0.06, "#c9b26b",
       ["chorreton", "pintura vieja"], rug=0.35),
    _a("plastico_vdi_fino", vdi, "Plástico de molde fino", PL, (6.0, 6.0), 0.004, "#2a2a2c",
       ["plastico mate", "carcasa", "plastico rugoso"], rug=0.5, tam=0.012),
    _a("plastico_vdi_grueso", vdi, "Plástico de molde grueso", PL, (10.0, 10.0), 0.01, "#3a3a3d",
       ["plastico rugoso texturizado", "salpicadero"], rug=0.6, tam=0.05),
    _a("plastico_usado", plastico_usado, "Plástico liso usado", PL, (20.0, 20.0), 0.004, "#d22c2c",
       ["plastico brillante", "bloque de juguete", "pvc", "plastico"], rug=0.2),
    _a("plastico_impresion_3d", impresion_3d, "Impresión 3D (FDM)", PL, (5.0, 5.0), 0.01, "#e0782a",
       ["impresion 3d", "pla", "fdm"], rug=0.45),
    _a("goma_mate", goma, "Goma mate", PL, (10.0, 10.0), 0.005, "#202020",
       ["goma", "neumatico", "caucho"], rug=0.75),
    _a("goma_punteada", goma, "Goma punteada antideslizante", PL, (10.0, 10.0), 0.08, "#1e1e1e",
       ["goma", "alfombrilla", "antideslizante"], rug=0.75, punteado=0.5),
    _a("silicona", silicona, "Silicona", PL, (10.0, 10.0), 0.01, "#7fb8c9",
       ["silicona", "plastico blando", "plastilina"], rug=0.45),
    _a("carbono_sarga", carbono, "Fibra de carbono en sarga", PL, (9.6, 9.6), 0.02, "#1a1b1d",
       ["fibra de carbono", "carbono"], rug=0.15),
    _a("carbono_tafetan", carbono, "Fibra de carbono en tafetán", PL, (9.6, 9.6), 0.02, "#1a1b1d",
       ["fibra de carbono", "carbono"], rug=0.15, patron=TAFETAN),
    _a("cinta_aislante", cinta_aislante, "Vinilo de cinta aislante", PL, (10.0, 10.0), 0.003, "#141414",
       ["cinta aislante", "vinilo"], rug=0.35),
    _a("espuma_eva", espuma, "Espuma EVA", PL, (6.0, 6.0), 0.03, "#3d6fb5", ["espuma", "eva", "foam"],
       rug=0.8),
]
