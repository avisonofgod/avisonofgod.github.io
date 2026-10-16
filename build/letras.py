"""Abecedario hebreo con su lectura pictográfica, para el desglose por letra del lector.

Referencia simbólica (tradición de la escritura paleo-hebrea: cada letra nombra un objeto y de
ahí un campo de sentido). NO es un número de Strong ni un diccionario: es una ayuda de lectura,
en el mismo espíritu que el marcador palabra <-> traducción de la versión propia עבדיהו.

Se publica como `/v1/letras.json` (una sola fuente: este archivo) y lo consume el lector para
mostrar, hacia abajo y una por línea, las letras de la palabra o del componente seleccionado:

    רֵאשִׁית  ->  ר Resh · El primero, el líder, la persona principal
                 א Aleph · Buey, fuerza, líder, aprender
                 ש Shin · Diente, consumir, afilar, fuego
                 י Yod · Mano, brazo, obrar, hecho
                 ת Tav · Marca, sello, señal, pacto

Las formas finales (ך ם ן ף ץ) se resuelven a su letra base. Los signos de niqqud y los te'amim
no se listan: no son letras.
"""

ORDEN = ["א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט", "י", "כ", "ל", "מ", "נ", "ס", "ע",
         "פ", "צ", "ק", "ר", "ש", "ת"]

_L = [
    ("Aleph", "Buey, fuerza, líder, aprender"),
    ("Bet", "Familia, dentro, el hogar"),
    ("Gimel", "Camello, levantarse, orgullo, dar"),
    ("Dalet", "Puerta, entrada, camino, humilde"),
    ("He", "Ventana, he aquí, revelar, aliento"),
    ("Vav", "Clavo, gancho, asegurar, conectar"),
    ("Zayin", "Arma, espada, cortar, memoria"),
    ("Jet", "Cerca, valla, protección, separar"),
    ("Tet", "Cesta, barro, bueno, rodear"),
    ("Yod", "Mano, brazo, obrar, hecho"),
    ("Kaf", "Palma de la mano, cubrir, sostener, abrir"),
    ("Lamed", "Aguijón, cayado, enseñar, hacia"),
    ("Mem", "Agua, mar, caos, fluir"),
    ("Nun", "Pez, semilla, vida, continuar"),
    ("Samej", "Apoyo, espina, rodear, sostener"),
    ("Ayin", "Ojo, ver, conocer, apariencia"),
    ("Pe", "Boca, hablar, soplar, abrir"),
    ("Tsadi", "Anzuelo, cazar, justicia, deseo"),
    ("Qof", "Nuca, ojo de aguja, santidad, ciclo"),
    ("Resh", "El primero, el líder, la persona principal"),
    ("Shin", "Diente, consumir, afilar, fuego"),
    ("Tav", "Marca, sello, señal, pacto, verdad"),
]

LETRAS = {letra: {"orden": i + 1, "nombre": nombre, "pictograma": pictograma}
          for i, (letra, (nombre, pictograma)) in enumerate(zip(ORDEN, _L))}

# Formas finales (sofit) -> letra base.
FINALES = {"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"}

META = {
    "note": ("Lectura pictográfica tradicional de las 22 letras hebreas (referencia simbólica, "
             "no números de Strong). Las formas finales se resuelven a su letra base; el niqqud "
             "y los te'amim no son letras."),
    "source": "Tradición de la escritura paleo-hebrea; tabla propia de la versión עבדיהו.",
    "license": "CC0 1.0 Universal (dedicación al dominio público)",
    "spdx": "CC0-1.0",
}


def payload():
    return dict(META, order=ORDEN, letters=LETRAS, finals=FINALES)


def base(letra):
    """Letra base de una forma final (ך -> כ)."""
    return FINALES.get(letra, letra)


if __name__ == "__main__":
    import json
    import os
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "v1", "letras.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(payload(), fh, ensure_ascii=False, indent=1)
    print("escrito %s (%d letras)" % (p, len(LETRAS)))
