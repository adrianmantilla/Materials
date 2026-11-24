"""Comprobación física de una receta: avisos que enseñan por qué un valor no es realista.

No depende de Maya. Devuelve una lista de avisos ``(nivel, clave_texto, valores)``
donde nivel es ``ok``, ``aviso`` o ``info``. Los textos están en i18n.
Con ``texturas`` (diccionario entrada -> información del mapa) se revisan
también los espacios de color y, en modo juego, los tamaños.
"""

from muestrario import color as col
from muestrario import receta as rc

OK, AVISO, INFO = "ok", "aviso", "info"


def _potencia_de_dos(n):
    return isinstance(n, int) and n > 0 and (n & (n - 1)) == 0


def comprobar(receta, destino=rc.RENDER, texturas=None):
    r = rc.normalizar(receta)
    texturas = texturas or {}
    avisos = []
    base = col.hex_a_lineal(r["color"])
    lum = col.luminancia(base)
    con_color_textura = "color" in texturas
    metal_textura = "metal" in texturas

    if not con_color_textura and r["emision"] == 0:
        if r["metal"] < 0.5 and lum < 0.011:
            avisos.append((AVISO, "chk_oscuro", {}))
        if r["metal"] < 0.5 and lum > 0.9 and r["transparencia"] < 0.5:
            avisos.append((AVISO, "chk_claro", {}))
        if r["metal"] >= 0.5 and max(base) < 0.3:
            avisos.append((AVISO, "chk_metal_oscuro", {}))
    if 0.1 < r["metal"] < 0.9 and not metal_textura:
        avisos.append((AVISO, "chk_metal_medias", {}))
    if r["metal"] >= 0.5 and (r["transparencia"] > 0 or r["subsuperficie"] > 0):
        avisos.append((AVISO, "chk_metal_transparente", {}))
    if r["transparencia"] > 0 and r["subsuperficie"] > 0:
        avisos.append((INFO, "chk_trans_sss", {}))
    if r["ior"] < 1.2 or r["ior"] > 2.6:
        avisos.append((AVISO, "chk_ior", {"ior": "{:.2f}".format(r["ior"])}))
    if r["emision"] > 0 and destino == rc.RENDER:
        avisos.append((INFO, "chk_emision", {"nits": int(round(rc.emision_a_nits(r["emision"])))}))
    if r["transparencia"] > 0 and r["opacidad"] < 1 and destino == rc.RENDER:
        avisos.append((INFO, "chk_opacidad_y_trans", {}))

    if destino == rc.JUEGO:
        apagados = [c for c in rc.SOLO_RENDER if r[c] > 0]
        if apagados:
            avisos.append((INFO, "chk_juego_apagados", {"lista": ", ".join(apagados)}))
        if r["transparencia"] > 0:
            avisos.append((INFO, "chk_juego_transparencia", {}))
        if 0 < r["metal"] < 1 and not metal_textura:
            avisos.append((AVISO, "chk_juego_metal", {}))
        if not rc.sirve_para(r, rc.JUEGO):
            avisos.append((AVISO, "chk_receta_render", {}))
    elif not rc.sirve_para(r, rc.RENDER):
        avisos.append((AVISO, "chk_receta_juego", {}))

    for entrada, info in sorted(texturas.items()):
        espacio = info.get("espacio")
        if entrada == "color" and espacio and espacio.lower() == "raw":
            avisos.append((AVISO, "chk_tex_color_raw", {"archivo": info.get("nombre", "")}))
        if entrada not in ("color", "emision") and espacio and espacio.lower().startswith("srgb"):
            avisos.append((AVISO, "chk_tex_dato_srgb", {"archivo": info.get("nombre", "")}))
        if entrada == "normal" and info.get("convencion") == "directx" and destino == rc.RENDER:
            avisos.append((INFO, "chk_tex_directx", {}))
        tam = info.get("tamano")
        if destino == rc.JUEGO and tam and not (_potencia_de_dos(tam[0]) and _potencia_de_dos(tam[1])):
            avisos.append((AVISO, "chk_tex_potencia", {"archivo": info.get("nombre", ""),
                                                       "ancho": tam[0], "alto": tam[1]}))
        if destino == rc.JUEGO and entrada == "altura" and info.get("desplazamiento"):
            avisos.append((AVISO, "chk_juego_desplazamiento", {}))

    if not any(n == AVISO for n, _, _ in avisos):
        avisos.insert(0, (OK, "chk_ok_juego" if destino == rc.JUEGO else "chk_ok", {}))
    return avisos


def hay_avisos(avisos):
    return any(n == AVISO for n, _, _ in avisos)
