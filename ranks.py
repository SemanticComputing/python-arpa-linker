from arpa_linker.arpa import Arpa, process, log_to_file
from rdflib import URIRef

def preprocessor(text):
    l = text.split('/')
    if len(l) > 1:
        for part in reversed(l):
            text = text + ' # ' + part

    return text

if __name__ == '__main__':

    log_to_file('ranks.log', 'INFO')

    arpa = Arpa('http://demo.seco.tkk.fi/arpa/warsa_actor_units')
    rdf_format = 'turtle'

    # Query the ARPA service, add the matches, and serialize the graph to disk.
    process('surma.ttl', rdf_format, 'output.ttl', rdf_format,
            URIRef('http://ldf.fi/schema/narc-menehtyneet1939-45/unit'),
            arpa, URIRef('http://ldf.fi/schema/narc-menehtyneet1939-45/joukko_osasto'),
            preprocessor=preprocessor, progress=True)
