"""Genera las recetas de la biblioteca (scripts/materials/biblioteca/*.json).

Herramienta de desarrollo: las recetas se escriben aquí como tablas compactas y
el script las vuelca a JSON, que es lo que lee el plugin. Para añadir o cambiar
una receta, edita la tabla y ejecuta:

    python3 herramientas/generar_biblioteca.py

Colores: «#rrggbb» en sRGB, o «L:r,g,b» para un reflejo lineal medido
(metales; valores F0 de tablas físicas como las de Real-Time Rendering).
Destinos: R = solo render, J = solo juego, si no se indica, los dos.
"""

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

from materials import color as col  # noqa: E402
from materials import receta as rc  # noqa: E402

SALIDA = os.path.join(RAIZ, "scripts", "materials", "biblioteca")


def c(texto):
    if texto.startswith("L:"):
        return col.lineal_a_hex(tuple(float(v) for v in texto[2:].split(",")))
    return texto


# Atajos para los extras
def M(**k):
    return k


ORO = "L:1.0,0.766,0.336"
PLATA = "L:0.972,0.960,0.915"
ALUMINIO = "L:0.913,0.922,0.924"
HIERRO = "L:0.562,0.565,0.578"
COBRE = "L:0.955,0.638,0.538"
CROMO = "L:0.550,0.556,0.554"
NIQUEL = "L:0.660,0.609,0.526"
TITANIO = "L:0.542,0.497,0.449"
PLATINO = "L:0.673,0.637,0.585"
ZINC = "L:0.664,0.824,0.850"
LATON = "L:0.910,0.778,0.423"
BRONCE = "L:0.80,0.55,0.35"
PLOMO = "L:0.632,0.626,0.641"
COBALTO = "L:0.662,0.655,0.634"
MERCURIO = "L:0.781,0.779,0.778"

