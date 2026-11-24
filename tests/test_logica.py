"""Pruebas sin Maya de la lógica de Materials (recetas, comprobación, texturas, intercambio, biblioteca).

    python3 -m unittest discover tests
"""

import json
import os
import re
import shutil
import struct
import sys
import tempfile
import types
import unittest
import zlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

from materials import biblioteca as bib  # noqa: E402
from materials import color as col  # noqa: E402
from materials import comprobacion as chk  # noqa: E402
from materials import intercambio as ic  # noqa: E402
from materials import receta as rc  # noqa: E402
from materials import texturas as tx  # noqa: E402
from materials import vista_previa as vp  # noqa: E402
from materials.i18n import claves  # noqa: E402


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def png(ruta, ancho, alto):
    """PNG gris mínimo, sin librerías."""
    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xffffffff)
    filas = b"".join(b"\x00" + b"\x80" * ancho for _ in range(alto))
    with open(ruta, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 0, 0, 0, 0)) +
                bloque(b"IDAT", zlib.compress(filas)) + bloque(b"IEND", b""))


class PruebaColor(unittest.TestCase):
    def test_ida_y_vuelta(self):
        for h in ("#000000", "#ffffff", "#9c1b1b", "#2f6fb0", "#808080"):
            self.assertEqual(col.lineal_a_hex(col.hex_a_lineal(h)), h)

    def test_acescg(self):
        rgb = (0.2, 0.5, 0.8)
        ida = col.a_espacio_render(rgb, "ACEScg")
        self.assertNotAlmostEqual(ida[0], rgb[0], places=3)
        vuelta = col.desde_espacio_render(ida, "ACES - ACEScg")
        for a, b in zip(rgb, vuelta):
            self.assertAlmostEqual(a, b, places=3)
        self.assertEqual(col.a_espacio_render(rgb, "scene-linear Rec.709-sRGB"), rgb)
        # El blanco sigue siendo blanco.
        for c in col.a_espacio_render((1, 1, 1), "ACEScg"):
            self.assertAlmostEqual(c, 1.0, places=3)

    def test_hex_invalido(self):
        self.assertFalse(col.hex_valido("rojo"))
        with self.assertRaises(ValueError):
            col.hex_a_srgb("#12")


class PruebaReceta(unittest.TestCase):
    def test_normalizar_limita(self):
        r = rc.normalizar({"rugosidad": 4, "metal": -1, "color": "nada", "ior": 9, "pared_fina": 1, "x": 3})
        self.assertEqual(r["rugosidad"], 1.0)
        self.assertEqual(r["metal"], 0.0)
        self.assertEqual(r["color"], rc.DEFECTO["color"])
        self.assertEqual(r["ior"], 3.0)
        self.assertIs(r["pared_fina"], True)
        self.assertNotIn("x", r)

    def test_atributos_openpbr(self):
        r = rc.nueva(color="#ff0000", rugosidad=0.3, metal=1, barniz=0.5, emision=0.5)
        a = rc.atributos_openpbr(r)
        self.assertAlmostEqual(a["specularRoughness"], 0.3)
        self.assertEqual(a["baseMetalness"], 1.0)
        self.assertEqual(a["coatWeight"], 0.5)
        self.assertAlmostEqual(a["baseColor"][0], 1.0, places=4)
        self.assertGreater(a["emissionLuminance"], 0)
        for nombre in a:
            self.assertRegex(nombre, r"^[a-z][A-Za-z]+$")

    def test_ida_y_vuelta_atributos(self):
        r = rc.nueva(nombre="Prueba", color="#336699", rugosidad=0.42, metal=0, transparencia=0.3, subsuperficie=0.2,
                     barniz=0.7, pelusa=0.1, emision=0.25, ior=1.45, color_subsuperficie="#aa0000")
        vuelta = rc.desde_atributos(rc.atributos_openpbr(r), nombre="Prueba")
        self.assertEqual(rc.diferencias(r, vuelta, tolerancia=0.01), [])

    def test_para_juego(self):
        r = rc.para_juego(rc.nueva(transparencia=1, subsuperficie=1, barniz=1, pelusa=1, metal=0.7, pelicula=1))
        self.assertEqual((r["transparencia"], r["subsuperficie"], r["barniz"], r["pelusa"], r["pelicula"]),
                         (0, 0, 0, 0, 0))
        self.assertEqual(r["metal"], 1.0)
        self.assertLess(r["opacidad"], 0.5)
        a = rc.atributos_openpbr(rc.nueva(barniz=1, transparencia=1), rc.JUEGO)
        self.assertEqual(a["coatWeight"], 0)
        self.assertEqual(a["transmissionWeight"], 0)

    def test_emision(self):
        self.assertEqual(rc.emision_a_nits(0), 0)
        for v in (0.1, 0.5, 1.0):
            self.assertAlmostEqual(rc.nits_a_emision(rc.emision_a_nits(v)), v, places=6)

    def test_nombre_material(self):
        self.assertEqual(rc.nombre_material("Pintura de coche"), "M_Pintura_de_coche")
        self.assertEqual(rc.nombre_material("Ébano / 2"), "M_Ebano_2")
        self.assertEqual(rc.nombre_material("M_Oro"), "M_Oro")
        self.assertEqual(rc.nombre_material("3D"), "M__3D")
        self.assertEqual(rc.nombre_material(""), "M_Material")


