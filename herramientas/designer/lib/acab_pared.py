"""Acabados de pared y construcción: estucos, yesos, gotelé, morteros, cementos, papel, cartón, suelos."""

import numpy as np

from superficie import (celdas, estirado, gris, hoyuelos, manchas_fractales, mezclar, rayas, rejilla,
                        ruido_cm, salpicado, suave)


def _llana(forma, cx, cy, tam, semilla, n=60):
    """Pasadas de llana: manchas planas de borde curvo que se solapan (estuco, microcemento)."""
    pasada = rayas(forma, cx, cy, n, tam * 3.0, tam * 0.8, semilla, curva=0.25)
    borde = rayas(forma, cx, cy, n, tam * 3.0, tam * 0.03, semilla + 1, curva=0.25)
    return pasada, borde


def estuco(forma, cx, cy):
    """Estuco veneciano: capas finas de llana, nubes de tono y brillo bruñido."""
    nube = ruido_cm(forma, cx, cy, 6.0, 16001, octavas=5) - 0.5
    pasada, borde = _llana(forma, cx, cy, 4.0, 16002)
    fino = ruido_cm(forma, cx, cy, 0.5, 16003, octavas=3) - 0.5
    color = gris(0.5 + 0.18 * nube + 0.05 * (pasada - 0.5) + 0.04 * fino - 0.06 * borde)
    return color, 0.5 - 0.1 * pasada + 0.05 * borde, 0.5 + 0.1 * pasada - 0.05 * borde


def yeso(forma, cx, cy):
    """Yeso liso pintado: casi plano, con pasadas de llana y poros sueltos."""
    pasada, borde = _llana(forma, cx, cy, 8.0, 16101, n=30)
    poro = hoyuelos(forma, cx, cy, 0.03, 16102, 0.01)
    fino = ruido_cm(forma, cx, cy, 0.3, 16103, octavas=2) - 0.5
    color = gris(0.5 + 0.015 * fino - 0.08 * poro - 0.02 * borde)
    return color, 0.5 + 0.03 * fino, 0.5 + 0.15 * pasada + 0.1 * fino - 0.4 * poro - 0.08 * borde


def gotele(forma, cx, cy, aplastado=False):
    """Gotelé: gotas de pintura espesa proyectadas de varios tamaños; ``aplastado`` las alisa con la
    llana (picado) y deja mesetas planas."""
    grande = ruido_cm(forma, cx, cy, 0.18, 16201, octavas=2)
    chica = ruido_cm(forma, cx, cy, 0.07, 16202, octavas=1)
    g1 = np.sqrt(suave(grande, np.quantile(grande, 0.62), np.quantile(grande, 0.97)))
    g2 = np.sqrt(suave(chica, np.quantile(chica, 0.75), np.quantile(chica, 0.99)))
    gota = np.maximum(g1, 0.6 * g2)
    fino = ruido_cm(forma, cx, cy, 0.03, 16203, octavas=2) - 0.5
    if aplastado:
        meseta = suave(gota, 0.45, 0.55)
        altura = 0.3 + 0.5 * np.minimum(gota, 0.5) / 0.5 + 0.05 * fino
        return gris(0.5 + 0.02 * fino + 0.02 * meseta), 0.5 - 0.08 * meseta, altura
    return gris(0.5 + 0.02 * fino), 0.5 + 0.03 * fino, 0.2 + 0.7 * gota + 0.08 * fino


def rodillo(forma, cx, cy):
    """Pintura a rodillo: piel de naranja fina y pasadas verticales apenas marcadas."""
    piel = ruido_cm(forma, cx, cy, 0.08, 16301, octavas=2) - 0.5
    pasada = estirado(forma, cx, cy, 2.0, 16302, 6.0, eje="y") - 0.5
    return gris(0.5 + 0.01 * piel + 0.015 * pasada), 0.5 + 0.06 * piel, 0.5 + 0.45 * piel + 0.05 * pasada


def enfoscado(forma, cx, cy):
    """Enfoscado de mortero (cemento y arena): áspero, granos de arena y fratás circular."""
    arena = ruido_cm(forma, cx, cy, 0.05, 16401, octavas=2) - 0.5
    grano = salpicado(forma, cx, cy, 0.08, 16402, 0.12, borde=0.05)
    mancha = ruido_cm(forma, cx, cy, 10.0, 16403, octavas=4) - 0.5
    humedad = manchas_fractales(forma, cx, cy, 20.0, 16404, 0.06)
    color = gris(0.5 + 0.06 * arena + 0.08 * mancha + 0.05 * grano - 0.08 * humedad, (1.0, 0.99, 0.97))
    return color, 0.5 + 0.05 * arena, 0.5 + 0.35 * arena + 0.15 * grano