FAMILIAS = [
    ("metales", "Metales", [
        ("Oro pulido", ORO, 0.08, M(metal=1), "", "Oro de 24 quilates. El color del metal va en Color base."),
        ("Oro", ORO, 0.22, M(metal=1), "", ""),
        ("Oro cepillado", ORO, 0.32, M(metal=1, anisotropia=0.6), "", "La anisotropía estira el brillo en la dirección del cepillado."),
        ("Oro rosa", "L:0.98,0.70,0.55", 0.2, M(metal=1), "", ""),
        ("Oro blanco", "L:0.90,0.87,0.78", 0.18, M(metal=1), "", ""),
        ("Plata pulida", PLATA, 0.06, M(metal=1), "", ""),
        ("Plata", PLATA, 0.25, M(metal=1), "", ""),
        ("Plata envejecida", "L:0.70,0.68,0.62", 0.45, M(metal=1), "", "El ennegrecido real está en las grietas: píntalo en Painter."),
        ("Aluminio pulido", ALUMINIO, 0.08, M(metal=1), "", ""),
        ("Aluminio", ALUMINIO, 0.3, M(metal=1), "", ""),
        ("Aluminio cepillado", ALUMINIO, 0.35, M(metal=1, anisotropia=0.7), "", ""),
        ("Aluminio anodizado rojo", "L:0.75,0.12,0.10", 0.3, M(metal=1), "", "El anodizado tiñe el reflejo, por eso es metal con color."),
        ("Aluminio anodizado azul", "L:0.15,0.30,0.75", 0.3, M(metal=1), "", ""),
        ("Aluminio anodizado negro", "L:0.32,0.32,0.34", 0.35, M(metal=1), "", ""),
        ("Acero inoxidable", "L:0.67,0.64,0.60", 0.2, M(metal=1), "", ""),
        ("Acero cepillado", "L:0.67,0.64,0.60", 0.35, M(metal=1, anisotropia=0.7), "", ""),
        ("Acero pulido espejo", "L:0.67,0.64,0.60", 0.03, M(metal=1), "", ""),
        ("Hierro", HIERRO, 0.45, M(metal=1), "", ""),
        ("Hierro fundido", HIERRO, 0.65, M(metal=1), "", ""),
        ("Hierro forjado oscuro", "L:0.42,0.42,0.43", 0.55, M(metal=1), "", ""),
        ("Cobre pulido", COBRE, 0.1, M(metal=1), "", ""),
        ("Cobre", COBRE, 0.3, M(metal=1), "", ""),
        ("Cobre envejecido", "L:0.80,0.50,0.38", 0.5, M(metal=1), "", "La pátina verde no es metal: usa una máscara en Painter."),
        ("Latón", LATON, 0.25, M(metal=1), "", ""),
        ("Latón envejecido", "L:0.72,0.60,0.33", 0.45, M(metal=1), "", ""),
        ("Bronce", BRONCE, 0.35, M(metal=1), "", ""),
        ("Cromo", CROMO, 0.03, M(metal=1), "", "El cromo es más oscuro de lo que parece: brilla porque es muy liso."),
        ("Níquel", NIQUEL, 0.2, M(metal=1), "", ""),
        ("Titanio", TITANIO, 0.3, M(metal=1), "", ""),
        ("Titanio quemado", "L:0.45,0.40,0.55", 0.25, M(metal=1, pelicula=0.8, grosor_pelicula=420), "R", "El arcoíris del titanio quemado es una película fina."),
        ("Platino", PLATINO, 0.15, M(metal=1), "", ""),
        ("Zinc", ZINC, 0.35, M(metal=1), "", ""),
        ("Chapa galvanizada", "L:0.70,0.72,0.73", 0.45, M(metal=1), "", ""),
        ("Plomo", PLOMO, 0.5, M(metal=1), "", ""),
        ("Cobalto", COBALTO, 0.25, M(metal=1), "", ""),
        ("Mercurio", MERCURIO, 0.0, M(metal=1), "", "Metal líquido: rugosidad cero."),
        ("Espejo", PLATA, 0.0, M(metal=1), "", "Un espejo es plata detrás de un vidrio; aquí basta con plata sin rugosidad."),
    ]),
    ("plasticos", "Plásticos y gomas", [
        ("Plástico rojo brillante", "#c22a2a", 0.18, M(), "", "Los plásticos son dieléctricos: metal a 0 e IOR cercano a 1,5."),
        ("Plástico azul brillante", "#2257b8", 0.18, M(), "", ""),
        ("Plástico amarillo brillante", "#e8b31a", 0.18, M(), "", ""),
        ("Plástico verde brillante", "#2f9a4a", 0.18, M(), "", ""),
        ("Plástico blanco brillante", "#e6e6e3", 0.15, M(), "", ""),
        ("Plástico negro brillante", "#1c1c1c", 0.15, M(), "", ""),
        ("Plástico mate", "#2f6fb0", 0.6, M(), "", ""),
        ("Plástico mate gris", "#7a7c7e", 0.6, M(), "", ""),
        ("Plástico mate negro", "#232323", 0.6, M(), "", ""),
        ("Plástico rugoso texturizado", "#3a3b3d", 0.75, M(), "", "Carcasas de electrodomésticos. El granulado va en el mapa de normales."),
        ("Bloque de juguete", "#d01f1f", 0.12, M(ior=1.52), "", ""),
        ("Plástico blando de juguete", "#f2a33a", 0.4, M(subsuperficie=0.2), "", ""),
        ("PVC blanco", "#e3e2dc", 0.35, M(), "", ""),
        ("Nailon", "#d9d4c5", 0.45, M(), "", ""),
        ("Policarbonato transparente", "#ffffff", 0.03, M(transparencia=1, ior=1.58), "", ""),
        ("Metacrilato", "#ffffff", 0.0, M(transparencia=1, ior=1.49), "", ""),
        ("Metacrilato de color", "#e04a6a", 0.02, M(transparencia=1, ior=1.49), "", ""),
        ("Plástico translúcido", "#dfe7ea", 0.3, M(transparencia=0.8, ior=1.5), "", "Botellas de agua y tuppers: transmisión con rugosidad."),
        ("Plástico lechoso", "#efefea", 0.35, M(subsuperficie=0.6, radio_subsuperficie=0.5), "R", ""),
        ("Goma negra", "#1e1e1e", 0.8, M(), "", ""),
        ("Neumático", "#1f1f1f", 0.85, M(), "", ""),
        ("Goma de color", "#c94a2c", 0.7, M(), "", ""),
        ("Silicona", "#cfd7d6", 0.45, M(subsuperficie=0.5, radio_subsuperficie=0.3), "R", ""),
        ("Vinilo", "#1e1e1e", 0.25, M(), "", ""),
        ("Fibra de carbono", "#1b1c1e", 0.3, M(barniz=1, anisotropia=0.5), "", "El tejido de la fibra va en una textura; el barniz da la profundidad."),
        ("Cinta aislante", "#1f1f1f", 0.4, M(), "", ""),
    ]),
    ("maderas", "Maderas", [
        ("Roble", "#a77a4e", 0.6, M(), "", "Sin textura de vetas una madera se ve como plástico: envíala a Painter."),
        ("Roble barnizado", "#9a6b3f", 0.45, M(barniz=0.8, rugosidad_barniz=0.1), "", ""),
        ("Nogal", "#6b4630", 0.55, M(), "", ""),
        ("Nogal barnizado", "#5e3c27", 0.45, M(barniz=0.9, rugosidad_barniz=0.08), "", ""),
        ("Pino", "#d1a873", 0.6, M(), "", ""),
        ("Pino tratado", "#b49d6c", 0.7, M(), "", ""),
        ("Haya", "#d4a77e", 0.55, M(), "", ""),
        ("Arce", "#e1c59c", 0.5, M(), "", ""),
        ("Cerezo", "#9c5a3c", 0.5, M(barniz=0.6), "", ""),
        ("Caoba", "#6e3426", 0.45, M(barniz=0.8), "", ""),
        ("Teca", "#9d6f42", 0.55, M(), "", ""),
        ("Ébano", "#2d2019", 0.4, M(barniz=0.7), "", ""),
        ("Bambú", "#d7c08a", 0.45, M(), "", ""),
        ("Madera envejecida", "#8d8173", 0.8, M(), "", "Madera gris de exterior, castigada por el sol."),
        ("Madera quemada", "#2a2420", 0.75, M(), "", ""),
        ("Madera pintada blanca", "#e5e2da", 0.5, M(), "", ""),
        ("Contrachapado", "#cfae83", 0.6, M(), "", ""),
        ("Tablero DM", "#a88663", 0.75, M(), "", ""),
        ("Aglomerado", "#b08f68", 0.8, M(), "", ""),
        ("Corcho", "#b68a5c", 0.85, M(), "", ""),
        ("Madera lacada piano", "#1d1d1d", 0.2, M(barniz=1, rugosidad_barniz=0.01), "", ""),
        ("Parqué", "#b3824f", 0.4, M(barniz=0.7, rugosidad_barniz=0.15), "", ""),
        ("Madera de palé", "#c1a37a", 0.85, M(), "", ""),
        ("Corteza", "#5a4a3c", 0.9, M(), "", "Necesita normal y altura: la forma la da la textura."),
    ]),
    ("piedra", "Piedra y cerámica", [
        ("Mármol blanco", "#e8e6e1", 0.15, M(subsuperficie=0.35, radio_subsuperficie=0.5), "", "El mármol deja pasar un poco de luz: subsuperficie baja."),
        ("Mármol blanco mate", "#e3e1db", 0.4, M(subsuperficie=0.3, radio_subsuperficie=0.5), "", ""),
        ("Mármol negro", "#1f1f21", 0.12, M(), "", ""),
        ("Mármol verde", "#3d5a4a", 0.15, M(), "", ""),
        ("Mármol rosa", "#d9b3a5", 0.15, M(subsuperficie=0.2), "", ""),
        ("Granito gris", "#8a8986", 0.35, M(), "", ""),
        ("Granito negro pulido", "#232325", 0.08, M(), "", ""),
        ("Pizarra", "#45494d", 0.6, M(), "", ""),
        ("Arenisca", "#c9a57c", 0.85, M(), "", ""),
        ("Caliza", "#cfc6b2", 0.8, M(), "", ""),
        ("Basalto", "#3b3a38", 0.75, M(), "", ""),
        ("Piedra pómez", "#a39f95", 0.95, M(), "", ""),
        ("Travertino", "#d8c7a6", 0.5, M(), "", ""),
        ("Obsidiana", "#1d1d20", 0.03, M(), "", ""),
        ("Jade", "#4c8a5c", 0.15, M(subsuperficie=0.8, radio_subsuperficie=0.4), "R", ""),
        ("Cuarzo", "#f2eee9", 0.05, M(transparencia=0.6, subsuperficie=0.3), "R", ""),
        ("Cerámica esmaltada blanca", "#ece8df", 0.3, M(barniz=1, rugosidad_barniz=0.03), "", "El esmalte es una capa de vidrio: barniz."),
        ("Cerámica esmaltada de color", "#2f6e8a", 0.3, M(barniz=1, rugosidad_barniz=0.03), "", ""),
        ("Porcelana", "#f3f1ec", 0.25, M(subsuperficie=0.3, radio_subsuperficie=0.2, barniz=1, rugosidad_barniz=0.02), "", ""),
        ("Gres", "#9c8b78", 0.6, M(), "", ""),
        ("Terracota", "#b2603d", 0.8, M(), "", ""),
        ("Barro cocido", "#a85a3a", 0.85, M(), "", ""),
        ("Azulejo blanco", "#f0efea", 0.1, M(barniz=0.6), "", ""),
        ("Azulejo hidráulico", "#5d7f8e", 0.4, M(), "", ""),
        ("Yeso", "#ecebe6", 0.9, M(), "", ""),
        ("Escayola", "#f1efe9", 0.85, M(), "", ""),
    ]),
    ("construccion", "Construcción", [
        ("Hormigón", "#9d9a94", 0.9, M(), "", ""),
        ("Hormigón claro", "#bdb9b0", 0.88, M(), "", ""),
        ("Hormigón pulido", "#8f8d89", 0.35, M(), "", ""),
        ("Hormigón visto", "#a3a19c", 0.85, M(), "", ""),
        ("Cemento", "#8b8a86", 0.85, M(), "", ""),
        ("Mortero", "#a59f93", 0.9, M(), "", ""),
        ("Ladrillo rojo", "#8f4a35", 0.85, M(), "", ""),
        ("Ladrillo amarillo", "#c7a76c", 0.85, M(), "", ""),
        ("Ladrillo refractario", "#c9b392", 0.85, M(), "", ""),
        ("Teja árabe", "#a6573a", 0.75, M(), "", ""),
        ("Pizarra de tejado", "#3b3f44", 0.55, M(), "", ""),
        ("Asfalto", "#3a3a3a", 0.85, M(), "", ""),
        ("Asfalto mojado", "#202021", 0.15, M(), "", "Mojado = misma piedra más oscura y con rugosidad baja."),
        ("Alquitrán", "#1d1d1d", 0.35, M(), "", ""),
        ("Pintura plástica blanca", "#ecebe7", 0.85, M(), "", "Paredes interiores. Nunca blanco puro."),
        ("Pintura plástica de color", "#c8b28a", 0.85, M(), "", ""),
        ("Gotelé", "#e7e4dd", 0.9, M(), "", ""),
        ("Pladur", "#e9e8e4", 0.9, M(), "", ""),
        ("Placa de techo", "#e2e1dc", 0.95, M(), "", ""),
        ("Cartón", "#b7916a", 0.85, M(), "", ""),
        ("Papel", "#f0eee8", 0.8, M(subsuperficie=0.15, radio_subsuperficie=0.1), "", ""),
        ("Papel kraft", "#b08a60", 0.85, M(), "", ""),
        ("Linóleo", "#6f8a7a", 0.5, M(), "", ""),
        ("Moqueta", "#5c5a63", 1.0, M(pelusa=0.5), "", ""),
        ("Chapa pintada", "#2f5f8f", 0.4, M(barniz=0.3), "", ""),
        ("Óxido", "#7a3b1e", 0.9, M(), "", "El óxido ya no es metal: metal a 0."),
    ]),
    ("terreno", "Terreno y exteriores", [
        ("Tierra seca", "#8a6e52", 0.95, M(), "", ""),
        ("Tierra húmeda", "#4d3b2c", 0.6, M(), "", ""),
        ("Barro", "#3f3125", 0.35, M(), "", ""),
        ("Arena de playa", "#d6c29a", 0.95, M(), "", ""),
        ("Arena mojada", "#9c8763", 0.5, M(), "", ""),
        ("Arena de desierto", "#d29a5f", 0.95, M(), "", ""),
        ("Grava", "#8e8a84", 0.9, M(), "", ""),
        ("Roca", "#7b7670", 0.85, M(), "", ""),
        ("Roca musgosa", "#5d6449", 0.9, M(), "", ""),
        ("Hierba", "#4f7a2e", 0.7, M(), "", "Para hierba de verdad usa geometría o instancias; esto es para el suelo lejano."),
        ("Hierba seca", "#a39556", 0.8, M(), "", ""),
        ("Musgo", "#4c6a24", 0.95, M(pelusa=0.4), "", ""),
        ("Hojarasca", "#7d5a33", 0.85, M(), "", ""),
        ("Nieve", "#e9eef2", 0.6, M(subsuperficie=0.6, radio_subsuperficie=2.0), "", "La nieve no es blanco puro y deja entrar la luz."),
        ("Nieve compacta", "#dde4ea", 0.45, M(subsuperficie=0.5, radio_subsuperficie=1.5), "", ""),
        ("Hielo", "#e6f2f7", 0.05, M(transparencia=1, ior=1.31), "", ""),
        ("Hielo opaco", "#cfe3ec", 0.3, M(transparencia=0.5, subsuperficie=0.4), "R", ""),
        ("Lava fría", "#2a2522", 0.8, M(), "", ""),
        ("Ceniza", "#7e7a75", 0.95, M(), "", ""),
        ("Carbón", "#1f1f1d", 0.7, M(), "", "Uno de los materiales más oscuros: ~4 % de reflejo."),
    ]),
    ("transparentes", "Vidrio y líquidos", [
        ("Vidrio de ventana", "#ffffff", 0.0, M(transparencia=1, ior=1.52, pared_fina=True), "", "Pared fina: el cristal plano de una ventana no refracta."),
        ("Vidrio", "#ffffff", 0.0, M(transparencia=1, ior=1.52), "", ""),
        ("Vidrio grueso", "#eaf4f1", 0.0, M(transparencia=1, ior=1.52, color_transmision="#cfe9e1", profundidad_transmision=5.0), "", "El color del vidrio grueso se nota más donde es más gordo: profundidad."),
        ("Vidrio de botella verde", "#3f7d4a", 0.0, M(transparencia=1, ior=1.52, profundidad_transmision=20.0), "", ""),
        ("Vidrio ámbar", "#b06a1d", 0.0, M(transparencia=1, ior=1.52, profundidad_transmision=20.0), "", ""),
        ("Vidrio azul", "#2f5fa0", 0.0, M(transparencia=1, ior=1.52, profundidad_transmision=20.0), "", ""),
        ("Vidrio esmerilado", "#f1f5f5", 0.35, M(transparencia=1, ior=1.52), "", ""),
        ("Vidrio tintado", "#5a5f63", 0.0, M(transparencia=1, ior=1.52, pared_fina=True), "", ""),
        ("Cristal tallado", "#ffffff", 0.0, M(transparencia=1, ior=1.6), "", ""),
        ("Diamante", "#ffffff", 0.0, M(transparencia=1, ior=2.42), "R", ""),
        ("Lente", "#ffffff", 0.0, M(transparencia=1, ior=1.52, barniz=1, color_barniz="#d8e8ff"), "R", ""),
        ("Agua", "#ffffff", 0.0, M(transparencia=1, ior=1.333), "", ""),
        ("Agua de mar", "#1f6b6a", 0.02, M(transparencia=1, ior=1.34, color_transmision="#5fa8a0", profundidad_transmision=50.0), "", ""),
        ("Agua turbia", "#5a5a3a", 0.05, M(transparencia=0.8, subsuperficie=0.4, ior=1.333), "R", ""),
        ("Burbuja de jabón", "#ffffff", 0.0, M(transparencia=1, ior=1.33, pared_fina=True, pelicula=1, grosor_pelicula=380), "R", ""),
        ("Leche", "#f4f2ea", 0.2, M(subsuperficie=1, radio_subsuperficie=0.3, ior=1.35), "R", ""),
        ("Zumo de naranja", "#f09a1a", 0.1, M(transparencia=0.5, subsuperficie=0.6, ior=1.35), "R", ""),
        ("Vino tinto", "#5a0f19", 0.0, M(transparencia=1, ior=1.35, profundidad_transmision=10.0), "", ""),
        ("Vino blanco", "#e8d98f", 0.0, M(transparencia=1, ior=1.35, profundidad_transmision=15.0), "", ""),
        ("Cerveza", "#c98a1c", 0.0, M(transparencia=1, ior=1.34, profundidad_transmision=15.0), "", ""),
        ("Refresco de cola", "#3a1608", 0.0, M(transparencia=1, ior=1.34, profundidad_transmision=8.0), "", ""),
        ("Aceite", "#c8a62c", 0.0, M(transparencia=1, ior=1.47, profundidad_transmision=12.0), "", ""),
        ("Miel", "#d08a12", 0.05, M(transparencia=1, subsuperficie=0.3, ior=1.5, profundidad_transmision=10.0), "R", ""),
        ("Gelatina", "#d43a5a", 0.1, M(transparencia=0.8, subsuperficie=0.5), "R", ""),
    ]),
    ("telas", "Telas y piel animal", [
        ("Algodón", "#e2ded4", 0.9, M(pelusa=0.6), "", "La pelusa da el brillo suave del borde de las telas."),
        ("Algodón de color", "#7d2f3a", 0.9, M(pelusa=0.6), "", ""),
        ("Lino", "#cfc4ad", 0.85, M(pelusa=0.4), "", ""),
        ("Lana", "#a8a094", 0.95, M(pelusa=1, rugosidad_pelusa=0.7), "", ""),
        ("Fieltro", "#4a5a6a", 1.0, M(pelusa=0.9), "", ""),
        ("Terciopelo", "#5a1838", 0.8, M(pelusa=1, rugosidad_pelusa=0.3), "", ""),
        ("Terciopelo azul", "#1a2f5a", 0.8, M(pelusa=1, rugosidad_pelusa=0.3), "", ""),
        ("Seda", "#d8c7a0", 0.3, M(anisotropia=0.8, pelusa=0.2), "", ""),
        ("Satén", "#b81f3a", 0.25, M(anisotropia=0.6), "", ""),
        ("Vaquero", "#33476b", 0.9, M(pelusa=0.5), "", ""),
        ("Lona", "#b9ad8c", 0.85, M(), "", ""),
        ("Poliéster deportivo", "#2a6ad1", 0.45, M(), "", ""),
        ("Toalla", "#f1efe8", 1.0, M(pelusa=1, rugosidad_pelusa=0.8), "", ""),
        ("Cuero", "#5a3420", 0.55, M(), "", ""),
        ("Cuero negro", "#221d1a", 0.45, M(), "", ""),
        ("Cuero brillante", "#3a1f14", 0.3, M(barniz=0.6, rugosidad_barniz=0.15), "", ""),
        ("Ante", "#9a7650", 0.95, M(pelusa=0.7), "", ""),
        ("Piel sintética", "#2a2a2a", 0.35, M(barniz=0.4), "", ""),
        ("Pelo corto", "#5a4532", 0.7, M(pelusa=1, rugosidad_pelusa=0.5), "", "Para pelo real usa XGen; esto es para peluches o pelo lejano."),
        ("Pluma", "#e8e4da", 0.6, M(anisotropia=0.4, pelusa=0.3), "", ""),
    ]),
    ("organicos", "Piel y orgánicos", [
        ("Piel clara", "#e3b49b", 0.45, M(subsuperficie=1, radio_subsuperficie=0.3), "R", "La piel deja pasar la luz y la devuelve rojiza. Trabaja a escala real (1 unidad = 1 cm)."),
        ("Piel media", "#c58c6a", 0.45, M(subsuperficie=1, radio_subsuperficie=0.3), "R", ""),
        ("Piel oscura", "#7a4b34", 0.45, M(subsuperficie=1, radio_subsuperficie=0.25), "R", ""),
        ("Piel (juego)", "#d1a083", 0.5, M(), "J", "En motor la subsuperficie se configura en el propio motor."),
        ("Labios", "#b55a5a", 0.3, M(subsuperficie=1, radio_subsuperficie=0.2), "R", ""),
        ("Uña", "#e7c1b5", 0.2, M(barniz=0.6, subsuperficie=0.4), "R", ""),
        ("Diente", "#f0eadb", 0.2, M(subsuperficie=0.6, radio_subsuperficie=0.2, barniz=0.8), "R", ""),
        ("Ojo (esclerótica)", "#f1ece6", 0.2, M(subsuperficie=0.5, barniz=1, rugosidad_barniz=0.0), "R", ""),
        ("Hueso", "#e3d9c2", 0.6, M(subsuperficie=0.3), "", ""),
        ("Cera de vela", "#efe2b8", 0.35, M(subsuperficie=1, radio_subsuperficie=1.0), "R", ""),
        ("Jabón", "#d7ecd9", 0.3, M(subsuperficie=1, radio_subsuperficie=0.8), "R", ""),
        ("Plastilina", "#c74d3a", 0.55, M(subsuperficie=0.3), "", ""),
        ("Hoja verde", "#3f6b22", 0.45, M(subsuperficie=0.5, pared_fina=True, transparencia=0.2), "R", "Pared fina con algo de transmisión: la luz atraviesa la hoja."),
        ("Hoja (juego)", "#47722a", 0.5, M(), "J", "Usa una textura con alfa para recortar la silueta."),
        ("Pétalo", "#e8789a", 0.4, M(subsuperficie=0.6, pared_fina=True, transparencia=0.3), "R", ""),
        ("Coral", "#e86a52", 0.7, M(subsuperficie=0.4), "", ""),
        ("Concha", "#efe3d6", 0.25, M(pelicula=0.6, grosor_pelicula=550, barniz=0.5), "R", "El nácar es una película fina."),
        ("Caparazón de insecto", "#1d3a2a", 0.2, M(pelicula=0.7, grosor_pelicula=600, barniz=1), "R", ""),
    ]),
    ("comida", "Comida", [
        ("Manzana roja", "#a3141a", 0.3, M(subsuperficie=0.4, barniz=0.5), "", ""),
        ("Manzana verde", "#7aa83a", 0.3, M(subsuperficie=0.4, barniz=0.5), "", ""),
        ("Naranja", "#e87a12", 0.45, M(subsuperficie=0.5), "", ""),
        ("Limón", "#e8d21f", 0.4, M(subsuperficie=0.5), "", ""),
        ("Plátano", "#e6c840", 0.5, M(subsuperficie=0.3), "", ""),
        ("Uva", "#4a1d3a", 0.2, M(subsuperficie=0.8, barniz=0.6), "R", ""),
        ("Fresa", "#c01e2a", 0.35, M(subsuperficie=0.6, barniz=0.4), "", ""),
        ("Tomate", "#c42a16", 0.2, M(subsuperficie=0.5, barniz=0.8), "", ""),
        ("Pan", "#c58a4a", 0.85, M(), "", ""),
        ("Corteza de pan tostada", "#8a4a1e", 0.7, M(), "", ""),
        ("Queso", "#f0c860", 0.45, M(subsuperficie=0.7, radio_subsuperficie=0.3), "", ""),
        ("Mantequilla", "#f3dc8a", 0.4, M(subsuperficie=0.8), "R", ""),
        ("Chocolate", "#4a2716", 0.4, M(), "", ""),
        ("Chocolate con leche", "#7a4a2a", 0.35, M(), "", ""),
        ("Caramelo duro", "#c2381c", 0.05, M(transparencia=0.8, subsuperficie=0.3), "R", ""),
        ("Carne cruda", "#a33a35", 0.4, M(subsuperficie=0.8, radio_subsuperficie=0.3), "R", ""),
        ("Carne asada", "#5a2a18", 0.6, M(), "", ""),
        ("Huevo (cáscara)", "#e6d2b5", 0.6, M(subsuperficie=0.2), "", ""),
        ("Yema", "#f0a41a", 0.15, M(subsuperficie=0.8), "R", ""),
        ("Glaseado", "#f2c6d6", 0.2, M(subsuperficie=0.4, barniz=0.5), "", ""),
        ("Café", "#3a1c0e", 0.0, M(transparencia=0.6, ior=1.34), "", ""),
    ]),
    ("pinturas", "Pinturas y lacas", [
        ("Pintura de coche roja", "#9c1b1b", 0.4, M(barniz=1, rugosidad_barniz=0.02), "", "Pintura de coche = color debajo y barniz transparente encima."),
        ("Pintura de coche azul", "#123a7a", 0.4, M(barniz=1, rugosidad_barniz=0.02), "", ""),
        ("Pintura de coche negra", "#1c1c1e", 0.4, M(barniz=1, rugosidad_barniz=0.02), "", ""),
        ("Pintura de coche blanca", "#e8e8e4", 0.4, M(barniz=1, rugosidad_barniz=0.02), "", ""),
        ("Pintura metalizada plata", "L:0.70,0.70,0.70", 0.35, M(metal=1, barniz=1, rugosidad_barniz=0.02), "", "Metalizada: metal debajo y barniz encima. Los destellos irían en textura."),
        ("Pintura metalizada gris", "L:0.40,0.41,0.43", 0.35, M(metal=1, barniz=1, rugosidad_barniz=0.02), "", ""),
        ("Pintura metalizada azul", "L:0.15,0.25,0.60", 0.35, M(metal=1, barniz=1, rugosidad_barniz=0.02), "", ""),
        ("Pintura perlada", "#f2eee8", 0.35, M(barniz=1, pelicula=0.5, grosor_pelicula=500), "R", ""),
        ("Pintura mate", "#4a5a3a", 0.75, M(), "", ""),
        ("Pintura satinada", "#d8d2c4", 0.45, M(), "", ""),
        ("Esmalte brillante", "#1f5f3a", 0.15, M(barniz=0.5), "", ""),
        ("Laca negra", "#1c1c1c", 0.1, M(barniz=1, rugosidad_barniz=0.01), "", ""),
        ("Laca roja", "#8a1010", 0.1, M(barniz=1, rugosidad_barniz=0.01), "", ""),
        ("Pintura de pizarra", "#25292a", 0.85, M(), "", ""),
        ("Pintura en polvo", "#3a3a3c", 0.5, M(), "", "Pintura de maquinaria y radiadores."),
        ("Barniz sobre madera", "#a77a4e", 0.6, M(barniz=1, rugosidad_barniz=0.05), "", ""),
        ("Pintura de juguete", "#e83a2a", 0.3, M(barniz=0.5), "", ""),
    ]),
    ("luces", "Luces y pantallas", [
        ("Neón rosa", "#ff4fa0", 0.3, M(emision=0.6), "", "La emisión ilumina en Arnold pero hace ruido: para iluminar, usa una luz de malla."),
        ("Neón azul", "#3fa8ff", 0.3, M(emision=0.6), "", ""),
        ("Neón verde", "#3fff7a", 0.3, M(emision=0.6), "", ""),
        ("Neón rojo", "#ff3a2a", 0.3, M(emision=0.6), "", ""),
        ("Pantalla encendida", "#9fd4ff", 0.1, M(emision=0.45, barniz=1), "", ""),
        ("Pantalla apagada", "#1b1c1f", 0.05, M(barniz=1, rugosidad_barniz=0.0), "", ""),
        ("LED blanco", "#ffffff", 0.3, M(emision=0.7), "", ""),
        ("Bombilla cálida", "#ffc07a", 0.2, M(emision=0.8), "", ""),
        ("Piloto rojo", "#ff2a1a", 0.2, M(emision=0.3, barniz=1), "", ""),
        ("Piloto verde", "#3aff3a", 0.2, M(emision=0.3, barniz=1), "", ""),
        ("Lava", "#ff5a0a", 0.6, M(emision=0.7), "", ""),
        ("Brasas", "#ff3a0a", 0.8, M(emision=0.45), "", ""),
        ("Fluorescente", "#c9ff3a", 0.4, M(emision=0.35), "", ""),
        ("Cielo de fondo", "#8fb8e8", 1.0, M(emision=0.35), "", ""),
        ("Holograma", "#3ae8ff", 0.2, M(emision=0.5, opacidad=0.4, pared_fina=True), "", ""),
    ]),
    ("arcilla", "Arcilla y presentación", [
        ("Clay gris", "#a8a39a", 0.7, M(), "", "Para presentar el modelo sin distraer con el color."),
        ("Clay blanco", "#d9d6cf", 0.7, M(), "", ""),
        ("Clay terracota", "#b06a4a", 0.7, M(), "", ""),
        ("Clay oscuro", "#4f4c48", 0.6, M(), "", ""),
        ("Clay brillante", "#b3aea6", 0.35, M(), "", ""),
        ("Maqueta de papel", "#efede6", 0.85, M(subsuperficie=0.15), "", ""),
        ("Maqueta de madera", "#d9b88a", 0.65, M(), "", ""),
        ("Plástico de impresión 3D", "#e8e6e0", 0.45, M(), "", ""),
        ("Resina", "#c8b89a", 0.2, M(subsuperficie=0.3), "", ""),
        ("Bronce de escultura", "L:0.60,0.42,0.28", 0.4, M(metal=1), "", ""),
        ("Escayola de escultura", "#ebe8e0", 0.85, M(subsuperficie=0.2), "", ""),
        ("Comprobar normales", CROMO, 0.0, M(metal=1), "", "Un cromo gris deja ver cualquier bache o normal girada."),
    ]),
]

