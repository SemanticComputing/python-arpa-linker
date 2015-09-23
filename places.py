import re
from arpa import Arpa, process
from rdflib import Graph, URIRef

def preprocessor(text):
    text = text.replace('Yli-Tornio', 'Ylitornio')
    # Remove unit numbers that would otherwise be interpreted as Ii.
    text = re.sub('II(I)*', '', text)
    # Remove parentheses.
    text = re.sub('[()]', ' ', text)
    # Add a space after commas if they're followed by a word
    text = re.sub(r'(\w),(\w)', r'\1, \2', text)
    # Baseforming doesn't work for "Salla" so baseform that manually.
    text = re.sub(r'Salla(a?n?|s[st]a)?\b', 'Salla', text)
    # Detach names connected by hyphens to match places better.
    # Skip Yl[äi]-, Al[ia]-, and Iso-.
    text = re.sub(r'(?<!\b(Yl|Al|Is))(\w)-([A-ZÄÅÖ])', r'\2 \3', text)

    return text

if __name__ == '__main__':

    ignore = [
            'sillanpää',
            'saari',
            'p',
            'm',
            's',
            'pohjoinen',
            'tienhaara',
            'suomalainen',
            'venäläinen',
            'asema',
            'ns',
            'rajavartiosto',
            'esikunta',
            'kauppa',
            'ryhmä',
            'ilma',
            'olla',
            'ruotsi',
            'pakkanen',
            'rannikko',
            'koulu',
            'kirkonkylä',
            'saksa',
            'työväentalo',
            'kirkko',
            'alku',
            'lentokenttä',
            'luoto',
            'risti',
            'posti',
            'lehti',
            'susi',
            'tykki',
            'prikaati',
            'niemi',
            'ranta',
            'eteläinen',
            'lappi',
            'järvi',
            'kallio',
            'salainen',
            'kannas',
            'taavetti',
            'berliini',
            'hannula',
            'itä'
            ]

    no_duplicates = [
            'http://www.yso.fi/onto/suo/kunta',
            'http://ldf.fi/warsa/places/place_types/Kirkonkyla_kaupunki',
            'http://ldf.fi/warsa/places/place_types/Kyla',
            'http://ldf.fi/pnr-schema#place_type_560',
            'http://ldf.fi/warsa/places/place_types/Maastokohde'
            ]

    graph = Graph()
    graph.parse('input.ttl', format='turtle')

    arpa = Arpa('http://demo.seco.tkk.fi/arpa/warsa-event-place',
            remove_duplicates=no_duplicates, ignore=ignore)

    # Query the ARPA service and add the matches
    process(graph, URIRef('http://www.cidoc-crm.org/cidoc-crm/P7_took_place_at'),
            arpa, preprocessor=preprocessor, progress=True)

    # Serialize the graph to disk
    graph.serialize(destination='output.ttl', format='turtle')


