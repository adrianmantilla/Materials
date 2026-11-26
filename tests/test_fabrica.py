"""Pruebas de la composición numpy de la fábrica de Designer (sin Designer)."""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "herramientas", "designer"))

try:
    import numpy as np
    import fabricar  # noqa: E402
    import acabados  # noqa: E402
    import estructuras_def as ed  # noqa: E402
    import patrones  # noqa: E402
except ImportError:  # sin numpy o Pillow
    fabricar = None


@unittest.skipIf(fabricar is None, "faltan numpy o Pillow")
class Fabrica(unittest.TestCase):
    def test_etiquetar_pieza_cortada_por_el_borde(self):
        m = np.zeros((40, 40), bool)
        m[5:15, 30:40] = True
        m[5:15, 0:8] = True  # la misma pieza, al otro lado del borde
        m[25:35, 10:20] = True
        m[38:40, 22:28] = True
        m[0:3, 22:28] = True  # cortada arriba y abajo
        lab, n = fabricar.etiquetar(m)
        self.assertEqual(n, 3)
        self.assertEqual(lab[10, 35], lab[10, 2])
        self.assertEqual(lab[39, 25], lab[1, 25])
        self.assertTrue((lab[~m] == -1).all())

    def test_ruido_repite_sin_costura(self):
        r = fabricar.ruido_cm((128, 128), 0.5, 0.25, 2.0, 3, octavas=2)
        self.assertLess(fabricar.costura(r), 1.2)
        self.assertAlmostEqual(float(r.mean()), 0.5, delta=0.05)

    def test_por_pieza_inclinacion_de_0_a_1(self):
        m = np.zeros((40, 40), bool)
        m[5:15, 30:40] = True
        m[5:15, 0:8] = True
        lab, n = fabricar.etiquetar(m)
        incl = fabricar.por_pieza(lab, n, 1.0, 1.0, 1)[2]
        self.assertAlmostEqual(float(incl[m].min()), 0.0, places=6)
        self.assertAlmostEqual(float(incl[m].max()), 1.0, places=6)

    def test_acabados_repiten_y_giran_alrededor_de_gris_medio(self):
        for d in acabados.ACABADOS:
            forma = (256, 256)
            color, rug, altura = d["funcion"](forma, d["tile_cm"][0] / 256, d["tile_cm"][1] / 256)
            self.assertEqual(color.shape, forma + (3,), d["id"])
            self.assertAlmostEqual(float(color.mean()), 0.5, delta=0.06, msg=d["id"])
            self.assertAlmostEqual(float(rug.mean()), 0.5, delta=0.06, msg=d["id"])
            self.assertLess(fabricar.costura(color.mean(axis=2)), 1.3, d["id"])
            self.assertLess(fabricar.costura(altura), 1.3, d["id"])

    def test_patrones_del_lote_2_cubren_y_repiten(self):
        for d in ed.LOTE_2 + ed.LOTE_3 + ed.LOTE_4 + ed.LOTE_5 + ed.LOTE_6 + ed.LOTE_7:
            if "patron" not in d:
                continue  # aparejo simple (piezas × desfase): lo prueba Designer
            m = patrones.forma(d, 256, fabricar.distancia_interior)
            self.assertGreater(m.mean(), 0.5, d["id"])
            self.assertLess(fabricar.costura(m.astype(float)), 1.5, d["id"])
            lab, n = fabricar.etiquetar(m)
            self.assertGreaterEqual(n, 2, d["id"])  # las chapas son dos paneles


if __name__ == "__main__":
    unittest.main()