DESTINOS = {"": ["render", "juego"], "R": ["render"], "J": ["juego"]}


def generar():
    os.makedirs(SALIDA, exist_ok=True)
    indice = []
    total = 0
    nombres = set()
    for orden, (clave, nombre, filas) in enumerate(FAMILIAS):
        recetas = []
        for fila in filas:
            n, color, rugosidad, extras, destinos, nota = fila
            if n in nombres:
                raise SystemExit("receta repetida: " + n)
            nombres.add(n)
            datos = dict(nombre=n, familia=clave, color=c(color), rugosidad=rugosidad,
                         destinos=DESTINOS[destinos], nota=nota)
            for k, v in extras.items():
                datos[k] = c(v) if isinstance(v, str) and k.startswith("color") else v
            r = rc.normalizar(datos)
            # Solo se guarda lo que no es el valor por defecto (archivos legibles).
            compacta = {"nombre": r["nombre"]}
            for k in rc.DEFECTO:
                if k in ("nombre", "familia"):
                    continue
                if r[k] != rc.DEFECTO[k]:
                    compacta[k] = r[k]
            recetas.append(compacta)
        ruta = os.path.join(SALIDA, "{:02d}_{}.json".format(orden + 1, clave))
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"familia": clave, "nombre": nombre, "recetas": recetas}, f, ensure_ascii=False, indent=1)
            f.write("\n")
        indice.append((nombre, len(recetas)))
        total += len(recetas)
    for nombre, n in indice:
        print("{:28s}{:4d}".format(nombre, n))
    print("{:28s}{:4d}".format("Total", total))


if __name__ == "__main__":
    generar()
