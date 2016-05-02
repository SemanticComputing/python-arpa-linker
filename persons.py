from datetime import datetime
from arpa_linker.arpa import Arpa, ArpaMimic, process, log_to_file, parse_args
from rdflib import URIRef
from rdflib.namespace import SKOS
import logging
import re
import sys

log_to_file('persons.log', 'INFO')
logger = logging.getLogger('arpa_linker.arpa')

dataset = ''


def validator(graph, s):

    def get_s_start_date():
        def parse_date_as_list(d):
            return datetime.strptime('-'.join(d[0:3]), "%Y-%m-%d").date()

        def get_event_date():
            date_uri = graph.value(s, URIRef('http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span'))
            try:
                d = str(date_uri).split('time_')[1].split('-')
                return parse_date_as_list(d)
            except ValueError:
                logger.warning("Invalid time-span URI: {}".format(date_uri))
                return None

        def get_photo_date():
            date_value = graph.value(s, URIRef('http://purl.org/dc/terms/created'))
            d = str(date_value).split('-')
            try:
                return parse_date_as_list(d)
            except ValueError:
                logger.warning("Invalid date: {}".format(date_value))
                return None

        if dataset == 'event':
            return get_event_date()
        elif dataset == 'photo':
            return get_photo_date()
        else:
            raise Exception('Dataset not defined or invalid')

    def get_ranks(person):
        props = person.get('properties', {})
        return props.get('rank_label', []) + props.get('promotion_rank', [])

    def validate(text, results):
        if not results:
            return results
        l = graph.value(s, SKOS.prefLabel)
        start = get_s_start_date()
        longest_matches = {}
        filtered = []
        for person in results:
            if person['id'] == 'http://ldf.fi/warsa/actors/person_p10276':
                logger.info("FAILURE: Filtering out person {}".format(person.get('id')))
                continue
            try:
                death_date = datetime.strptime(
                    person['properties']['death_date'][0].split('^')[0],
                    '"%Y-%m-%d"').date()
            except (KeyError, ValueError):
                logger.info("No death date found for {}".format(person.get('id')))
            else:
                if start and start > death_date:
                    logger.info(
                        "FAILURE: {} ({}) died ({}) before event start ({})".format(
                            person.get('label'), person.get('id'),
                            death_date, start))
                    continue
            # The person either died after the event or the date of death is unknown
            match_len = len(person.get('matches'))
            count = 0
            match = True
            for i, m in enumerate(person.get('matches'), 1):
                if match_len >= longest_matches.get(m, 0):
                    longest_matches[m] = match_len
                    count = count + 1

                if count > 0 and i != count:
                    logger.warning("Partial longest match for {} ({}): {}".format(
                        person.get('label'), person.get('id'),
                        person.get('matches'), l))

                if match_len < longest_matches.get(m, 0):
                    match = False
                    break
            if match:
                logger.info("{} ({}) preliminarily accepted".format(
                    person.get('label'),
                    person.get('id')))
                filtered.append(person)
            else:
                logger.info("FAILURE: {} {} ({}) failed validation after matching {} in {} (in preliminary step)".format(
                    get_ranks(person),
                    person.get('label'),
                    person.get('id'),
                    person.get('matches'),
                    l))

        res = []
        for p in filtered:
            match_len = len(p.get('matches'))
            ranks = get_ranks(p)
            if ('"Sotamies"' in ranks) and not re.findall(r"([Ss]otamie|[Ss]tm\b)", text):
                logger.info("FAILURE: Filterin out private {} {} ({}), matched {} in {}".format(
                    ranks,
                    p.get('label'),
                    p.get('id'),
                    p.get('matches'),
                    l))
            elif match_len >= longest_matches[p.get('matches')[0]]:
                logger.info("SUCCESS: {} {} ({}) passed validation, matching {} in {}".format(
                    ranks,
                    p.get('label'),
                    p.get('id'),
                    p.get('matches'),
                    l))
                res.append(p)
            else:
                logger.info("FAILURE: {} {} ({}) failed validation after matching {} in {}".format(
                    ranks,
                    p.get('label'),
                    p.get('id'),
                    p.get('matches'),
                    l))

        logger.info("PASSED VALIDATION: {}".format(res))
        return res

    return validate

list_regex = '(?:([A-ZÄÖÅ]\w+)(?:,\W*))?' * 10 + '(?:([A-ZÄÖÅ]\w+)?(?:\W+ja\W+)?([A-ZÄÖÅ]\w+)?)?'

_g_re = '(?:[Kk]enraali(?:majurit)?(?:t)?(?:)?\W+)' + list_regex
g_regex = re.compile(_g_re)