class PruebaComprobacion(unittest.TestCase):
    def claves(self, receta, destino=rc.RENDER, texturas=None):
        return [c for _, c, _ in chk.comprobar(receta, destino, texturas)]

    def test_ok(self):
        self.assertEqual(self.claves(rc.nueva(color="#808080")), ["chk_ok"])
        self.assertEqual(self.claves(rc.nueva(color="#808080"), rc.JUEGO), ["chk_ok_juego"])

    def test_avisos(self):
        self.assertIn("chk_oscuro", self.claves(rc.nueva(color="#050505")))
        self.assertIn("chk_claro", self.claves(rc.nueva(color="#ffffff")))
        self.assertIn("chk_metal_oscuro", self.claves(rc.nueva(color="#202020", metal=1)))
        self.assertIn("chk_metal_medias", self.claves(rc.nueva(metal=0.5)))
        self.assertIn("chk_juego_apagados", self.claves(rc.nueva(barniz=1), rc.JUEGO))
        self.assertIn("chk_receta_render", self.claves(rc.nueva(destinos=["render"]), rc.JUEGO))
        # Con textura de metal, el metal a medias no avisa.
        self.assertNotIn("chk_metal_medias", self.claves(rc.nueva(metal=0.5), texturas={"metal": {}}))
        # Subsuperficie en un objeto pequeño (radio en unidades de escena).
        piel = rc.nueva(subsuperficie=1, radio_subsuperficie=1.0)
        self.assertIn("chk_sss_escala", [c for _, c, _ in chk.comprobar(piel, rc.RENDER, tamano=1.8)])
        self.assertNotIn("chk_sss_escala", [c for _, c, _ in chk.comprobar(piel, rc.RENDER, tamano=20)])

    def test_texturas(self):
        tex = {"rugosidad": {"espacio": "sRGB", "nombre": "r.png"},
               "color": {"espacio": "Raw", "nombre": "c.png", "tamano": (1000, 1000)}}
        claves = self.claves(rc.nueva(), rc.JUEGO, tex)
        self.assertIn("chk_tex_dato_srgb", claves)
        self.assertIn("chk_tex_color_raw", claves)
        self.assertIn("chk_tex_potencia", claves)

    def test_todos_los_avisos_tienen_texto(self):
        codigo = leer(os.path.join(RAIZ, "scripts", "materials", "comprobacion.py"))
        for clave in set(re.findall(r'"(chk_[a-z_]+)"', codigo)):
            self.assertIn(clave, claves(), clave)


