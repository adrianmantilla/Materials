"""Acabados de madera: especies (veta a lo largo de X), nudos, radios, envejecida, quemada, tableros."""

import numpy as np

from superficie import (celdas, estirado, gris, grietas, hoyuelos, manchas_fractales, mezclar, rejilla,
                        ruido_cm, salpicado, suave)


def _periodico(d, tam):
    return (d + tam / 2) % tam - tam / 2


def veta(forma, cx, cy, anillo=0.45, contraste=0.14, bandas=0.06, poros=0.0, radios=0.0, nudos=0,
         figura=0.0, tono=0.20, desvio=20.0, semilla=12001):
    """Madera aserrada (veta a lo largo de X) con parámetros de especie.

    ``anillo`` cm entre anillos; ``contraste`` del tardío; ``poros`` (roble, fresno: poros abiertos
    en el temprano); ``radios`` (roble: motas brillantes cruzadas); ``nudos`` (pino: cuántos por
    imagen); ``figura`` (arce rizado: ondas cruzadas); ``desvio`` cm de ondulación de la veta.
    """
    alto, ancho = forma
    x, y = rejilla(forma, cx, cy)
    tw, th = ancho * cx, alto * cy
    onda = ((ruido_cm(forma, cx * 0.04, cy, 1.2, semilla, octavas=2) - 0.5) * desvio
            + (ruido_cm(forma, cx * 0.15, cy, 0.8, semilla + 1) - 0.5) * 0.8)
    rng = np.random.default_rng(semilla + 2)
    nudo_osc = np.zeros(forma)
    for _ in range(int(nudos)):
        nx, ny = rng.uniform(0, tw), rng.uniform(0, th)
        r = rng.uniform(0.6, 1.4)
        dx, dy = _periodico(x - nx, tw), _periodico(y - ny, th)
        d2 = (dx / 2.2) ** 2 + dy ** 2
        onda = onda + 1.6 * r * r / (d2 + r * r) * np.sign(dy + 1e-6) * r
        nudo_osc = np.maximum(nudo_osc, np.exp(-d2 / (0.35 * r) ** 2))
    if figura:
        onda = onda + figura * 0.25 * np.sin(2 * np.pi * x * max(1, round(tw / 1.2)) / tw)
    periodo = th / max(1, round(th / anillo))
    t = ((y + onda) / periodo) % 1.0
    tardio = suave(t, 0.62, 0.72) * (1.0 - suave(t, 0.9, 1.0))
    k1, k2 = max(1, round(th / periodo / 7)), max(1, round(th / periodo / 17))
    banda = (np.sin(2 * np.pi * (y + onda) * k1 / th) + 0.6 * np.sin(2 * np.pi * (y + 0.7 * onda) * k2 / th))
    mancha = ruido_cm(forma, cx * 0.1, cy, 3.0, semilla + 3, octavas=2) - 0.5
    fibra = ruido_cm(forma, cx * 0.04, cy, 0.05, semilla + 4, octavas=2) - 0.5
    lum = 0.5 + tono * mancha + bandas * banda + 0.08 * fibra - contraste * tardio
    altura = 0.5 + 0.25 * fibra - 0.12 * tardio
    rug = 0.5 + 0.05 * fibra + 0.06 * tardio
    if poros:
        p = suave(ruido_cm(forma, cx * 0.06, cy, 0.03, semilla + 5), 0.62, 0.7) * (1 - tardio) * poros
        lum = lum - 0.15 * p
        altura = altura - 0.35 * p
        rug = rug + 0.08 * p
    if radios:
        r_ = suave(ruido_cm(forma, cx, cy * 0.15, 0.08, semilla + 6), 0.72, 0.78) * radios
        lum = lum + 0.10 * r_
        rug = rug - 0.1 * r_
    if nudos:
        lum = lum - 0.35 * nudo_osc
        rug = rug - 0.05 * nudo_osc
    color = np.dstack([lum * 1.02, lum, lum * 0.96])
    return color, rug, altura


def envejecida(forma, cx, cy):
    """Madera a la intemperie: gris plateada, veta en relieve (el temprano se gasta) y grietas."""
    color, rug, altura = veta(forma, cx, cy, anillo=0.5, contraste=0.2, semilla=12101)
    grieta = 1 - suave(np.abs(estirado(forma, cx, cy, 0.4, 12102, 25.0) - 0.5), 0.0, 0.02)
    liquen = salpicado(forma, cx, cy, 0.3, 12103, 0.03, borde=0.05)
    l = color.mean(axis=2)
    color = gris(l, (1.0, 1.0, 1.02)) * (1 - 0.4 * grieta[..., None])
    color = mezclar(color, (0.55, 0.55, 0.42), 0.5 * liquen)
    return color, rug + 0.2, altura * 1.6 - 0.3 - 0.4 * grieta


