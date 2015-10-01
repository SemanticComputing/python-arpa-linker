from arpa_linker.arpa import Arpa, process
from rdflib import Graph, URIRef

def preprocessor(text):
    l = text.split('/')
    if len(l) > 1:
        for part in reversed(l):
            text = text + ' # ' + part

    return text

if __name__ == '__main__':

    graph = Graph()
    graph.parse('surma.ttl', format='turtle')

    arpa = Arpa('http://demo.seco.tkk.fi/arpa/warsa_actor_units')

    # Query the ARPA service and add the matches
    process(graph, URIRef('http://ldf.fi/schema/narc-menehtyneet1939-45/unit'),
            arpa, URIRef('http://ldf.fi/schema/narc-menehtyneet1939-45/joukko_osasto'),
            preprocessor=preprocessor, progress=True)

    # Serialize the graph to disk
    graph.serialize(destination='output.ttl', format='turtle')