class PruebaTexturas(unittest.TestCase):
    CASOS = {
        # Painter, plantilla de Materials y plantillas de Adobe
        "silla_Madera_BaseColor.1001.png": ("color", "silla_Madera"),
        "Madera_Normal_OpenGL.png": ("normal", "Madera"),
        "Madera_Normal_DirectX.png": ("normal", "Madera"),
        "Madera_OcclusionRoughnessMetallic.png": ("orm", "Madera"),
        "Madera_BaseMap.png": ("color", "Madera"),
        "Madera_MaskMap.png": ("mascara_unity", "Madera"),
        "silla_Madera_Metalness.png": ("metal", "silla_Madera"),
        "silla_Madera_Emissive.png": ("emision", "silla_Madera"),
        "silla_Madera_Height.png": ("altura", "silla_Madera"),
        # Poly Haven
        "rock_wall_diff_2k.jpg": ("color", "rock_wall"),
        "rock_wall_nor_gl_2k.exr": ("normal", "rock_wall"),
        "rock_wall_arm_2k.jpg": ("orm", "rock_wall"),
        "rock_wall_disp_2k.png": ("altura", "rock_wall"),
        "rock_wall_rough_2k.jpg": ("rugosidad", "rock_wall"),
        # Otros
        "T_Caja_ORM.tga": ("orm", "T_Caja"),
        "brick-Glossiness-4096.jpg": ("brillo", "brick"),
        "Wood066_4K-PNG_Color.png": ("color", "Wood066_4K_PNG"),
        "metal_panel_AmbientOcclusion.png": ("ao", "metal_panel"),
        "Base_color.png": ("color", ""),
    }

    def test_reconocer(self):
        for nombre, (tipo, prefijo) in self.CASOS.items():
            r = tx.reconocer(nombre)
            self.assertIsNotNone(r, nombre)
            self.assertEqual((r[0], r[1]), (tipo, prefijo), nombre)
        self.assertIsNone(tx.reconocer("foto_vacaciones.png"))
        self.assertIsNone(tx.reconocer("notas.txt"))

    def test_convencion_normal(self):
        self.assertEqual(tx.reconocer("a_Normal_DirectX.png")[2], "directx")
        self.assertEqual(tx.reconocer("a_nor_gl_1k.png")[2], "opengl")
        self.assertIsNone(tx.reconocer("a_Normal.png")[2])

    def test_udim(self):
        r = tx.reconocer("silla_Madera_BaseColor.1003.png")
        self.assertTrue(r[3])
        self.assertEqual(r[4], "silla_Madera_BaseColor.<UDIM>.png")
        juegos = tx.analizar(["/t/silla_Madera_BaseColor.1001.png", "/t/silla_Madera_BaseColor.1002.png",
                              "/t/silla_Madera_Roughness.1001.png"])
        juego = juegos["silla_madera"]
        self.assertEqual(len(juego.mapas["color"].tiles), 2)
        self.assertTrue(juego.conexiones["color"].como_dict()["ruta"].endswith("<UDIM>.png"))
        self.assertEqual(juego.ignorados, [])

    def test_analizar_painter_arnold(self):
        rutas = ["/p/silla_Madera_{}.png".format(m) for m in
                 ("BaseColor", "Roughness", "Metallic", "Normal_OpenGL", "Height", "Emissive", "Opacity")]
        rutas += ["/p/silla_Metal_BaseColor.png", "/p/silla_Metal_Roughness.png"]
        juegos = tx.analizar(rutas)
        self.assertEqual(set(juegos), {"silla_madera", "silla_metal"})
        madera = juegos["silla_madera"]
        self.assertEqual(madera.nombre, "Madera")
        self.assertEqual(set(madera.conexiones), {"color", "rugosidad", "metal", "normal", "altura", "emision",
                                                  "opacidad"})
        self.assertEqual(madera.conexiones["color"].espacio, "sRGB")
        self.assertEqual(madera.conexiones["rugosidad"].espacio, "Raw")
        self.assertEqual(madera.conexiones["normal"].mapa.convencion, "opengl")

    def test_analizar_motores(self):
        unreal = tx.analizar(["/u/Caja_BaseColor.png", "/u/Caja_OcclusionRoughnessMetallic.png",
                              "/u/Caja_Normal_DirectX.png"])["caja"]
        self.assertEqual(unreal.conexiones["rugosidad"].canal, "G")
        self.assertEqual(unreal.conexiones["metal"].canal, "B")
        self.assertEqual(unreal.conexiones["normal"].mapa.convencion, "directx")
        unity = tx.analizar(["/u/Caja_BaseMap.png", "/u/Caja_MaskMap.png", "/u/Caja_Normal_OpenGL.png"])["caja"]
        self.assertEqual(unity.conexiones["metal"].canal, "R")
        self.assertEqual(unity.conexiones["rugosidad"].canal, "A")
        self.assertTrue(unity.conexiones["rugosidad"].invertir)
        # Maya lee la MaskMap premultiplicada: el metal se divide por el alfa.
        self.assertTrue(unity.conexiones["metal"].como_dict()["dividir_alfa"])
        self.assertFalse(unreal.conexiones["metal"].como_dict()["dividir_alfa"])

    def test_brillo_y_ao(self):
        juego = tx.analizar(["/b/brick_Color.jpg", "/b/brick_Glossiness.jpg", "/b/brick_AO.jpg"])["brick"]
        self.assertTrue(juego.conexiones["rugosidad"].invertir)
        self.assertIn(("brick_AO.jpg", "ao"), juego.ignorados)

    def test_normal_por_defecto(self):
        juego = tx.analizar(["/n/x_Normal.png"], normal_por_defecto="directx")["x"]
        self.assertEqual(juego.conexiones["normal"].mapa.convencion, "directx")

    def test_buscar_material(self):
        materiales = ["M_Madera", "metal_mat", "lambert1", "pCubeSG"]
        self.assertEqual(tx.buscar_material("Madera", materiales), "M_Madera")
        self.assertEqual(tx.buscar_material("Metal", materiales), "metal_mat")
        self.assertIsNone(tx.buscar_material("Vidrio", materiales))
        self.assertIsNone(tx.buscar_material("", materiales))

    def test_rutas(self):
        proyecto = os.path.join(os.sep, "proy")
        dentro = os.path.join(proyecto, "sourceimages", "a.png")
        self.assertEqual(tx.relativa_al_proyecto(dentro, proyecto), "sourceimages/a.png")
        fuera = os.path.join(os.sep, "otra", "a.png")
        self.assertEqual(tx.relativa_al_proyecto(fuera, proyecto), fuera)
        self.assertEqual(tx.nombre_de_ruta(r"C:\Users\ana\tex\silla.png"), "silla.png")
        self.assertEqual(tx.nombre_de_ruta("/Users/ana/tex/silla.png"), "silla.png")

    def test_tamano_y_busqueda(self):
        carpeta = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(carpeta, "sub"))
            ruta = os.path.join(carpeta, "sub", "Caja_BaseColor.png")
            png(ruta, 300, 200)
            self.assertEqual(tx.tamano_imagen(ruta), (300, 200))
            self.assertEqual(tx.buscar_por_nombre("caja_basecolor.png", [carpeta]), ruta)
            self.assertEqual(tx.listar_imagenes(carpeta, recursivo=True), [ruta])
            self.assertEqual(tx.listar_imagenes(carpeta), [])
        finally:
            shutil.rmtree(carpeta)