_el_re = '[Ee]verstiluutnantit(?:)?\W+' + list_regex
el_regex = re.compile(_el_re)

_ma_re = '[Mm]ajurit(?:)?\W+' + list_regex
ma_regex = re.compile(_ma_re)

_m_re = '[Mm]inisterit(?:)?\W+' + list_regex
m_regex = re.compile(_m_re)

_c_re = '[Kk]apteenit\W+' + list_regex
c_regex = re.compile(_c_re)


def repl(groups):

    def rep(m):
        res = r''
        for i in groups:
            if m.group(i):
                res = res + ' # § {}'.format(m.group(i))
        return '{} # '.format(res) if res else m.group(0)

    return rep


def add_titles(regex, title, text):
    people = regex.findall(text)
    for batch in people:
        groups = []
        for i, p in enumerate(batch, 1):
            if p:
                groups.append(i)
        if groups:
            logger.info('Adding titles ({}) to "{}"'.format(title, text))
            try:
                text = regex.sub(repl(groups), text)
            except Exception:
                logger.exception('Regex error while adding titles')
    return text.replace('§', title)


def replace_general_list(text):
    return add_titles(g_regex, 'kenraali', text)


def replace_el_list(text):
    return add_titles(el_regex, 'everstiluutnantti', text)


def replace_minister_list(text):
    return add_titles(m_regex, 'ministeri', text)


def replace_major_list(text):
    return add_titles(ma_regex, 'majuri', text)


def replace_captain_list(text):
    return add_titles(c_regex, 'kapteeni', text)


snellman_list = (
    "Eversti Snellman 17.Divisioonan komentaja.",
    "Piirros Aarne Nopsanen: Eversti Snellman.",
    "Hangon ryhmän komentaja ev. Snellman",
    "17. Divisioonan hiihtokilpailuiden palkintojenjakotilaisuudesta:Komentaja, eversti Snellman puhuu ennen palkintojen jakoa. Pöydällä pokaaleita.",
    "Divisioonan hiihtokilpailut Syvärin rannalla: Komentaja eversti Snellman toimitsijoiden seurassa.",
    "Divisioonan hiihtokilpailut Syvärin rannalla: Vänrikki E. Sevon haastattelee eversti Snellmania kilpailuiden johdosta."
)


to_be_lowercased = (
    "Eversti",
    "Luutnantti",
    "Majuri",
    "Kenraali"
)