def quemada(forma, cx, cy):
    """Madera quemada (yakisugi): costra negra agrietada en «piel de cocodrilo», brillo plateado."""
    grieta = grietas(forma, cx, cy, 1.0, 12201, 0.05)
    _, dist, valor = celdas(forma, cx, cy, 1.0, 12201, temblor=0.9)
    escama = np.sqrt(suave(dist, 0.0, 0.35))
    fibra = estirado(forma, cx, cy, 0.05, 12202, 20.0) - 0.5
    color = gris(0.30 + 0.06 * (valor - 0.5) + 0.04 * fibra - 0.2 * grieta)
    rug = 0.5 + 0.1 * grieta - 0.08 * escama * (valor > 0.7)
    return color, rug, 0.25 + 0.5 * escama + 0.1 * fibra - 0.2 * grieta


def pintada(forma, cx, cy):
    """Madera pintada (blanca) envejecida: se adivina la veta y la pintura salta en el borde de las vetas."""
    _, rug, altura = veta(forma, cx, cy, anillo=0.5, contraste=0.2, semilla=12301)
    salta = manchas_fractales(forma, cx, cy, 2.5, 12302, 0.08, detalle=0.6)
    cuarteado = 1 - suave(np.abs(estirado(forma, cx, cy, 0.3, 12303, 12.0) - 0.5), 0.0, 0.015)
    madera = np.array([0.30, 0.22, 0.15])
    color = gris(0.5 + 0.02 * (altura - 0.5))
    color = mezclar(color * (1 - 0.15 * cuarteado[..., None]), madera, salta)
    return color, 0.5 + 0.15 * salta, 0.5 + 0.4 * (altura - 0.5) + 0.08 * (1 - salta) - 0.1 * cuarteado


def contrachapado(forma, cx, cy):
    """Contrachapado (chapa desenrollada): veta ancha y ondulante, con algún parche o nudo tapado."""
    color, rug, altura = veta(forma, cx, cy, anillo=1.6, contraste=0.10, bandas=0.08, desvio=60.0, tono=0.12,
                              semilla=12401)
    parche = salpicado(forma, cx, cy, 2.0, 12402, 0.01, borde=0.01)
    return color * (1 + 0.05 * parche[..., None]), rug, altura


def tablero_dm(forma, cx, cy):
    """Tablero DM (MDF): fibra finísima y uniforme, sin veta."""
    grano = ruido_cm(forma, cx, cy, 0.01, 12501, octavas=2) - 0.5
    mancha = ruido_cm(forma, cx, cy, 2.0, 12502, octavas=3) - 0.5
    return gris(0.5 + 0.04 * grano + 0.04 * mancha, (1.02, 1.0, 0.97)), 0.5 + 0.03 * grano, 0.5 + 0.2 * grano


def aglomerado(forma, cx, cy, viruta=0.5):
    """Aglomerado u OSB: virutas alargadas en todas direcciones, cada una con su tono."""
    color = np.zeros(forma + (3,))
    altura = np.full(forma, 0.5)
    for k, (fx, eje) in enumerate(((5.0, "x"), (5.0, "y"), (3.0, "x"), (3.0, "y"))):
        r = estirado(forma, cx, cy, viruta, 12601 + k, fx, eje=eje)
        corte = np.quantile(r, 0.6)
        m = suave(r, corte, corte + 0.02)
        lum = 0.5 + 0.15 * (ruido_cm(forma, cx, cy, viruta * 2, 12611 + k) - 0.5)
        sel = m > 0.5
        color[sel] = np.dstack([lum, lum * 0.97, lum * 0.92])[sel]
        altura[sel] = 0.5 + 0.08 * k
    vacio = color.sum(axis=2) == 0
    color[vacio] = 0.42
    fibra = estirado(forma, cx, cy, 0.02, 12620, 8.0) - 0.5
    color = color * (1 + 0.08 * fibra[..., None])
    return color, 0.5 + 0.05 * fibra, altura + 0.15 * fibra - 0.2 * vacio


def corcho(forma, cx, cy):
    """Corcho aglomerado: gránulos de varios tonos y huecos oscuros."""
    _, dist, valor = celdas(forma, cx, cy, 0.25, 12701, temblor=1.0, pesos=0.6)
    hueco = 1 - suave(dist, 0.0, 0.025)
    poro = hoyuelos(forma, cx, cy, 0.03, 12702, 0.08)
    color = gris(0.5 + 0.18 * (valor - 0.5) - 0.2 * hueco - 0.1 * poro, (1.03, 1.0, 0.95))
    return color, 0.5 + 0.05 * poro, 0.5 + 0.1 * (valor - 0.5) - 0.4 * hueco - 0.3 * poro


def bambu(forma, cx, cy, nudo=30.0):
    """Bambú (tablero o caña abierta): fibras paralelas muy finas y nudos cada ``nudo`` cm."""
    x, _ = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    paso = tw / max(1, round(tw / nudo))
    fibra = estirado(forma, cx, cy, 0.02, 12801, 40.0) - 0.5
    d = np.abs(_periodico(x, paso))
    n = np.exp(-(d / 0.6) ** 2)
    mancha = ruido_cm(forma, cx * 0.1, cy, 2.0, 12802, octavas=2) - 0.5
    color = gris(0.5 + 0.05 * fibra + 0.08 * mancha - 0.15 * n, (1.02, 1.0, 0.92))
    return color, 0.5 + 0.03 * fibra + 0.05 * n, 0.5 + 0.2 * fibra + 0.3 * n