class PruebaIntercambio(unittest.TestCase):
    def setUp(self):
        self.casa = tempfile.mkdtemp()
        self.proyecto = tempfile.mkdtemp()
        os.environ["MATERIALS_CASA"] = self.casa

    def tearDown(self):
        os.environ.pop("MATERIALS_CASA", None)
        shutil.rmtree(self.casa)
        shutil.rmtree(self.proyecto)

    def test_ida_y_vuelta(self):
        carpeta = ic.carpeta_envio(self.proyecto, "|grupo|silla:Silla Roja")
        self.assertTrue(carpeta.endswith(os.path.join("materials", "Silla_Roja")))
        receta = ic.nueva_receta_envio("Silla_Roja", os.path.join(carpeta, "Silla_Roja.fbx"),
                                       {"Madera": rc.nueva(nombre="Madera")}, "juego", "unreal", 1024)
        self.assertEqual(receta["normal"], "directx")
        ic.enviar(carpeta, receta)
        avisos = ic.avisos_pendientes()
        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]["objeto"], "Silla_Roja")
        self.assertEqual(ic.envios_del_proyecto(self.proyecto), [carpeta])
        self.assertIsNone(ic.leer_manifiesto(carpeta))
        self.assertIsNone(ic.huella_manifiesto(carpeta))
        textura = os.path.join(carpeta, "texturas", "Madera_BaseColor.png")
        png(textura, 4, 4)
        ic.escribir_manifiesto(carpeta, {"Madera": [textura]})
        m = ic.leer_manifiesto(carpeta)
        self.assertEqual(m["contador"], 1)
        self.assertEqual(m["juegos"]["Madera"], [os.path.abspath(textura)])
        ic.escribir_manifiesto(carpeta, {"Madera": [textura]})
        self.assertEqual(ic.leer_manifiesto(carpeta)["contador"], 2)
        self.assertIsNotNone(ic.huella_manifiesto(carpeta))
        # Reenviar aparta el manifiesto viejo para no reconectar texturas antiguas.
        ic.enviar(carpeta, receta)
        self.assertIsNone(ic.leer_manifiesto(carpeta))
        self.assertTrue(os.path.isfile(os.path.join(carpeta, "manifiesto_anterior.json")))

    def test_manifiesto_movido(self):
        carpeta = ic.carpeta_envio(self.proyecto, "caja")
        os.makedirs(os.path.join(carpeta, "texturas"))
        png(os.path.join(carpeta, "texturas", "Caja_BaseColor.png"), 2, 2)
        ic.escribir_json(os.path.join(carpeta, ic.MANIFIESTO),
                         {"juegos": {"Caja": [r"D:\otro\ordenador\texturas\Caja_BaseColor.png"]}})
        m = ic.leer_manifiesto(carpeta)
        self.assertEqual(m["juegos"]["Caja"], [os.path.join(carpeta, "texturas", "Caja_BaseColor.png")])

    def test_json_roto(self):
        ruta = os.path.join(self.casa, "roto.json")
        with open(ruta, "w") as f:
            f.write("{")
        self.assertIsNone(ic.leer_json(ruta))