def preprocessor(text, *args):
    """
    >>> preprocessor("Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, majurit: Müller, Pennanen, Kalpamaa, Varko.")
    'Kuva ruokailusta. Ruokailussa läsnä: kenraalimajuri Martola,  # Juho Koivisto # ministeri Salovaara # ministeri Horelli # ministeri Arola # ministeri Honka #  # everstiluutnantti Varis # everstiluutnantti Ehnrooth # everstiluutnantti Juva # everstiluutnantti Heimolainen # everstiluutnantti Björnström #  # majuri Müller # majuri Pennanen # majuri Kalpamaa # majuri Varko # .'
    >>> preprocessor("Kenraali Hägglund seuraa maastoammuntaa Aunuksen kannaksen mestaruuskilpailuissa.")
    ' # kenraaliluutnantti Hägglund #  seuraa maastoammuntaa Aunuksen kannaksen mestaruuskilpailuissa.'
    >>> preprocessor("Korkeaa upseeristoa maastoammunnan Aunuksen kannaksen mestaruuskilpailuissa.")
    'Korkeaa upseeristoa maastoammunnan Aunuksen kannaksen mestaruuskilpailuissa.'
    >>> preprocessor("Presidentti Ryti, sotamarsalkka Mannerheim, pääministeri, kenraalit  Neuvonen,Walden,Mäkinen, eversti Sihvo, kenraali Airo,Oesch, eversti Hersalo ym. klo 12.45.")
    '# Risto Ryti #, sotamarsalkka Mannerheim, pääministeri,  # kenraaliluutnantti Neuvonen # kenraaliluutnantti Walden # kenraaliluutnantti Mäkinen # eversti Sihvo,  # kenraaliluutnantti Airo # kenraaliluutnantti Oesch # eversti Hersalo ym. klo 12.45.'
    >>> preprocessor("Sotamarsalkka Raasulissa.")
    '# sotamarsalkka Mannerheim # Raasulissa.'
    >>> preprocessor("Eräs Brewster-koneista, jotka seurasivat marsalkan seuruetta.")
    'Eräs Brewster-koneista, jotka seurasivat # sotamarsalkka Mannerheim # seuruetta.'
    >>> preprocessor("Kenraali Walden Marsalkan junassa aterialla.")
    ' # kenraaliluutnantti Walden #  # sotamarsalkka Mannerheim # junassa aterialla.'
    >>> preprocessor('"Eläköön Sotamarsalkka"')
    'Eläköön # sotamarsalkka Mannerheim #'
    >>> preprocessor("Fältmarsalk Mannerheim mattager Hangögruppens anmälar av Öv. Koskimies.")
    'sotamarsalkka Mannerheim mattager Hangögruppens anmälar av Öv. Koskimies.'
    >>> preprocessor("Majuri Laaksonen JR 8:ssa.")
    '# everstiluutnantti Sulo Laaksonen # JR 8:ssa.'
    >>> preprocessor("Everstiluutnantti Laaksonen")
    '# everstiluutnantti Sulo Laaksonen #'
    >>> preprocessor("Vas: eversti Laaksonen, kapteeni Karu, ylikersantti Vorho, ja alikersantit Paajanen ja Nordin filmattavina. Oik. komentajakapteeni Arho juttelee muiden Mannerheim-ritarien kanssa.")
    'Vas: # everstiluutnantti Sulo Laaksonen #, kapteeni Karu, ylikersantti Vorho, ja alikersantit Paajanen ja Nordin filmattavina. Oik. komentajakapteeni Arho juttelee muiden Mannerheim-ritarien kanssa.'
    >>> preprocessor("Majuri Laaksosen komentopaikka mistä johdettiin viivytystaistelua Karhumäkilinjalla. Majuri Laaksonen seisomassa kuvan keskellä.")
    'majuri Laaksosen komentopaikka mistä johdettiin viivytystaistelua Karhumäkilinjalla. majuri Laaksonen seisomassa kuvan keskellä.'
    >>> preprocessor("Luutn. Juutilainen Saharan kauhu jouluk. Alussa.")
    '# kapteeni Juutilainen # # kapteeni Juutilainen # jouluk. Alussa.'
    >>> preprocessor("Kapteenit Palolampi ja Juutilainen ratsailla Levinassa.")
    ' # kapteeni Palolampi # kapteeni Juutilainen #  ratsailla Levinassa.'
    >>> preprocessor("kenraalit keskustelevat pienen tauon aikana, vas: eversti Paasonen, kenraalimajuri Palojärvi, kenraalimajuri Svanström, Yl.Esikuntapäällikkö jalkaväenkenraali Heinrichs ja eversti Vaala.")
    'kenraalit keskustelevat pienen tauon aikana, vas: eversti Paasonen, kenraalimajuri Palojärvi, kenraalimajuri Svanström, Yl.Esikuntapäällikkö jalkaväen # kenraaliluutnantti Heinrichs # # kenraalimajuri Vaala #.'
    """

    text = str(text).replace('"', '')
    logger.info('Preprocessing: {}'.format(text))
    if text.strip() == 'Illalla venäläisten viimeiset evakuointialukset mm. Josif Stalin lähtivät Hangosta.':
        return ''
    if text == "Lentomestari Oippa Tuominen.":
        text = "lentomestari Tuominen"
        logger.info('=> {}'.format(text))
        return text
    if text in snellman_list:
        logger.info('Snellman list: {}'.format(text))
        return 'kenraalimajuri Snellman'
    if text == 'Eversti Snellman ja Eversti Vaala.':
        logger.info('Snellman and Vaala: {}'.format(text))
        return 'kenraalimajuri Snellman # kenraalimajuri Vaala'

    orig = text

    # Mannerheim
    text = text.replace('Fältmarsalk', 'sotamarsalkka')
    text = re.sub(r'(?<![Ss]otamarsalkka )(?<![Mm]arsalkka )Mannerheim(?!-)(in|ille|ia)?\b', '# sotamarsalkka Mannerheim #', text)
    text = re.sub(r'([Ss]ota)?[Mm]arsalk(ka|an|alle|en)?\b(?! Mannerheim)', '# sotamarsalkka Mannerheim #', text)
    text = re.sub(r'[Yy]lipäällik(kö|ön|ölle|köä|kön)\b', '# sotamarsalkka Mannerheim #', text)
    text = re.sub(r'Marski(n|a|lle)?\b', '# sotamarsalkka Mannerheim #', text)

    for r in to_be_lowercased:
        text = text.replace(r, r.lower())
    text = text.replace('hal.neuv.', '')
    text = replace_general_list(text)
    text = replace_minister_list(text)
    text = replace_el_list(text)
    text = replace_major_list(text)
    text = replace_captain_list(text)
    text = re.sub(r'\b[Kk]enr(\.|aali) ', 'kenraaliluutnantti ', text)
    text = re.sub(r'\b[Kk]enr\.\b', 'kenraali§', text)
    text = re.sub(r'\b[Ee]v\.(?=(\b| ))', 'eversti§', text)
    text = re.sub(r'\b[Ll]uu(tn|nt)\.', 'luutnantti', text)
    text = re.sub(r'\b[Mm]aj\.', 'majuri', text)
    text = re.sub(r'\b[Kk]apt\.', 'kapteeni', text)
    text = text.replace('§', '')
    text = re.sub(r'[Ll]entomies', 'lentomestari', text)
    text = re.sub(r'[Gg]eneralmajor(s)?', 'kenraalimajuri', text)
    text = re.sub(r'\b[Ee]verstil\.', 'everstiluutnantti', text)
    text = re.sub(r'[Tt]ykistökenraali', 'tykistönkenraali', text)
    text = text.replace('F. E. Sillanpää', '##')
    text = text.replace('Paavo Nurmi', '##')
    text = text.replace('T. M. Kivimäki', 'T.M.Kivimäki')
    text = text.replace('Verner Viiklan', 'Verner Viikla')
    text = text.replace('Heinrichsin', 'Heinrichs')
    text = text.replace('Linderin', 'Linder')
    text = text.replace('Karl Takkula', 'K. Takkula')
    text = text.replace('Laiva Josif Stalin', '##')
    text = re.sub(r'(Aleksandra\W)?Kollontai(\b|lle|n|hin)', 'Alexandra Kollontay', text)
    text = re.sub(r'Blick(\b|ille|in)', 'Aarne Leopold Blick', text)
    text = text.replace('A.-E. Martola', 'Ilmari Armas-Eino Martola')
    text = re.sub(r'(?<!alikersantti\W)Neno(nen|selle|sen)\b', '## kenraaliluutnantti Nenonen', text)
    text = re.sub(r'[Mm]ajuri(\W+K\.\W*)? Kari(n|lle)?\b', 'everstiluutnantti Kari', text)
    text = text.replace('majuri V.Tuompo', '##')
    text = text.replace('Tuompo, Viljo Einar', 'kenraaliluutnantti Tuompo')
    text = text.replace('Erfurth & Tuompo', 'Waldemar Erfurth ja kenraaliluutnantti Tuompo')
    text = text.replace('[Kk]enraali(majuri|luutnantti) Siilasvuo', '# Hjalmar Fridolf Siilasvuo #')
    text = text.replace('Wuolijoki', '## Hella Wuolijoki')
    text = text.replace('Presidentti ja rouva R. Ryti', 'Risto Ryti # Gerda Ryti')
    text = re.sub('[Pp]residentti Ryti', '# Risto Ryti #', text)
    text = re.sub(r'[Mm]inisteri Koivisto', 'Juho Koivisto', text)
    text = re.sub(r'[Pp]residentti Kallio', '## Kyösti Kallio ##', text)
    text = re.sub(r'[Rr](ou)?va(\.)? Kallio', '## Kaisa Kallio ##', text)
    text = re.sub(r'[Ee]versti Vaala(n|lle|a)?\b', '# kenraalimajuri Vaala #', text)
    text = re.sub(r'(kenraaliluutnantti|eversti) Raappana', '# kenraalimajuri Raappana #', text)

    text = text.replace(r'Saharan kauhu', '# kapteeni Juutilainen #')
    text = text.replace(r'luutnantti Juutilainen', '# kapteeni Juutilainen #')

    text = re.sub(r'(?<!patterin päällikkö )[Kk]apteeni (Joppe )?Karhu(nen|sen)', '# kapteeni Jorma Karhunen #', text)
    text = text.replace(r'Wind', '# luutnantti Wind #')
    text = re.sub(r'(?<!3\. )(?<!III )(luutnantti|[Vv]änrikki|Lauri Wilhelm) Nissi(nen|sen)\b', '# vänrikki Lauri Nissinen #', text)
    # Hack because of duplicate person
    text = re.sub(r'((G\.)|([Ee]versti)) Snellman', '## everstiluutnantti G. Snellman', text)
    text = text.replace('Cajander', '## Aimo Kaarlo Cajander')
    text = re.sub('eversti(luutnantti)? Laaksonen', '# everstiluutnantti Sulo Laaksonen #', text)
    if 'JR 8' in text:
        text = re.sub('majuri Laaksonen', '# everstiluutnantti Sulo Laaksonen #', text)
    # Needs tweaking for photos
    #text = text.replace('G. Snellman', '## everstiluutnantti G. Snellman')
    text = text.replace('Ribbentrop', '## Joachim von_Ribbentrop')
    #text = re.sub(r'(?<!Josif\W)Stalin(ille|in|iin)?\b', 'Josif Stalin', text)
    #text = text.replace('Kuusisen hallituksen', '## O. W. Kuusinen')
    #text = text.replace('Molotov', '## V. Molotov')  # not for photos
    #text = re.sub(r'(?<!M\.\W)Kallio(lle|n)?\b', '## Kyösti Kallio', text)
    #text = text.replace('E. Mäkinen', '## kenraalimajuri Mäkinen')
    #text = text.replace('Ryti', '## Risto Ryti')
    #text = text.replace('Tanner', '## Väinö Tanner')
    text = re.sub(r'(?<!Aimo )(?<!Aukusti )(?<!Y\.)Tanner', '# Väinö Tanner #', text)
    #text = text.replace('Niukkanen', '## Juho Niukkanen')
    #text = text.replace('Söderhjelm', '## Johan Otto Söderhjelm')
    text = re.sub(r'(?<![Ee]verstiluutnantti )Paasikivi', '## Juho Kusti Paasikivi', text)
    text = re.sub(r'[Mm]inisteri Walden', '## kenraaliluutnantti Walden #', text)
    text = re.sub(r'(?<!eversti )(?<!kenraaliluutnantti )Walden', '## kenraaliluutnantti Walden #', text)
    text = re.sub('[vV]ääpeli( Oiva)? Tuomi(nen|selle|sen)', '## Oiva Emil Kalervo Tuominen', text)
    text = text.replace('Sotamies Pihlajamaa', 'sotamies Väinö Pihlajamaa')  # in photos
    text = text.replace('Martti Pihlaja ', ' # ')

    if text != orig:
        logger.info('Preprocessed to: {}'.format(text))

    return text


