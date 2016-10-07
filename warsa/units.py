import re
import sys
from arpa_linker.link_helper import process_stage


def preprocessor(text, *args):
    """
    >>> preprocessor("Klo 8.52 ilmahälytys Viipurissa ja klo 9 pommitus Kotkan lohkoa vastaan.")
    'klo 8.52 ilmahälytys Viipurissa ja klo 9 pommitus Kotkan lohkoa vastaan.'
    >>> preprocessor("7 div.komendörs")
    '7. D komendörs'
    >>> preprocessor("Tyk.K/JR22:n hyökkäyskaistaa.")
    'TykK/JR 22 hyökkäyskaistaa. # JR 22'
    >>> preprocessor("1/JR 10:ssä.")
    '1/JR 10. # JR 10'
    >>> preprocessor("1/JR10:ssä.")
    '1/JR 10. # JR 10'
    >>> preprocessor("JP1:n radioasema")
    'JP 1 radioasema'
    >>> preprocessor("2./I/15.Pr.")
    '2./I/15. Pr. # 15. Pr'
    >>> preprocessor("IV.AKE.")
    'IV AKE.'
    >>> preprocessor("(1/12.Pr.)")
    '(1/12. Pr.) # 12. Pr'
    >>> preprocessor("Tsto 3/2. DE aliupseerit.")
    'Tsto 3/2. DE aliupseerit. # 2. DE'
    >>> preprocessor("pistooli m/41.")
    'pistooli m/41.'
    >>> preprocessor("Raskas patteristo/14.D. Elo-syyskuu 1944.")
    'Raskas patteristo/14. D. Elo-syyskuu 1944. # 14. D'
    >>> preprocessor("Kenraalimajuri E.J.Raappana seurueineen.")
    'Kenraalimajuri E.J.Raappana seurueineen.'
    >>> preprocessor("J.R.8. komentaja, ev. Antti")
    'JR 8. komentaja, ev. Antti'
    >>> preprocessor("Harlu JP.I.")
    'Harlu JP 1.'
    """

    # E.g. URR:n -> URR
    text = re.sub(r'(?<=\w):\w+', '', text)

    # KLo = Kotkan Lohko, 'Klo' will match
    text = re.sub(r'\bKlo\b', 'klo', text)

    # TykK
    text = re.sub(r'\b[Tt]yk\.K\b', 'TykK', text)

    # Div -> D
    text = re.sub(r'\b[Dd]iv\.\s*', 'D ', text)

    # D, Pr
    text = re.sub(r'\b(\d+)\.?\s*(?=D|Pr\b)', r'\1. ', text)

    # J.R. -> JR
    text = re.sub(r'\bJ\.[Rr]\.?\s*(?=\d)', 'JR ', text)
    # JR, JP
    text = re.sub(r'\b(J[RrPp])\.?(?=\d|I)', r'\1 ', text)
    # JR/55 -> JR 55
    text = re.sub(r'\b(?<=J[Rr])/(?=\d)', ' ', text)

    text = re.sub(r'\b(?<=J[RrPp] )I', '1', text)
    text = re.sub(r'\b(?<=J[RrPp] )II', '2', text)

    # AK, AKE
    text = re.sub(r'([IV])\.\s*(?=AKE?)', r'\1 ', text)

    # Match super unit as well
    for m in re.finditer(r'(?<=/)([A-Z]+\.?\s*\d+)', text):
        text += ' # {}'.format(m.group(0))

    for m in re.finditer(r'(?<=/)([0-9]+\.\s*\w+)', text):
        text += ' # {}'.format(m.group(0))

    text = text.strip()
    text = re.sub(r'\s+', ' ', text)

    return text

if __name__ == '__main__':
    if sys.argv[1] == 'test':
        import doctest
        doctest.testmod()
        exit()

    process_stage(sys.argv, preprocessor=preprocessor)
