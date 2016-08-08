import re
import sys
from link_helper import process_stage


def preprocessor(text, *args):
    """
    >>> preprocessor("Klo 8.52 ilmahälytys Viipurissa ja klo 9 pommitus Kotkan lohkoa vastaan.")
    ' 8.52 ilmahälytys Viipurissa ja  9 pommitus Kotkan lohko vastaan.'
    """
    text = text.strip()
    text = re.sub(r':\w+', ' ', text)
    # KLo = Kotkan Lohko
    text = re.sub(r'\bklo\b', '', text, flags=re.I)
    # ARPA has a problem with "lohkoa"
    text = re.sub(r'\blohkoa\b', 'lohko', text, flags=re.I)
    return text

if __name__ == '__main__':
    if sys.argv[1] == 'test':
        import doctest
        doctest.testmod()
        exit()

    process_stage(sys.argv, preprocessor=preprocessor)
