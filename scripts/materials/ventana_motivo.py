"""Pestaña «Motivo» de la ventana de Materials.

El motivo es un extra opcional encima de la receta: una estructura (ladrillo, baldosa,
tablas...), un acabado (cepillado, poro, veta...) y una proyección a tamaño real.
Está apagado en todas las recetas. Con un material de la escena vinculado, cada cambio
se ve al momento: los valores van al nodo de control y solo se rehace la red cuando
cambia la estructura, el acabado o la proyección.
"""

import os

from materials import estilo
from materials import motivos as mv
from materials import receta as rc
from materials.i18n import t
from materials.qt import QtCore, QtGui, QtWidgets
from materials.ventana import BotonColor, Deslizador

Qt = QtCore.Qt
TAM_ICONO = 64
NINGUNA = ""


class PestanaMotivo(QtWidgets.QWidget):
    """Necesita la ventana: lee y escribe ``ventana.receta``, ``ventana.material`` y ``ventana.destino``."""

    def __init__(self, ventana, padre=None):
        super(PestanaMotivo, self).__init__(padre)
        self.ventana = ventana
        self.servicios = ventana.servicios
        self.catalogo = mv.Catalogo(self.carpetas())
        self.motivo = mv.normalizar(None)
        self._aplicado = None          # último motivo escrito en el material vinculado
        self._cargando = False
        self._vivo_t = QtCore.QTimer(self, singleShot=True, interval=60, timeout=self._aplicar_vivo)
        self._construir()
        self.rellenar_catalogo()

    # --- Datos --------------------------------------------------------------------------------

    def carpetas(self):
        carpetas = []
        propia = self.ventana._ajuste("carpeta_motivos")
        if propia:
            carpetas.append(propia)
        if self.ventana.carpeta_preferencias:
            carpetas.append(os.path.join(self.ventana.carpeta_preferencias, "motivos"))
        return carpetas

    def recargar_catalogo(self):
        self.catalogo = mv.Catalogo(self.carpetas())
        self.rellenar_catalogo()
        return len(self.catalogo)

    def _resolucion(self):
        return self.ventana._ajuste("resolucion_motivos")

    def plan(self, motivo=None):
        return mv.plan(motivo if motivo is not None else self.motivo, self.catalogo, self.ventana.receta,
                       self._resolucion(), self.ventana.destino)

    # --- Construcción --------------------------------------------------------------------------

    def _construir(self):
        exterior = QtWidgets.QVBoxLayout(self)
        desplazable = QtWidgets.QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QtWidgets.QFrame.NoFrame)
        interior = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(interior)
        capa.setContentsMargins(2, 6, 6, 6)
        capa.setSpacing(10)

        marco, dentro = estilo.tarjeta(12, 6)
        self.casilla = QtWidgets.QCheckBox(t("mot_usar"))
        self.casilla.setToolTip(t("mot_usar_ayuda"))
        self.casilla.toggled.connect(lambda v: self._cambiar("activo", bool(v)))
        dentro.addWidget(self.casilla)
        self.etiqueta_estado = estilo.etiqueta(t("mot_ayuda"), "tenue", ajuste=True)
        dentro.addWidget(self.etiqueta_estado)
        capa.addWidget(marco)

        self.cuerpo = QtWidgets.QWidget()
        cuerpo = QtWidgets.QVBoxLayout(self.cuerpo)
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(10)

        marco, dentro = estilo.tarjeta(12, 6)
        dentro.addWidget(estilo.etiqueta(t("mot_estructura"), "seccion"))
        dentro.addWidget(estilo.etiqueta(t("mot_estructura_ayuda"), "tenue", ajuste=True))
        self.lista_estructuras = QtWidgets.QListWidget()
        self.lista_estructuras.setViewMode(QtWidgets.QListView.IconMode)
        self.lista_estructuras.setIconSize(QtCore.QSize(TAM_ICONO, TAM_ICONO))
        self.lista_estructuras.setGridSize(QtCore.QSize(TAM_ICONO + 34, TAM_ICONO + 40))
        self.lista_estructuras.setResizeMode(QtWidgets.QListView.Adjust)
        self.lista_estructuras.setMovement(QtWidgets.QListView.Static)
        self.lista_estructuras.setWordWrap(True)
        self.lista_estructuras.setMinimumHeight(TAM_ICONO + 50)
        self.lista_estructuras.setMaximumHeight(TAM_ICONO * 2 + 90)
        self.lista_estructuras.currentItemChanged.connect(self._al_elegir_estructura)
        dentro.addWidget(self.lista_estructuras)
        formulario = estilo.formulario()
        formulario.setHorizontalSpacing(12)
        formulario.setVerticalSpacing(6)
        self.combo_acabado = QtWidgets.QComboBox()
        self.combo_acabado.setToolTip(t("mot_acabado_ayuda"))
        self.combo_acabado.currentIndexChanged.connect(self._al_elegir_acabado)
        formulario.addRow(t("mot_acabado"), self.combo_acabado)
        dentro.addLayout(formulario)
        cuerpo.addWidget(marco)

        marco, dentro = estilo.tarjeta(12, 6)
        dentro.addWidget(estilo.etiqueta(t("mot_proyeccion"), "seccion"))
        formulario = estilo.formulario()
        formulario.setHorizontalSpacing(12)
        formulario.setVerticalSpacing(6)
        self.combo_proyeccion = QtWidgets.QComboBox()
        for p in mv.PROYECCIONES:
            self.combo_proyeccion.addItem(t("mot_p_" + p), p)
            self.combo_proyeccion.setItemData(self.combo_proyeccion.count() - 1, t("mot_p_" + p + "_ayuda"),
                                              Qt.ToolTipRole)
        self.combo_proyeccion.currentIndexChanged.connect(
            lambda _: self._cambiar("proyeccion", self.combo_proyeccion.currentData()))
        formulario.addRow(t("mot_proyeccion_tipo"), self.combo_proyeccion)
        self.etiqueta_proyeccion = estilo.etiqueta("", "tenue", ajuste=True)
        formulario.addRow("", self.etiqueta_proyeccion)
        self.combo_espacio = QtWidgets.QComboBox()
        for e in mv.ESPACIOS:
            self.combo_espacio.addItem(t("mot_e_" + e), e)
        self.combo_espacio.setToolTip(t("mot_espacio_ayuda"))
        self.combo_espacio.currentIndexChanged.connect(
            lambda _: self._cambiar("espacio", self.combo_espacio.currentData()))
        formulario.addRow(t("mot_espacio"), self.combo_espacio)
        self.combo_eje = QtWidgets.QComboBox()
        for e in mv.EJES:
            self.combo_eje.addItem(e.upper(), e)
        self.combo_eje.currentIndexChanged.connect(lambda _: self._cambiar("eje", self.combo_eje.currentData()))
        self.rotulo_eje = QtWidgets.QLabel(t("mot_eje"))
        formulario.addRow(self.rotulo_eje, self.combo_eje)
        self.casilla_azar = QtWidgets.QCheckBox(t("mot_azar"))
        self.casilla_azar.setToolTip(t("mot_azar_ayuda"))
        self.casilla_azar.toggled.connect(lambda v: self._cambiar("azar", bool(v)))
        formulario.addRow("", self.casilla_azar)
        dentro.addLayout(formulario)
        fila = QtWidgets.QHBoxLayout()
        self.boton_reproyectar = QtWidgets.QPushButton(t("mot_reproyectar"))
        self.boton_reproyectar.setToolTip(t("mot_reproyectar_ayuda"))
        self.boton_reproyectar.clicked.connect(self.reproyectar)
        self.boton_control = QtWidgets.QPushButton(t("mot_control"))
        self.boton_control.setToolTip(t("mot_control_ayuda"))
        self.boton_control.clicked.connect(self.seleccionar_control)
        fila.addWidget(self.boton_reproyectar)
        fila.addWidget(self.boton_control)
        fila.addStretch(1)
        dentro.addLayout(fila)
        cuerpo.addWidget(marco)

        marco, dentro = estilo.tarjeta(12, 6)
        dentro.addWidget(estilo.etiqueta(t("mot_medidas"), "seccion"))
        formulario = estilo.formulario()
        formulario.setHorizontalSpacing(12)
        formulario.setVerticalSpacing(6)
        self.deslizadores = {}
        self.rotulos = {}
        for clave, minimo, maximo, decimales in (
                ("pieza_cm", 1.0, 200.0, 1), ("repeticion_cm", 1.0, 200.0, 1), ("rotacion", -180.0, 180.0, 0),
                ("mezcla", 0.0, 1.0, 2), ("variacion", 0.0, 1.0, 2), ("relieve", 0.0, 1.0, 2),
                ("desgaste", 0.0, 1.0, 2), ("rugosidad_desgaste", 0.0, 1.0, 2), ("rugosidad_junta", 0.0, 1.0, 2)):
            d = Deslizador(minimo, maximo, decimales)
            d.cambiado.connect(lambda v, k=clave: self._cambiar(k, v))
            d.setToolTip(t("mot_" + clave + "_ayuda"))
            rotulo = QtWidgets.QLabel(t("mot_" + clave))
            rotulo.setToolTip(t("mot_" + clave + "_ayuda"))
            self.deslizadores[clave] = d
            self.rotulos[clave] = rotulo
            formulario.addRow(rotulo, d)
        self.colores = {}
        self.boton_color_pieza = BotonColor()
        self.boton_color_pieza.setToolTip(t("mot_color_pieza_ayuda"))
        self.boton_color_pieza.cambiado.connect(self._al_color_pieza)
        formulario.addRow(t("mot_color_pieza"), self.boton_color_pieza)
        for clave in ("color2", "color_junta", "color_desgaste"):
            b = BotonColor()
            b.setToolTip(t("mot_" + clave + "_ayuda"))
            b.cambiado.connect(lambda c, k=clave: self._cambiar(k, c) if c else None)
            rotulo = QtWidgets.QLabel(t("mot_" + clave))
            self.colores[clave] = b
            self.rotulos[clave] = rotulo
            formulario.addRow(rotulo, b)
        dentro.addLayout(formulario)
        cuerpo.addWidget(marco)

        capa.addWidget(self.cuerpo)
        self.etiqueta_vacio = estilo.etiqueta(t("mot_catalogo_vacio"), "tenue", ajuste=True)
        capa.addWidget(self.etiqueta_vacio)
        capa.addStretch(1)
        desplazable.setWidget(interior)
        exterior.addWidget(desplazable)

    # --- Catálogo en los controles ---------------------------------------------------------------

    def _icono(self, motivo):
        ruta = motivo.miniatura() if motivo else None
        imagen = QtGui.QImage(ruta) if ruta else QtGui.QImage()
        if imagen.isNull():
            imagen = QtGui.QImage(TAM_ICONO, TAM_ICONO, QtGui.QImage.Format_RGB32)
            imagen.fill(QtGui.QColor("#3a3a3a"))
        return QtGui.QIcon(QtGui.QPixmap.fromImage(imagen.scaled(TAM_ICONO, TAM_ICONO, Qt.IgnoreAspectRatio,
                                                                 Qt.SmoothTransformation)))

    def rellenar_catalogo(self):
        """Rellena estructuras y acabados con ★ primero para la receta actual."""
        self._cargando = True
        try:
            receta = self.ventana.receta
            self.lista_estructuras.clear()
            item = QtWidgets.QListWidgetItem(self._icono(None), t("mot_ninguna"))
            item.setData(Qt.UserRole, NINGUNA)
            item.setToolTip(t("mot_ninguna_ayuda"))
            self.lista_estructuras.addItem(item)
            for m in self.catalogo.ordenados(mv.ESTRUCTURAS, receta):
                nombre = ("★ " if m.recomendado(receta) else "") + m.nombre
                item = QtWidgets.QListWidgetItem(self._icono(m), nombre)
                item.setData(Qt.UserRole, m.id)
                item.setToolTip("{} · {}\n{}".format(m.nombre, m.familia, t("mot_pieza_tip", cm=_cm(m.pieza_cm))))
                self.lista_estructuras.addItem(item)
            self.combo_acabado.clear()
            propuesto = mv.acabado_propuesto(receta, self.catalogo)
            self.combo_acabado.addItem(t("mot_acabado_auto"), "")
            familia = None
            for m in self.catalogo.ordenados(mv.ACABADOS, receta):
                if m.id != propuesto and not m.recomendado(receta) and m.familia != familia:
                    familia = m.familia
                    self.combo_acabado.insertSeparator(self.combo_acabado.count())
                estrella = "★ " if m.id == propuesto or m.recomendado(receta) else ""
                self.combo_acabado.addItem(estrella + m.nombre + ("  · " + m.familia if m.familia else ""), m.id)
        finally:
            self._cargando = False
        self._poner_controles()

    # --- Carga y estado ----------------------------------------------------------------------------

    def cargar(self, motivo, aplicado=False):
        """Pone el motivo de la receta en los controles. ``aplicado``: ya está así en el material."""
        self.motivo = mv.normalizar(motivo)
        self._aplicado = dict(self.motivo) if aplicado and self.motivo["activo"] else None
        self.rellenar_catalogo()

    def _poner_controles(self):
        self._cargando = True
        try:
            m = self.motivo
            self.casilla.setChecked(m["activo"])
            for i in range(self.lista_estructuras.count()):
                if self.lista_estructuras.item(i).data(Qt.UserRole) == m["estructura"]:
                    self.lista_estructuras.setCurrentRow(i)
                    break
            else:
                self.lista_estructuras.setCurrentRow(0)
            indice = self.combo_acabado.findData(m["acabado"])
            self.combo_acabado.setCurrentIndex(max(0, indice))
            self.combo_proyeccion.setCurrentIndex(max(0, self.combo_proyeccion.findData(m["proyeccion"])))
            self.combo_espacio.setCurrentIndex(max(0, self.combo_espacio.findData(m["espacio"])))
            self.combo_eje.setCurrentIndex(max(0, self.combo_eje.findData(m["eje"])))
            self.casilla_azar.setChecked(m["azar"])
            estructura = self.catalogo.estructura(m["estructura"]) if m["estructura"] else None
            acabado = self._acabado()
            pieza = mv.pieza_efectiva(m, estructura) or 0.0
            repeticion = mv.repeticion_efectiva(m, acabado) or 0.0
            if estructura:
                self.deslizadores["pieza_cm"].rango(max(0.1, estructura.pieza_cm / 6.0), estructura.pieza_cm * 6.0)
            if acabado:
                self.deslizadores["repeticion_cm"].rango(max(0.1, acabado.tile_cm[0] / 6.0), acabado.tile_cm[0] * 6.0)
            valores = dict(m, pieza_cm=pieza, repeticion_cm=repeticion)
            for clave, d in self.deslizadores.items():
                d.poner(valores[clave])
            self.boton_color_pieza.poner(self.ventana.receta["color"])
            junta = m["color_junta"] or (estructura.junta if estructura else mv.JUNTA_DEFECTO)
            for clave, b in self.colores.items():
                b.poner(junta if clave == "color_junta" else m[clave])
        finally:
            self._cargando = False
        self._visibilidad()

    def _acabado(self):
        ident = self.motivo["acabado"] or mv.acabado_propuesto(self.ventana.receta, self.catalogo)
        return self.catalogo.acabado(ident) if ident else None

    def _visibilidad(self):
        m = self.motivo
        hay = len(self.catalogo) > 0
        self.casilla.setEnabled(hay)
        self.etiqueta_vacio.setVisible(not hay)
        self.cuerpo.setVisible(hay)
        self.cuerpo.setEnabled(m["activo"])
        estructura = self.catalogo.estructura(m["estructura"]) if m["estructura"] else None
        con_estructura = estructura is not None
        for clave in ("pieza_cm", "variacion", "desgaste", "rugosidad_desgaste", "rugosidad_junta"):
            self.deslizadores[clave].setVisible(con_estructura)
            self.rotulos[clave].setVisible(con_estructura)
        for clave in ("color_junta", "color_desgaste"):
            self.colores[clave].setVisible(con_estructura)
            self.rotulos[clave].setVisible(con_estructura)
        con_acabado = self._acabado() is not None
        self.deslizadores["repeticion_cm"].setVisible(con_acabado)
        self.rotulos["repeticion_cm"].setVisible(con_acabado)
        con_color2 = bool(estructura and estructura.color2)
        self.colores["color2"].setVisible(con_color2)
        self.rotulos["color2"].setVisible(con_color2)
        triplanar = m["proyeccion"] == "triplanar"
        self.deslizadores["mezcla"].setVisible(triplanar)
        self.rotulos["mezcla"].setVisible(triplanar)
        con_eje = m["proyeccion"] in ("planar", "cilindrica", "esferica")
        self.combo_eje.setVisible(con_eje)
        self.rotulo_eje.setVisible(con_eje)
        escribe = m["proyeccion"] in mv.ESCRIBEN_UV
        self.casilla_azar.setVisible(escribe)
        self.combo_espacio.setVisible(m["proyeccion"] != "uv")
        vinculado = bool(self.ventana.material)
        self.boton_reproyectar.setEnabled(vinculado and m["activo"] and escribe)
        self.boton_control.setEnabled(vinculado and m["activo"])
        # En videojuego no hay triplanar.
        modelo = self.combo_proyeccion.model()
        indice = self.combo_proyeccion.findData("triplanar")
        item = modelo.item(indice) if hasattr(modelo, "item") else None
        if item is not None:
            item.setEnabled(self.ventana.destino != rc.JUEGO)
        texto = t("mot_p_" + m["proyeccion"] + "_ayuda")
        if m["proyeccion"] in mv.SOLO_RENDER and self.ventana.destino == rc.JUEGO:
            texto = t("mot_triplanar_juego")
        self.etiqueta_proyeccion.setText(texto)
        self._poner_estado()

    def _poner_estado(self):
        m = self.motivo
        if not len(self.catalogo):
            texto = t("mot_ayuda")
        elif not m["activo"]:
            texto = t("mot_ayuda")
        else:
            plan = self.plan()
            if plan is None:
                texto = t("mot_nada")
            else:
                partes = [c["nombre"] for c in (plan["capas"].get("estructura"), plan["capas"].get("acabado")) if c]
                texto = t("mot_resumen", motivo=" + ".join(partes), proyeccion=t("mot_p_" + plan["motivo"]["proyeccion"]))
                if plan["faltan"]:
                    texto += " " + t("mot_faltan", lista=", ".join(plan["faltan"]))
        self.etiqueta_estado.setText(texto)

    def al_cambiar_destino(self):
        self._visibilidad()
        if self.ventana.material and self.motivo["activo"]:
            self._aplicar(forzar=True)

    def al_cambiar_receta(self):
        """El color de la pestaña Material se ve aquí (el color de pieza es el de la receta)."""
        self._cargando = True
        try:
            self.boton_color_pieza.poner(self.ventana.receta["color"])
        finally:
            self._cargando = False

    # --- Cambios -----------------------------------------------------------------------------------

    def _al_elegir_estructura(self, actual, _anterior=None):
        if actual is None:
            return
        self._cambiar("estructura", actual.data(Qt.UserRole) or "", recolocar=True)

    def _al_elegir_acabado(self, _indice):
        self._cambiar("acabado", self.combo_acabado.currentData() or "", recolocar=True)

    def _al_color_pieza(self, color):
        if self._cargando or not color:
            return
        self.ventana._cambiar("color", color)

    def _cambiar(self, clave, valor, recolocar=False):
        if self._cargando:
            return
        if clave in ("estructura", "acabado"):
            # Al cambiar de estructura o acabado, su medida propia (0 = la del catálogo).
            self.motivo["pieza_cm" if clave == "estructura" else "repeticion_cm"] = 0.0
            if clave == "estructura":
                self.motivo["color_junta"] = ""
        self.motivo[clave] = valor
        self.motivo = mv.normalizar(self.motivo)
        self.ventana.receta["motivo"] = dict(self.motivo)
        if recolocar or clave in ("activo", "proyeccion"):
            self._poner_controles()
        else:
            self._visibilidad()
        if self.ventana.material:
            self._aplicar()

    def _aplicar(self, forzar=False):
        material = self.ventana.material
        if not material:
            return
        que = "red" if forzar or self._aplicado is None else mv.cambios(self._aplicado, self.motivo)
        if not self.motivo["activo"]:
            if self._aplicado is not None:
                self.ventana._seguro(self.servicios.quitar_motivo, material, self.ventana.receta,
                                     self.ventana.destino)
                self._aplicado = None
                self.ventana.mensaje(t("mot_quitado", material=material))
            return
        if que == "nada":
            return
        if que == "vivo":
            self._vivo_t.start()
            return
        if que == "reproyectar":
            self._aplicar_vivo()
            self.ventana._seguro(self.servicios.reproyectar, material)
            self._aplicado = dict(self.motivo)
            return
        self.montar(material)

    def montar(self, material):
        """Monta el motivo en el material (o lo quita si no hay nada que montar)."""
        plan = self.plan()
        if plan is None:
            if self._aplicado is not None:
                self.ventana._seguro(self.servicios.quitar_motivo, material, self.ventana.receta,
                                     self.ventana.destino)
            self._aplicado = None
            return False
        hecho = self.ventana._seguro(self.servicios.aplicar_motivo, material, plan, self.ventana.receta,
                                     self.ventana.destino)
        if hecho is None:
            return False
        self._aplicado = dict(self.motivo)
        self.ventana.mensaje(t("mot_aplicado", material=material))
        return True

    def _aplicar_vivo(self):
        material = self.ventana.material
        if material and self.motivo["activo"] and self._aplicado is not None:
            plan = self.plan()
            motivo = plan["motivo"] if plan else self.motivo
            self.ventana._seguro(self.servicios.ajustar_motivo, material, motivo)
            self._aplicado = dict(self.motivo)

    def al_crear_material(self, material):
        """Material nuevo desde la receta: si la receta lleva motivo, se monta."""
        self._aplicado = None
        if self.motivo["activo"]:
            self.montar(material)
        self._visibilidad()

    def reproyectar(self):
        material = self.ventana.material
        if material:
            formas = self.ventana._seguro(self.servicios.reproyectar, material) or []
            self.ventana.mensaje(t("mot_reproyectado", n=len(formas)))

    def seleccionar_control(self):
        material = self.ventana.material
        if material:
            nodo = self.ventana._seguro(self.servicios.seleccionar_control_motivo, material)
            if nodo:
                self.ventana.mensaje(t("mot_control_hecho", nodo=nodo))

    def cerrar(self):
        if self._vivo_t.isActive():
            self._vivo_t.stop()
            self._aplicar_vivo()


def _cm(valor):
    return ("{:.1f}".format(valor)).rstrip("0").rstrip(".").replace(".", ",")