def monocapa(forma, cx, cy):
    """Monocapa raspado: árido grueso que asoma en una masa de color, superficie arañada."""
    _, dist, valor = celdas(forma, cx, cy, 0.3, 16501, temblor=1.0, pesos=0.6)
    arido = (valor > 0.55) * np.sqrt(suave(dist, 0.0, 0.1))
    raspa = ruido_cm(forma, cx, cy, 0.04, 16502, octavas=2) - 0.5
    color = gris(0.5 + 0.04 * raspa + 0.04 * (valor - 0.5) * (valor > 0.55))
    return color, 0.5 + 0.08 * raspa, 0.35 + 0.35 * arido + 0.3 * raspa


def microcemento(forma, cx, cy):
    """Microcemento: aguas de llana grises, nubes y poros pequeños, satinado."""
    nube = ruido_cm(forma, cx, cy, 15.0, 16601, octavas=5) - 0.5
    pasada, borde = _llana(forma, cx, cy, 10.0, 16602, n=40)
    poro = hoyuelos(forma, cx, cy, 0.04, 16603, 0.015)
    color = gris(0.5 + 0.14 * nube + 0.05 * (pasada - 0.5) - 0.06 * borde - 0.15 * poro, (1.0, 1.0, 1.01))
    return color, 0.5 - 0.06 * pasada + 0.1 * poro, 0.5 + 0.05 * pasada - 0.3 * poro


def hormigon_pulido(forma, cx, cy):
    """Hormigón pulido: árido cortado (piedras de canto) en pasta gris, con pulido brillante."""
    ids, dist, valor = celdas(forma, cx, cy, 1.0, 16701, temblor=1.0, pesos=0.8)
    piedra = (valor > 0.45) * suave(dist, 0.04, 0.12)
    tono = np.random.default_rng(16702).uniform(0.35, 0.65, ids.max() + 1)[ids]
    pasta = ruido_cm(forma, cx, cy, 0.05, 16703, octavas=2) - 0.5
    color = gris(0.52 + 0.03 * pasta)
    color = color * (1 - piedra[..., None]) + gris(tono * 1.1) * piedra[..., None]
    poro = hoyuelos(forma, cx, cy, 0.03, 16704, 0.01)
    return color - 0.1 * poro[..., None], 0.5 + 0.1 * poro, 0.5 - 0.3 * poro


def fratasado(forma, cx, cy):
    """Cemento fratasado: remolinos del fratás mecánico (helicóptero) en arcos solapados."""
    x, y = rejilla(forma, cx, cy)
    arco = np.zeros(forma)
    rng = np.random.default_rng(16801)
    tw, th = forma[1] * cx, forma[0] * cy
    for _ in range(24):
        x0, y0, r = rng.uniform(0, tw), rng.uniform(0, th), rng.uniform(25, 45)
        dx = (x - x0 + tw / 2) % tw - tw / 2
        dy = (y - y0 + th / 2) % th - th / 2
        d = np.hypot(dx, dy)
        arco += np.exp(-((d - r) / 1.5) ** 2) * rng.uniform(0.3, 1.0)
    arco = np.clip(arco, 0, 1.5)
    arena = ruido_cm(forma, cx, cy, 0.05, 16802, octavas=2) - 0.5
    nube = ruido_cm(forma, cx, cy, 20.0, 16803, octavas=4) - 0.5
    color = gris(0.5 + 0.03 * arena + 0.1 * nube - 0.05 * arco)
    return color, 0.5 - 0.06 * arco + 0.03 * arena, 0.5 + 0.1 * arena + 0.03 * arco


def papel(forma, cx, cy, fibra=1.0, tono=(1.0, 1.0, 1.0), manchas=0.0):
    """Papel: fibras cortas entrecruzadas y nubes de pasta (formación)."""
    f1 = estirado(forma, cx, cy, 0.01, 16901, 8.0) - 0.5
    f2 = estirado(forma, cx, cy, 0.01, 16902, 8.0, eje="y") - 0.5
    formacion = ruido_cm(forma, cx, cy, 0.3, 16903, octavas=3) - 0.5
    lum = 0.5 + fibra * (0.02 * (f1 + f2) + 0.05 * formacion)
    color = gris(lum, tono)
    if manchas:
        punto = salpicado(forma, cx, cy, 0.02, 16904, manchas, borde=0.02)
        color = mezclar(color, (0.25, 0.20, 0.15), 0.6 * punto)
    return color, 0.5 + 0.03 * formacion, 0.5 + 0.3 * (f1 + f2) + 0.2 * formacion


