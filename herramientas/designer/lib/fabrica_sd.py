"""Ayudas para montar grafos de Substance Designer por script (API ``sd``).

Solo funciona dentro de Designer (lo usan los scripts que ejecuta materials_puente).
Los nombres de entradas y salidas de los nodos se buscan con tolerancia: si el
identificador pedido no existe se usa el primero que se parezca, y se avisa en el log.
"""

import os

import sd
from sd.api.sdbasetypes import float2, float3, float4, int2
from sd.api.sdproperty import SDPropertyCategory
from sd.api.sdvaluebool import SDValueBool
from sd.api.sdvaluefloat import SDValueFloat
from sd.api.sdvaluefloat2 import SDValueFloat2
from sd.api.sdvaluefloat3 import SDValueFloat3
from sd.api.sdvaluefloat4 import SDValueFloat4
from sd.api.sdvalueint import SDValueInt
from sd.api.sdvalueint2 import SDValueInt2
from sd.api.sdvaluestring import SDValueString
from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph

ENTRADA = SDPropertyCategory.Input
SALIDA = SDPropertyCategory.Output

_app = sd.getContext().getSDApplication()
_pm = _app.getPackageMgr()
try:
    from sd.api.sdapplication import SDApplicationPath
    RECURSOS = _app.getPath(SDApplicationPath.DefaultResourcesDir)
except Exception:  # pragma: no cover
    RECURSOS = "/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/Resources"
PAQUETES = os.path.join(RECURSOS, "packages")

# Modos de fusión del nodo atómico Blend.
COPIAR, SUMAR, RESTAR, MULTIPLICAR, SUMA_RESTA, MAXIMO, MINIMO = 0, 1, 2, 3, 4, 5, 6
SALIDA_ATOMICA = "unique_filter_output"
_grafos = {}
_avisos = set()


def avisar(texto):
    if texto not in _avisos:
        _avisos.add(texto)
        print("AVISO", texto)


def grafo_biblioteca(paquete, grafo=None):
    """Grafo de la biblioteca de Designer (packages/<paquete>.sbs)."""
    clave = (paquete, grafo)
    if clave not in _grafos:
        ruta = os.path.join(PAQUETES, paquete + ".sbs")
        pkg = _pm.getUserPackageFromFilePath(ruta) or _pm.loadUserPackage(ruta)
        grafos = [r for r in pkg.getChildrenResources(True) if type(r).__name__ == "SDSBSCompGraph"]
        elegido = [g for g in grafos if g.getIdentifier() == (grafo or paquete)] or grafos
        _grafos[clave] = elegido[0]
    return _grafos[clave]


def _valor(tipo, v):
    if tipo == "bool":
        return SDValueBool.sNew(bool(v))
    if tipo == "int":
        return SDValueInt.sNew(int(v))
    if tipo == "float":
        return SDValueFloat.sNew(float(v))
    if tipo == "float2":
        return SDValueFloat2.sNew(float2(*[float(x) for x in v]))
    if tipo == "float3":
        return SDValueFloat3.sNew(float3(*[float(x) for x in v]))
    if tipo == "float4":
        return SDValueFloat4.sNew(float4(*[float(x) for x in v]))
    if tipo == "int2":
        return SDValueInt2.sNew(int2(*[int(x) for x in v]))
    if tipo == "string":
        return SDValueString.sNew(str(v))
    raise TypeError("tipo no soportado: {} ({!r})".format(tipo, v))


_ENUMS = {}


def opciones_enum(tipo):
    """[(identificador, valor)] de un tipo enumerado (se apunta en el log la primera vez)."""
    ident = tipo.getId()
    if ident not in _ENUMS:
        lista = []
        try:
            for e in tipo.getEnumerators():
                try:
                    valor = e.getDefaultValue().get()
                except BaseException:
                    valor = None
                lista.append((e.getId(), valor))
        except BaseException as error:
            avisar("no puedo leer las opciones de {}: {}".format(ident, error))
        _ENUMS[ident] = lista
        print("ENUM", ident, lista)
    return _ENUMS[ident]


def _valor_enum(tipo, v):
    from sd.api.sdvalueenum import SDValueEnum
    ident = tipo.getId()
    opciones = opciones_enum(tipo)
    if isinstance(v, str):
        return SDValueEnum.sFromValueId(ident, v)
    for nombre, valor in opciones:
        if valor == int(v):
            return SDValueEnum.sFromValueId(ident, nombre)
    if 0 <= int(v) < len(opciones):  # sin valores: por posición
        return SDValueEnum.sFromValueId(ident, opciones[int(v)][0])
    return SDValueEnum.sFromValue(ident, int(v))