ignore = [
    'Ensio Pehr Hjalmar Siilasvuo',
    'Eric Väinö Tanner',
    'Erik Gustav Martin Heinrichs'
]


name_re = "^((?:[a-zA-ZäÄåÅöÖ-]\.[ ]*)|(?:[a-zA-ZäÄöÖåÅèü-]{3,}[ ]+))((?:[a-zA-ZäÄåÅöÖ-]\.[ ]*)|(?:[a-zA-ZäÄöÖåÅèü-]{3,}[ ]+))?((?:[a-zA-ZäÄåÅöÖ-]\.[ ]*)|(?:[a-zA-ZäÄöÖåÅèü-]{3,}[ ]+))*([A-ZÄÖÅÜ][_a-zA-ZäÄöÖåÅèü-]{2,})$"
name_re_compiled = re.compile(name_re)

name_re_exclude = "[a-zäåö]+\W[a-zäåö]+"
name_re_exclude_compiled = re.compile(name_re_exclude)


def pruner(candidate):
    if name_re_compiled.fullmatch(candidate):
        if not name_re_exclude_compiled.search(candidate):
            return candidate
    return None


def set_dataset(args):
    global dataset
    if str(args.tprop) == 'http://purl.org/dc/terms/subject':
        logger.info('Handling as photos')
        dataset = 'photo'
    else:
        logger.info('Handling as events')
        dataset = 'event'


