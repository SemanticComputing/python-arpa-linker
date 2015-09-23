from arpa import Arpa, process
from rdflib import Graph, URIRef

def preprocessor(text):
    return ", ".join(x.strip() for x in text.split("-"))

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
    'ii',
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
    'hannula'
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