def poner(nodo, **params):
    """Fija parámetros por identificador, convirtiendo al tipo de la propiedad.

    Los enumerados aceptan el número de la opción o su identificador (texto).
    """
    for ident, v in params.items():
        p = nodo.getPropertyFromId(ident, ENTRADA)
        if p is None:
            avisar("{}: no hay parámetro {}".format(_nombre(nodo), ident))
            continue
        tipo = p.getType()
        if hasattr(tipo, "getEnumerators") or tipo.getId().startswith("sbs::") or "enum" in tipo.getId().lower():
            valor = _valor_enum(tipo, v)
        else:
            valor = _valor(tipo.getId(), v)
        nodo.setPropertyValue(p, valor)
    return nodo


def _nombre(nodo):
    try:
        return nodo.getDefinition().getId()
    except Exception:
        return "?"


def _ids(nodo, categoria, conectables=True):
    out = []
    for p in nodo.getProperties(categoria):
        if conectables and categoria == ENTRADA and not p.isConnectable():
            continue
        if p.getId().startswith("$"):
            continue
        out.append(p.getId())
    return out


def _elegir(nodo, categoria, pedido, indice):
    ids = _ids(nodo, categoria)
    if pedido in ids:
        return pedido
    if pedido:
        parecidos = [i for i in ids if pedido.lower() in i.lower() or i.lower() in pedido.lower()]
        if parecidos:
            avisar("{}: uso {} en vez de {} ({})".format(_nombre(nodo), parecidos[0], pedido, ids))
            return parecidos[0]
    if not ids:
        raise ValueError("{} no tiene {} conectables".format(_nombre(nodo), "entradas" if categoria == ENTRADA else "salidas"))
    i = min(indice, len(ids) - 1)
    if pedido:
        avisar("{}: no existe {}, uso {} ({})".format(_nombre(nodo), pedido, ids[i], ids))
    return ids[i]


class Grafo(object):
    """Envoltorio de un SDSBSCompGraph nuevo dentro de un paquete."""

    def __init__(self, paquete, ident, formato=1):
        self.g = SDSBSCompGraph.sNew(paquete)
        self.g.setIdentifier(ident)
        self.x = 0
        # Formato de todo el grafo: 1 = 16 bits enteros (alturas sin escalones).
        try:
            self.g.setPropertyValue(self.g.getPropertyFromId("$format", ENTRADA), SDValueInt.sNew(formato))
        except Exception as e:
            avisar("no puedo fijar $format: {}".format(e))

    def _colocar(self, nodo):
        try:
            nodo.setPosition(float2(self.x * 160.0, 0.0))
        except Exception:
            pass
        self.x += 1
        return nodo

    def bib(self, paquete, grafo=None, **params):
        nodo = self.g.newInstanceNode(grafo_biblioteca(paquete, grafo))
        return self._colocar(poner(nodo, **params))

    def atomo(self, nombre, **params):
        nodo = self.g.newNode("sbs::compositing::" + nombre)
        return self._colocar(poner(nodo, **params))

    def unir(self, origen, destino, entrada=None, indice_entrada=0, salida=None):
        s = _elegir(origen, SALIDA, salida, 0)
        e = _elegir(destino, ENTRADA, entrada, indice_entrada)
        origen.newPropertyConnectionFromId(s, destino, e)
        return destino

    def mezcla(self, fondo, frente, modo, opacidad=1.0, mascara=None):
        """Blend atómico: frente sobre fondo."""
        nodo = self.atomo("blend", blendingmode=modo, opacitymult=opacidad)
        self.unir(frente, nodo, "source")
        self.unir(fondo, nodo, "destination")
        if mascara is not None:
            self.unir(mascara, nodo, "opacity")
        return nodo

    def salida(self, origen, ident, salida=None):
        nodo = self.g.newNode("sbs::compositing::output")
        self._colocar(nodo)
        for clave in ("identifier", "label"):
            try:
                nodo.setAnnotationPropertyValueFromId(clave, SDValueString.sNew(ident))
            except Exception as e:
                avisar("salida {}: no puedo fijar {} ({})".format(ident, clave, e))
        self.unir(origen, nodo, "inputNodeOutput", salida=salida)
        return nodo


def paquete_nuevo():
    return _pm.newUserPackage()


def guardar(paquete, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    _pm.savePackageAs(paquete, ruta)
    return ruta


def describir_nodo(nodo):
    """Entradas conectables y salidas de un nodo (para el log)."""
    return "{}: entradas {} salidas {}".format(_nombre(nodo), _ids(nodo, ENTRADA), _ids(nodo, SALIDA))