def arrugado(forma, cx, cy):
    """Papel arrugado y alisado: pliegues afilados (ruido «crestado») de varios tamaños sobre papel."""
    color, rug, altura = papel(forma, cx, cy)
    pliegues = np.zeros(forma)
    for k, (tam, peso) in enumerate(((4.0, 0.5), (1.5, 0.3), (0.6, 0.2))):
        r = ruido_cm(forma, cx, cy, tam, 16951 + k, octavas=1)
        pliegues += peso * (1 - np.abs(2 * r - 1) * 3.0).clip(-1, 1)
    gx = (np.roll(pliegues, -1, 1) - np.roll(pliegues, 1, 1)) / 2  # repite: sin np.gradient
    gy = (np.roll(pliegues, -1, 0) - np.roll(pliegues, 1, 0)) / 2
    luz = np.clip(0.5 + 6.0 * (gx - gy), 0, 1) - 0.5
    return color + 0.05 * luz[..., None], rug, 0.5 + 0.35 * pliegues + 0.1 * (altura - 0.5)


def carton(forma, cx, cy):
    """Cartón (superficie): fibra marrón gruesa, motas oscuras y la onda interior apenas marcada."""
    x, _ = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    paso = tw / max(1, round(tw / 0.8))
    onda = 0.5 + 0.5 * np.cos(2 * np.pi * x / paso)
    color, rug, altura = papel(forma, cx, cy, fibra=1.6, manchas=0.02)
    return color, rug, altura + 0.15 * onda


def carton_ondulado(forma, cx, cy):
    """Cartón ondulado al aire (canto rasgado): onda sinusoidal profunda con fibra."""
    x, _ = rejilla(forma, cx, cy)
    tw = forma[1] * cx
    paso = tw / max(1, round(tw / 0.8))
    onda = 0.5 + 0.5 * np.cos(2 * np.pi * x / paso)
    color, rug, altura = papel(forma, cx, cy, fibra=1.4)
    sombra = 1 - 0.15 * (1 - onda)
    return color * sombra[..., None], rug, 0.1 + 0.8 * onda + 0.05 * (altura - 0.5)


def linoleo(forma, cx, cy):
    """Linóleo jaspeado: vetas estiradas de dos o tres tonos (como mármol arrastrado)."""
    a = estirado(forma, cx, cy, 0.6, 17001, 6.0, octavas=4)
    b = estirado(forma, cx, cy, 0.3, 17002, 6.0, octavas=3)
    claro = suave(a, 0.55, 0.62)
    oscuro = suave(b, 0.6, 0.66)
    color = gris(0.5 + 0.12 * claro - 0.12 * oscuro)
    fino = ruido_cm(forma, cx, cy, 0.05, 17003) - 0.5
    return color, 0.5 + 0.03 * fino, 0.5 + 0.05 * fino


def asfalto(forma, cx, cy, gastado=0.0):
    """Asfalto (aglomerado): árido gris en betún negro; ``gastado`` deja ver más piedra y la aclara."""
    _, dist, valor = celdas(forma, cx, cy, 0.6, 17101, temblor=1.0, pesos=0.6)
    piedra = suave(dist, 0.03, 0.1) * (valor > 0.3 - 0.2 * gastado)
    betun = ruido_cm(forma, cx, cy, 0.05, 17102, octavas=2) - 0.5
    mancha = ruido_cm(forma, cx, cy, 30.0, 17103, octavas=4) - 0.5
    lum = 0.38 + 0.03 * betun + 0.25 * piedra * (0.6 + 0.4 * valor) * (0.4 + 0.6 * gastado) + 0.06 * mancha
    color = gris(lum)
    return color, 0.5 + 0.05 * betun - 0.05 * piedra * gastado, 0.25 + 0.5 * piedra + 0.1 * betun


def humedad(forma, cx, cy):
    """Pared pintada con manchas de humedad: cercos amarillentos, salitre y pintura abombada."""
    rodal = manchas_fractales(forma, cx, cy, 30.0, 17201, 0.35, detalle=0.5)
    r = ruido_cm(forma, cx, cy, 30.0, 17201, octavas=4)
    cerco = np.exp(-((r - np.quantile(r, 0.65)) / 0.01) ** 2)
    salitre = salpicado(forma, cx, cy, 0.3, 17202, 0.08, borde=0.08) * rodal
    abombado = hoyuelos(forma, cx, cy, 1.5, 17203, 0.08) * rodal
    color = gris(np.full(forma, 0.5))
    color = mezclar(color, (0.46, 0.43, 0.36), 0.5 * rodal)
    color = mezclar(color, (0.38, 0.33, 0.25), 0.6 * cerco)
    color = mezclar(color, (0.56, 0.56, 0.55), 0.7 * salitre)
    return color, 0.5 + 0.15 * rodal + 0.2 * salitre, 0.5 + 0.3 * abombado + 0.05 * salitre