class PruebaBiblioteca(unittest.TestCase):
    def test_grande_y_valida(self):
        familias = bib.familias_del_plugin()
        self.assertGreaterEqual(len(familias), 12)
        total = 0
        nombres = set()
        for f in familias:
            self.assertGreaterEqual(len(f.recetas), 12, f.nombre)
            for r in f.recetas:
                self.assertNotIn(r["nombre"], nombres)
                nombres.add(r["nombre"])
                self.assertEqual(r, dict(rc.normalizar(r), familia=r["familia"], origen="plugin"))
                total += 1
        self.assertGreaterEqual(total, 250)

    def test_destinos(self):
        todas = [r for f in bib.familias_del_plugin() for r in f.recetas]
        solo_render = [r for r in todas if r["destinos"] == ["render"]]
        solo_juego = [r for r in todas if r["destinos"] == ["juego"]]
        self.assertTrue(solo_render and solo_juego)
        for r in todas:
            if r["metal"] not in (0.0, 1.0):
                self.fail("metal a medias en " + r["nombre"])
            if rc.sirve_para(r, rc.JUEGO) and r["pelicula"] > 0:
                self.fail("película en receta de juego: " + r["nombre"])

    def test_comprobacion_de_la_biblioteca(self):
        """Las recetas del plugin no deben dar avisos físicos (salvo las que lo explican en su nota)."""
        for f in bib.familias_del_plugin():
            for r in f.recetas:
                destino = rc.RENDER if rc.sirve_para(r, rc.RENDER) else rc.JUEGO
                avisos = [c for n, c, _ in chk.comprobar(r, destino) if n == chk.AVISO]
                self.assertEqual(avisos, [], r["nombre"])

    def test_buscar_y_guardar(self):
        carpeta = tempfile.mkdtemp()
        clase = tempfile.mkdtemp()
        try:
            with open(os.path.join(clase, "familia.json"), "w", encoding="utf-8") as f:
                json.dump({"recetas": [{"nombre": "Metal del profe", "metal": 1, "color": "#cccccc"}]}, f)
            b = bib.Biblioteca(carpeta, clase)
            self.assertTrue(b.buscar("marmol"))
            self.assertTrue(all("Mármol" in r["nombre"] or "mármol" in r.get("nota", "").lower()
                                for r in b.buscar("marmol")))
            self.assertTrue(b.buscar("vidrio", familia="transparentes"))
            self.assertFalse([r for r in b.buscar("", destino=rc.JUEGO) if not rc.sirve_para(r, rc.JUEGO)])
            self.assertEqual(b.familia(bib.CLASE).recetas[0]["nombre"], "Metal del profe")
            ruta = b.guardar_mia(rc.nueva(nombre="Mi rojo", color="#aa0000"))
            self.assertTrue(os.path.isfile(ruta))
            mias = b.familia(bib.MIS_RECETAS).recetas
            self.assertEqual([r["nombre"] for r in mias], ["Mi rojo"])
            self.assertTrue(b.borrar_mia(mias[0]))
            self.assertEqual(b.familia(bib.MIS_RECETAS).recetas, [])
        finally:
            shutil.rmtree(carpeta)
            shutil.rmtree(clase)