if __name__ == '__main__':
    if sys.argv[1] == 'prune':
        args = parse_args(sys.argv[2:])
        set_dataset(args)
        process(args.input, args.fi, args.output, args.fo, args.tprop, prune_only=True,
                pruner=pruner, source_prop=args.prop, rdf_class=args.rdf_class,
                new_graph=args.new_graph, progress=True)
    elif sys.argv[1] == 'disambiguate':
        args = parse_args(sys.argv[3:])
        set_dataset(args)
        f = open(sys.argv[2])
        qry = f.read()
        f.close()
        arpa = ArpaMimic(qry, args.arpa, args.no_duplicates, args.min_ngram, ignore)
        process(args.input, args.fi, args.output, args.fo, args.tprop, arpa=arpa,
                source_prop=args.prop, rdf_class=args.rdf_class, new_graph=args.new_graph,
                progress=True)
    else:
        args = parse_args(sys.argv[1:])
        arpa = Arpa(args.arpa, args.no_duplicates, args.min_ngram, ignore)

        # Query the ARPA service, add the matches and serialize the graph to disk.
        process(args.input, args.fi, args.output, args.fo, args.tprop, arpa,
                source_prop=args.prop, rdf_class=args.rdf_class, new_graph=args.new_graph,
                preprocessor=preprocessor, validator=validator, progress=True,
                candidates_only=args.candidates_only)