def corteza(forma, cx, cy):
    """Corteza de árbol: surcos verticales profundos que se ramifican, placas y musgo."""
    surco = estirado(forma, cx, cy, 1.0, 12901, 6.0, eje="y", octavas=4)
    placa = suave(surco, 0.35, 0.6)
    grieta = grietas(forma, cx, cy, 2.0, 12902, 0.08)
    grano = ruido_cm(forma, cx, cy, 0.08, 12903, octavas=2) - 0.5
    musgo = manchas_fractales(forma, cx, cy, 4.0, 12904, 0.12) * (1 - placa)
    color = gris(0.38 + 0.2 * placa + 0.05 * grano - 0.1 * grieta)
    color = mezclar(color, (0.30, 0.38, 0.15), 0.7 * musgo)
    return color, 0.5 + 0.1 * (1 - placa), 0.1 + 0.7 * placa - 0.2 * grieta + 0.1 * grano


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.55, **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia="Madera", tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


T = (160.0, 20.0)  # tabla: 1,6 m de largo por 20 cm, veta a lo largo
ACABADOS = [
    _a("roble", veta, "Roble", T, 0.15, "#9a7048", ["roble", "parque", "parqué"], poros=1.0, radios=0.6,
       anillo=0.35),
    _a("nogal", veta, "Nogal", T, 0.12, "#5a3a26", ["nogal"], poros=0.5, anillo=0.5, contraste=0.2, tono=0.25),
    _a("pino", veta, "Pino con nudos", T, 0.15, "#c9a06a", ["pino", "palé", "pale", "abeto"], anillo=0.6,
       contraste=0.25, nudos=3),
    _a("haya", veta, "Haya", T, 0.08, "#c89a72", ["haya"], anillo=0.4, contraste=0.06, radios=0.4, tono=0.1),
    _a("arce_rizado", veta, "Arce rizado", T, 0.06, "#d8b88e", ["arce"], anillo=0.6, contraste=0.06, figura=1.0,
       tono=0.1),
    _a("cerezo", veta, "Cerezo", T, 0.08, "#9a5638", ["cerezo"], anillo=0.4, contraste=0.1, tono=0.2),
    _a("caoba", veta, "Caoba", T, 0.08, "#6e2e1e", ["caoba", "sapelli"], anillo=0.9, contraste=0.08,
       bandas=0.12, poros=0.4),
    _a("teca", veta, "Teca", T, 0.1, "#8a6338", ["teca", "iroko"], anillo=0.7, contraste=0.16, poros=0.6),
    _a("ebano", veta, "Ébano", T, 0.04, "#2a201c", ["ebano", "wengue"], anillo=0.3, contraste=0.1, tono=0.3),
    _a("madera_envejecida", envejecida, "Madera envejecida a la intemperie", T, 0.3, "#9c8f80",
       ["madera envejecida", "granero", "vieja"], rug=0.8),
    _a("madera_quemada", quemada, "Madera quemada (yakisugi)", (40.0, 40.0), 0.3, "#2a2725",
       ["madera quemada", "yakisugi", "carbonizad"], rug=0.7),
    _a("madera_pintada_vieja", pintada, "Madera pintada envejecida", T, 0.08, "#e8e4da",
       ["madera pintada", "pintada blanca", "contraventana"], rug=0.6),
    _a("contrachapado", contrachapado, "Contrachapado", (120.0, 120.0), 0.06, "#c9a477", ["contrachapado",
       "tablero"], rug=0.6),
    _a("tablero_dm", tablero_dm, "Tablero DM", (40.0, 40.0), 0.02, "#a87c55", ["dm", "mdf", "tablero dm"], rug=0.7),
    _a("aglomerado_osb", aglomerado, "Aglomerado OSB", (60.0, 60.0), 0.2, "#b89464", ["aglomerado", "osb"],
       rug=0.75, viruta=1.2),
    _a("aglomerado_fino", aglomerado, "Aglomerado fino", (20.0, 20.0), 0.05, "#bfa27a", ["aglomerado",
       "conglomerado"], rug=0.75, viruta=0.25),
    _a("corcho", corcho, "Corcho aglomerado", (20.0, 20.0), 0.08, "#a47548", ["corcho"], rug=0.85),
    _a("bambu", bambu, "Bambú", (120.0, 20.0), 0.1, "#cfb27a", ["bambu"], rug=0.5),
    _a("corteza_arbol", corteza, "Corteza de árbol", (40.0, 60.0), 1.5, "#6b5a4a", ["corteza", "tronco", "arbol"],
       rug=0.9),
]