class PruebaVistaPrevia(unittest.TestCase):
    def test_tamano(self):
        for receta in (rc.nueva(), rc.nueva(transparencia=1), rc.nueva(barniz=1, pelusa=1, emision=1, opacidad=0.3)):
            self.assertEqual(len(vp.pixeles(receta, 24)), 24 * 24 * 3)

    def test_cache(self):
        a = vp.clave_cache(rc.nueva(nombre="a"), 64, "render")
        self.assertEqual(a, vp.clave_cache(rc.nueva(nombre="b"), 64, "render"))
        self.assertNotEqual(a, vp.clave_cache(rc.nueva(rugosidad=0.1), 64, "render"))


class PruebaTextos(unittest.TestCase):
    def test_claves_usadas(self):
        existentes = claves()
        usadas, prefijos = set(), set()
        for carpeta in (os.path.join(RAIZ, "scripts", "materials"), RAIZ):
            for nombre in os.listdir(carpeta):
                if nombre.endswith(".py"):
                    codigo = leer(os.path.join(carpeta, nombre))
                    usadas.update(re.findall(r'\bt\("([a-z0-9_]+)"', codigo))
                    prefijos.update(re.findall(r'\bt\("([a-z0-9_]+_)" \+', codigo))
        faltan = sorted(c for c in usadas if c not in existentes and c not in prefijos)
        self.assertEqual(faltan, [])
        dinamicas = ["tab_" + x for x in ("biblioteca", "material", "texturas", "painter", "escena", "ajustes")]
        dinamicas += ["c_" + k for k in rc.DESLIZADORES] + ["ayuda_" + k for k in rc.DESLIZADORES]
        dinamicas += ["entrada_" + e for e in tx.ENTRADAS]
        dinamicas += ["ignorado_" + m for m in ("ao", "especular", "brillo_sobra", "duplicado")]
        dinamicas += ["motor_" + m for m in ic.MOTORES] + ["plantilla_" + m for m in ic.MOTORES]
        dinamicas += ["destino_corto_" + d for d in rc.DESTINOS] + ["normal_" + n for n in ("auto", "opengl", "directx")]
        for clave in ("ior", "especular", "anisotropia", "profundidad_transmision", "radio_subsuperficie",
                      "rugosidad_barniz", "ior_barniz", "rugosidad_pelusa", "opacidad", "pelicula", "grosor_pelicula",
                      "color_especular", "color_barniz", "color_transmision", "color_subsuperficie", "color_pelusa",
                      "color_emision"):
            dinamicas.append("c_" + clave)
        for boton in ("esc_actualizar", "esc_editar", "esc_seleccionar", "esc_prefijo", "esc_convertir", "esc_borrar"):
            dinamicas += [boton, boton + "_ayuda"]
        self.assertEqual([c for c in dinamicas if c not in existentes], [])