def sucia(forma, cx, cy):
    """Pared sucia: churretes verticales de lluvia y polvo."""
    churrete = estirado(forma, cx, cy, 0.5, 17301, 25.0, eje="y", octavas=3)
    polvo = ruido_cm(forma, cx, cy, 8.0, 17302, octavas=4)
    suciedad = np.clip(1.4 * (churrete - 0.45) + 0.4 * (polvo - 0.5), 0, 1)
    color = mezclar(gris(np.full(forma, 0.5)), (0.36, 0.34, 0.30), 0.6 * suciedad)
    return color, 0.5 + 0.1 * suciedad, 0.5 + 0.02 * suciedad


def _a(id_, funcion, nombre, tile, relieve, muestra, para, rug=0.7, familia="Revestimiento", **kw):
    f = (lambda forma, cx, cy: funcion(forma, cx, cy, **kw)) if kw else funcion
    return dict(id=id_, funcion=f, nombre=nombre, familia=familia, tile_cm=tile, relieve_cm=relieve,
                muestra=muestra, muestra_rug=rug, muestra_metal=0.0, recomendado_para=para)


P = "Papel"
ACABADOS = [
    _a("estuco_veneciano", estuco, "Estuco veneciano", (80.0, 80.0), 0.03, "#c8b89a", ["estuco", "veneciano"],
       rug=0.25),
    _a("yeso_liso", yeso, "Yeso liso pintado", (80.0, 80.0), 0.03, "#e8e6e0", ["yeso", "pared pintada",
       "pared lisa"], rug=0.8),
    _a("gotele", gotele, "Gotelé", (20.0, 20.0), 0.15, "#ece8dc", ["gotele"], rug=0.8),
    _a("gotele_aplastado", gotele, "Gotelé aplastado", (20.0, 20.0), 0.1, "#ece8dc", ["gotele aplastado",
       "picado"], rug=0.75, aplastado=True),
    _a("pintura_rodillo", rodillo, "Pintura a rodillo", (20.0, 20.0), 0.02, "#d8dde0", ["rodillo",
       "pintura plastica"], rug=0.75),
    _a("enfoscado", enfoscado, "Enfoscado de mortero", (60.0, 60.0), 0.1, "#a8a49c", ["enfoscado", "mortero",
       "revoco"], rug=0.9),
    _a("monocapa_raspado", monocapa, "Monocapa raspado", (30.0, 30.0), 0.15, "#d4c6a8", ["monocapa",
       "raspado"], rug=0.9),
    _a("microcemento", microcemento, "Microcemento", (120.0, 120.0), 0.02, "#9a9894", ["microcemento"], rug=0.4),
    _a("hormigon_pulido", hormigon_pulido, "Hormigón pulido", (40.0, 40.0), 0.02, "#9c9a96",
       ["hormigon pulido", "suelo industrial"], rug=0.25),
    _a("cemento_fratasado", fratasado, "Cemento fratasado", (200.0, 200.0), 0.02, "#8e8c88", ["fratasado",
       "solera", "cemento"], rug=0.5),
    _a("papel_blanco", papel, "Papel", (10.0, 10.0), 0.005, "#f2f0ea", ["papel", "folio", "libro"], rug=0.85,
       familia=P),
    _a("papel_kraft", papel, "Papel kraft", (10.0, 10.0), 0.008, "#b08a5e", ["kraft", "papel de estraza",
       "bolsa"], rug=0.85, familia=P, fibra=1.6, manchas=0.01),
    _a("papel_arrugado", arrugado, "Papel arrugado", (20.0, 20.0), 0.3, "#ece8e0", ["arrugad", "papel viejo"],
       rug=0.85, familia=P),
    _a("carton", carton, "Cartón", (20.0, 20.0), 0.02, "#a8825a", ["carton", "caja"], rug=0.9, familia=P),
    _a("carton_ondulado", carton_ondulado, "Cartón ondulado (al aire)", (8.0, 8.0), 0.3, "#b08c60",
       ["ondulado"], rug=0.9, familia=P),
    _a("linoleo", linoleo, "Linóleo jaspeado", (40.0, 40.0), 0.005, "#8a7a6a", ["linoleo", "marmoleum"],
       rug=0.5, familia="Suelo"),
    _a("asfalto", asfalto, "Asfalto", (60.0, 60.0), 0.3, "#5a5a5a", ["asfalto", "carretera", "calle"], rug=0.85,
       familia="Suelo"),
    _a("asfalto_gastado", asfalto, "Asfalto gastado", (60.0, 60.0), 0.3, "#6e6c68", ["asfalto viejo"],
       rug=0.85, familia="Suelo", gastado=1.0),
    _a("pared_humedad", humedad, "Pared con humedad", (150.0, 150.0), 0.05, "#e0dcd2", ["humedad", "salitre",
       "pared vieja"], rug=0.8),
    _a("pared_sucia", sucia, "Pared sucia (churretes)", (150.0, 150.0), 0.01, "#d8d4ca", ["sucia", "churrete",
       "fachada"], rug=0.8),
]
