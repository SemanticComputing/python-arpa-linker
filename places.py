import re
from arpa_linker.arpa import Arpa, process, log_to_file
from rdflib import URIRef


def validator(graph, s):
    def validate(text, results):
        if not results:
            return results
        for i, place in enumerate(results):
            label = place.get('label')
            if label == "Rautalahti":
                results[i]['id'] = 'http://ldf.fi/warsa/places/karelian_places/k_place_33031'
            elif label == "Murtovaara":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10558843'
            elif label == "Saarijärvi":
                results[i]['id'] = 'http://ldf.fi/warsa/places/karelian_places/k_place_37458'
            elif label == "Myllykoski":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10130817'
            elif label == "Kuosmala":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10392668'
            elif label == "Tyrävaara":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10213175'
            elif label == "Kivivaara":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10543550'
            elif "Lieks" in text and label == "Nurmijärvi":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10588451'
            elif label == "Kotka":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10878654'
            elif label == "Malmi":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10012991'
            elif label == "Kylänmäki":
                results[i]['id'] = 'http://ldf.fi/pnr/P_10530797'

        return results
    return validate


def preprocessor(text, *args):
    text = text.replace('Yli-Tornio', 'Ylitornio')
    text = re.sub('Oin[ao]la', 'Oinaala', text)
    # Remove unit numbers that would otherwise be interpreted as Ii.
    text = re.sub('II(I)*', '', text)
    # Remove parentheses.
    text = re.sub('[()]', ' ', text)
    # Add a space after commas if they're followed by a word
    text = re.sub(r'(\w),(\w)', r'\1, \2', text)
    # Baseforming doesn't work for "Salla" so baseform that manually.
    text = re.sub(r'Salla(a?n?|s[st]a)?\b', 'Salla', text)
    # Ditto for Sommee.
    text = re.sub(r'Sommee(n?|s[st]a)?\b', 'Sommee', text)
    # Current bug in ARPA causes Uuras to not baseform correctly.
    text = re.sub(r'Uuraa(n?|s[st]a)?\b', 'Uuras', text)
    # Detach names connected by hyphens to match places better.
    # Skip Yl[äi]-, Al[ia]-, Iso-. and Pitkä-
    text = text.replace('Pitkä-', 'Pitkä#')
    text = re.sub(r'(?<!\b(Yl[äi]|Al[ia]|Iso))-([A-ZÄÅÖ])', r' \2', text)
    text = text.replace('Pitkä#', 'Pitkä-')

    text = text.replace('Inkilän kartano', '##')
    text = text.replace('Norjan Kirkkoniem', '##')
    text = text.replace('Pietari Autti', '##')

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
        'hannuksela'
        'itä',
        'karhu',
        'tausta',
        'korkea',
        'niska',
        'saha',
        'komi',
        'aho',
        'kantti',
        'martola',
        'rättö',
        'oiva',
        'harald',
        'honkanen',
        'koskimaa',
        'järvinen',
        'autti',
        'suokanta',
        'holsti',
        'mäkinen',
        'rahola',
        'viro',
        'hakkila',
        'frans',
        'haukiperä',
        'lauri',
        'kolla',
        'kekkonen',
        'kello',
        'kari',
        'nurmi',
        'tiainen',
        'läntinen',
        'pajala',
        'pajakka',
        'malm',
        'kolla',
        'hiidenmaa',
        'kyösti',
        'pohjola',
        'mauno',
        'pekkala',
        'kylä',
        'kirkonkylä, kaupunki',
        'vesimuodostuma',
        'maastokohde',
        'kunta',
        'kallela',
        'palojärvi',
        'maaselkä',  # the proper one does not exist yet
        'kalajoki',  # the proper one does not exist yet
        'turtola', # only for events!
        'pajari'  # only for events, remove for photos
        #'karsikko'?
    ]

    no_duplicates = [
        'http://www.yso.fi/onto/suo/kunta',
        'http://ldf.fi/warsa/places/place_types/Kirkonkyla_kaupunki',
        'http://ldf.fi/warsa/places/place_types/Kyla',
        'http://ldf.fi/warsa/places/place_types/Vesimuodostuma',
        'http://ldf.fi/warsa/places/place_types/Maastokohde',
        'http://ldf.fi/pnr-schema#place_type_540',
        'http://ldf.fi/pnr-schema#place_type_560',
    ]

    log_to_file('places.log', 'INFO')

    arpa = Arpa('http://demo.seco.tkk.fi/arpa/warsa-event-place',
            remove_duplicates=no_duplicates, ignore=ignore)

    rdf_format = 'turtle'

    # Query the ARPA service, add the matches, and serialize the graph to disk.
    process('input.ttl', rdf_format, 'output.ttl', rdf_format,
            #URIRef('http://purl.org/dc/terms/spatial'),
            URIRef('http://www.cidoc-crm.org/cidoc-crm/P7_took_place_at'),
            arpa,
            #URIRef('http://ldf.fi/warsa/photographs/place_string'),
            preprocessor=preprocessor, validator=validator, progress=True)