class PruebaPainter(unittest.TestCase):
    """El complemento de Painter se carga con un ``substance_painter`` falso."""

    @classmethod
    def setUpClass(cls):
        falso = types.ModuleType("substance_painter")
        for sub in ("project", "textureset", "layerstack", "export", "event", "ui", "logging", "colormanagement"):
            setattr(falso, sub, types.ModuleType(sub))
        sys.modules["substance_painter"] = falso
        try:
            import PySide6  # noqa: F401  (el complemento importa Qt)
        except ImportError:
            raise unittest.SkipTest("sin PySide6")
        sys.path.insert(0, os.path.join(RAIZ, "painter"))
        import materials_painter
        cls.mp = materials_painter

    def test_plantillas_reconocidas(self):
        for motor in ic.MOTORES:
            juego = {"emision": 0.5, "opacidad": 0.5}
            nombres = [m["fileName"].replace("$textureSet", "Caja").replace("(.$udim)", "") + ".png"
                       for m in self.mp.plantilla(motor, juego)]
            analisis = tx.analizar(["/x/" + n for n in nombres], normal_por_defecto=ic.NORMAL_DE_MOTOR[motor])
            self.assertEqual(list(analisis), ["caja"], motor)
            conexiones = analisis["caja"].conexiones
            for entrada in ("color", "rugosidad", "metal", "normal", "emision"):
                self.assertIn(entrada, conexiones, (motor, entrada))
            self.assertEqual(conexiones["normal"].mapa.convencion, ic.NORMAL_DE_MOTOR[motor], motor)
            for m in self.mp.plantilla(motor, juego):
                for canal in m["channels"]:
                    self.assertEqual(set(canal), {"destChannel", "srcChannel", "srcMapType", "srcMapName"})

    def test_buzon_compartido(self):
        casa = tempfile.mkdtemp()
        os.environ["MATERIALS_CASA"] = casa
        try:
            self.assertEqual(self.mp.carpeta_buzon(), ic.carpeta_buzon())
            carpeta = os.path.join(casa, "envio")
            ic.enviar(carpeta, ic.nueva_receta_envio("caja", "caja.fbx", {}))
            self.assertEqual(len(self.mp.avisos()), 1)
            self.mp.escribir_manifiesto(carpeta, {"Caja": [os.path.join(carpeta, "a.png")]})
            self.assertEqual(ic.leer_manifiesto(carpeta)["contador"], 1)
        finally:
            os.environ.pop("MATERIALS_CASA", None)
            shutil.rmtree(casa)


if __name__ == "__main__":
    unittest.main()
