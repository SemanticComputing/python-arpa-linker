from collections import defaultdict
from datetime import date, datetime, timedelta
from link_helper import process_stage
from rdflib import URIRef
# from rdflib.namespace import SKOS
import logging
import re
import sys

logger = logging.getLogger('arpa_linker.arpa')

RANK_CLASS_SCORES = {
    'Kenraalikunta': 10,
    'Esiupseeri': 10,
    'Komppaniaupseeri': 5,
    'Upseeri': 5,
    'kirkollinen henkilöstö': 1,
    'Aliupseeri': -5,
    'Miehistö': -10,
    'lottahenkilostö': 0,
    'virkahenkilostö': 0,
    'Jääkäriarvo': 0,
    'Muu arvo': 0,
    'Päällystö': 0,
    'Saksalaisarvo': 0,
    'eläinlääkintähenkilöstö': 0,
    'lääkintähenkilöstö': 0,
    'musiikkihenkilöstö': 0,
    'tekninen henkilöstö': 0,
    'NA': 0
}

ALL_RANKS = (
    'sotilasvirkamies',
    'tuntematon',
    'alikersantti',
    'aliluutnantti',
    'alisotilasohjaaja',
    'alisotilasvirkamies',
    'aliupseeri',
    'aliupseerioppilas',
    'alokas',
    'apusisar',
    'asemestari',
    'eläinlääketieteen everstiluutnantti',
    'eläinlääketieteen kapteeni',
    'eläinlääketieteen luutnantti',
    'eläinlääketieteen majuri',
    'eläinlääkintäeversti',
    'eläinlääkintäeverstiluutnantti',
    'eläinlääkintäkapteeni',
    'eläinlääkintäkenraalimajuri',
    'eläinlääkintäluutnantti',
    'eläinlääkintämajuri',
    'erikoismestari',
    'eversti',
    'everstiluutnantti',
    'gewehrführer',
    'gruppenführer',
    'hauptzugführer',
    'hilfsgewehrführer',
    'hilfsgruppenführer',
    'ilmasuojelumies',
    'ilmasuojelusotamies',
    'insinöörikapteeni',
    'insinöörikapteeniluutnantti',
    'insinöörikenraalimajuri',
    'insinööriluutnantti',
    'insinöörimajuri',
    'jalkaväenkenraali',
    'jefreitteri',
    'jääkäri',
    'kadetti',
    'kansiupseeri',
    'kanslialotta',
    'kapteeni',
    'kapteeniluutnantti',
    'kenraali',
    'kenraaliluutnantti',
    'kenraalimajuri',
    'kenttäpiispa',
    'kersantti',
    'komentaja',
    'komentajakapteeni',
    'kommodori',
    'kontra-amiraali',
    'kornetti',
    'korpraali',
    'lentomekaanikko',
    'lentomestari',
    'linnoitustyönjohtaja',
    'lotta',
    'luotsi',
    'luutnantti',
    'lähetti',
    'lääkintäalikersantti',
    'lääkintäamiraali',
    'lääkintäeversti',
    'lääkintäeverstiluutnantti',
    'lääkintäkapteeni',
    'lääkintäkenraaliluutnantti',
    'lääkintäkenraalimajuri',
    'lääkintäkersantti',
    'lääkintäkorpraali',
    'lääkintälotta',
    'lääkintäluutnantti',
    'lääkintämajuri',
    'lääkintäsotamies',
    'lääkintävirkamies',
    'lääkintävääpeli',
    'majuri',
    'matruusi',
    'merivartija',
    'musiikkiluutnantti',
    'obersturmführer',
    'oberzugführer',
    'offizierstellvertreter',
    'oppilas',
    'paikallispäällikkö',
    'panssarijääkäri',
    'pioneeri',
    'pursimies',
    'rajajääkäri',
    'rajavääpeli',
    'rakuuna',
    'ratsumestari',
    'ratsumies',
    'ratsuväenkenraali',
    'ratsuvääpeli',
    'reservin aliluutnantti',
    'reservin kapteeni',
    'reservin kornetti',
    'reservin luutnantti',
    'reservin vänrikki',
    'rottenführer',
    'sairaanhoitaja',
    'sairaanhoitajaoppilas',
    'schütze',
    'siviili',
    'soitto-oppilas',
    'sotainvalidi',
    'sotakirjeenvaihtaja',
    'sotamarsalkka',
    'sotamies',
    'sotaylituomari',
    'sotilasalivirkamies',
    'sotilaskotisisar',
    'sotilasmestari',
    'sotilaspastori',
    'sotilaspoika',
    'sotilaspoliisi',
    'sturmmann',
    'suojeluskunta-alokas',
    'suojeluskuntakorpraali',
    'suojeluskuntasotamies',
    'suojeluskuntaupseeri',
    'suojeluskuntavääpeli',
    'suomen marsalkka',
    'toisen luokan nostomies',
    'tykistönkenraali',
    'tykkimies',
    'työvelvollinen',
    'unterscharführer',
    'untersturmführer',
    'upseerikokelas',
    'upseerioppilas',
    'vahtimestari',
    'vara-amiraali',
    'varavahtimestari',
    'varavääpeli',
    'vizefeldwebel',
    'vänrikki',
    'vääpeli',
    'yleisesikuntaupseeri',
    'ylihoitaja',
    'ylikersantti',
    'yliluutnantti',
    'ylimatruusi',
    'ylivääpeli',
    'zugführer',
)

all_rank_classes_regex = re.compile(r'\b{}\b'.format(r'\b|\b'.join(RANK_CLASS_SCORES.keys())), re.I)
all_ranks_regex = re.compile(r'\b{}\b'.format(r'\b|\b'.join(ALL_RANKS)), re.I)


class Validator:
    dataset = ''

    def __init__(self, graph, *args, **kwargs):
        self.graph = graph

    def parse_date(self, d):
        str_date = '-'.join(d.replace('"', '').split('^')[0].split('-')[0:3])
        return datetime.strptime(str_date, "%Y-%m-%d").date()

    def get_s_start_date(self, s):

        def get_event_date():
            date_uri = self.graph.value(s, URIRef('http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span'))
            try:
                d = str(date_uri).split('time_')[1]
                return self.parse_date(d)
            except ValueError:
                logger.warning("Invalid time-span URI: {}".format(date_uri))
                return None

        def get_photo_date():
            date_value = self.graph.value(s, URIRef('http://purl.org/dc/terms/created'))
            d = str(date_value)
            try:
                return self.parse_date(d)
            except ValueError:
                logger.warning("Invalid date for {}: {}".format(s, date_value))
                return None

        if self.dataset == 'event':
            return get_event_date()
        elif self.dataset == 'photo':
            return get_photo_date()
        else:
            raise Exception('Dataset not defined or invalid')

    def get_ranked_matches(self, results):
        """
        >>> v = Validator(None)
        >>> props = {'death_date': ['"1944-09-02"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Komppaniaupseeri"'],
        ...    'rank': ['"Vänrikki"']}
        >>> person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'lieutenant'}
        >>> props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
        ...    'promotion_date': ['"1942-04-26"^^xsd:date'],
        ...    'hierarchy': ['"Kenraalikunta"'],
        ...    'rank': ['"Kenraalimajuri"']}
        >>> person2 = {'properties': props, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'general'}
        >>> results = [person, person2]
        >>> rd = v.get_ranked_matches(results)
        >>> rd['A. Snellman']['uris']
        {'lieutenant'}
        >>> rd['A. Snellman']['score']
        -20
        >>> rd['Kenraalimajuri A. Snellman']['uris']
        {'general'}
        >>> rd['Kenraalimajuri A. Snellman']['score']
        0
        """

        d = {x.get('id'): set(x.get('matches')) for x in results}
        dd = defaultdict(set)
        for k, v in d.items():
            for match in v:
                dd[match].add(k)
        rd = {}
        for k in dd.keys():
            match_list = [s for s in dd.keys() if k in s and k != s]
            rd[k] = {'score': len(match_list) * -20, 'uris': dd[k]}
            for r in match_list:
                st = dd[k] - dd[r]
                rd[k]['uris'] = st
        return rd

    def get_match_scores(self, results):
        """
        >>> v = Validator(None)
        >>> props = {'death_date': ['"1944-09-02"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Komppaniaupseeri"'],
        ...    'rank': ['"Vänrikki"']}
        >>> person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'lieutenant'}
        >>> props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
        ...    'promotion_date': ['"1942-04-26"^^xsd:date'],
        ...    'hierarchy': ['"Kenraalikunta"'],
        ...    'rank': ['"Kenraalimajuri"']}
        >>> person2 = {'properties': props2, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'general'}
        >>> results = [person, person2]
        >>> scores = v.get_match_scores(results)
        >>> scores['general']
        0
        >>> scores['lieutenant']
        -20
        >>> props = {'death_date': ['"1942-04-28"^^xsd:date'],
        ...    'promotion_date': ['"1942-04-26"^^xsd:date'],
        ...    'hierarchy': ['"Kenraalikunta"'],
        ...    'rank': ['"Kenraalimajuri"']}
        >>> person = {'properties': props, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'general2'}
        >>> results = [person, person2]
        >>> scores = v.get_match_scores(results)
        >>> scores['general']
        0
        >>> scores['general2']
        0
        >>> props = {'death_date': ['"1944-06-30"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'rank': ['"Sotamies"']}
        >>> person = {'properties': props, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id1'}
        >>> props2 = {'death_date': ['"1943-09-22"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'rank': ['"Sotamies"']}
        >>> person2 = {'properties': props2, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id2'}
        >>> props3 = {'death_date': ['"1940-02-02"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'rank': ['"Sotamies"']}
        >>> person3 = {'properties': props3, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id3'}
        >>> results = [person, person2, person3]
        >>> scores = v.get_match_scores(results)
        >>> scores['id1']
        0
        >>> scores['id2']
        0
        >>> scores['id3']
        0
        """
        rd = self.get_ranked_matches(results)
        scores = {}
        for k, v in rd.items():
            for uri in v['uris']:
                scores[uri] = v['score']

        return scores

    def get_death_date(self, person):
        """
        >>> v = Validator(None)
        >>> ranks = {'death_date': ['"1940-02-01"^^xsd:date']}
        >>> person = {'properties': ranks}
        >>> v.get_death_date(person)
        datetime.date(1940, 2, 1)
        """
        try:
            death_date = self.parse_date(person['properties']['death_date'][0])
        except (KeyError, ValueError):
            logger.info("No death date found for {}".format(person.get('id')))
            return None
        return death_date

    def get_current_rank(self, person, event_date):
        """
        Get the latest rank the person had attained by the date given.
        >>> from datetime import date
        >>> v = Validator(None)
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-01"^^xsd:date'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        >>> person = {'properties': ranks}
        >>> d = date(1940, 3, 5)
        >>> v.get_current_rank(person, d)
        'Korpraali'
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-01"^^xsd:date'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        >>> person = {'properties': ranks}
        >>> d = date(1940, 4, 5)
        >>> v.get_current_rank(person, d)
        'Luutnantti'
        """
        props = person['properties']
        res = None
        latest_date = None
        for i, rank in enumerate(props.get('rank')):
            try:
                promotion_date = self.parse_date(props.get('promotion_date')[i])
            except:
                # Unknown date
                continue

            if promotion_date > event_date or latest_date and promotion_date < latest_date:
                # Not a current rank
                continue

            latest_date = promotion_date
            res = rank.replace('"', '')

        return res

    def get_fuzzy_current_ranks(self, person, event_date, rank_type, date_range=30):
        """
        >>> from datetime import date
        >>> v = Validator(None)
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1940-04-06"^^xsd:date'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        >>> person = {'properties': ranks}
        >>> d = date(1940, 3, 5)
        >>> r = v.get_fuzzy_current_ranks(person, d, 'rank')
        >>> len(r)
        2
        >>> 'Korpraali' in r
        True
        >>> 'Sotamies' in r
        True
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Luutnantti"']}
        >>> person = {'properties': ranks}
        >>> d = date(1943, 4, 5)
        >>> v.get_fuzzy_current_ranks(person, d, 'rank')
        {'Luutnantti'}
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Yleisesikuntaupseeri"']}
        >>> person = {'properties': ranks}
        >>> d = date(1943, 4, 5)
        >>> v.get_fuzzy_current_ranks(person, d, 'rank')
        {'Korpraali'}
        """
        props = person['properties']
        res = set()
        latest_date = None
        lowest_rank = None
        for i, rank in enumerate(props.get(rank_type)):

            rank = rank.replace('"', '')
            if rank == 'Yleisesikuntaupseeri':
                # Yleisesikuntaupseeri is not an actual rank.
                continue

            try:
                promotion_date = self.parse_date(props.get('promotion_date')[i])
            except:
                # Unknown date
                continue

            delta = timedelta(date_range)

            if promotion_date > event_date + delta:
                # promotion_date > upper boundary
                continue

            if promotion_date > event_date - delta:
                # lower boundary < promotion_date < upper boundary
                res.add(rank)
                continue

            if not latest_date or latest_date < promotion_date:
                latest_date = promotion_date
                lowest_rank = rank
                continue

            # event_date < lower boundary

        if lowest_rank:
            res.add(lowest_rank)

        return res

    def filter_promotions_after_wars(self, person, rank_type):
        props = person['properties']
        res = set()
        for i, rank in enumerate(props.get(rank_type)):
            try:
                promotion_date = self.parse_date(props.get('promotion_date')[i])
            except:
                # Unknown date
                res.add(rank.replace('"', ''))
                continue
            if promotion_date < date(1946, 1, 1):
                res.add(rank.replace('"', ''))

        return res

    def get_ranks_with_unknown_date(self, person):
        """
        >>> v = Validator(None)
        >>> props = {'death_date': ['"1976-09-02"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Aliupseeri"'],
        ...    'rank': ['"Lentomestari"']}
        >>> person = {'properties': props, 'matches': ['lentomestari Oiva Tuominen', 'Oiva Tuominen'], 'id': 'id1'}
        >>> v.get_ranks_with_unknown_date(person)
        ['Lentomestari']
        >>> ranks = {'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"NA"'],
        ...    'rank': ['"NA"']}
        >>> person = {'properties': ranks, 'matches': ['Adolf Hitler']}
        >>> v.get_ranks_with_unknown_date(person)
        ['NA']
        """
        res = []
        props = person['properties']
        for i, rank in enumerate(props.get('rank')):
            promotion_date = props.get('promotion_date')[i].replace('"', '')
            if promotion_date == 'NA':
                res.append(rank.replace('"', ''))

        return res

    def has_consistent_rank(self, person, text):
        """
        Check if the mention of the person in `text` is preceded by a rank that
        the person does not have, in which case return False. Otherwise return True.

        True/False is enough (as opposed to scoring different results),
        because either there is a match with a consistent rank, in which case
        matches are already scored accordingly, or there is no match with a rank.

        >>> v = Validator(None)
        >>> props = {'death_date': ['"1942-04-28"^^xsd:date'],
        ...    'promotion_date': ['"1942-04-26"^^xsd:date'],
        ...    'hierarchy': ['"Kenraalikunta"'],
        ...    'rank': ['"Kenraalimajuri"']}
        >>> person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}
        >>> v.has_consistent_rank(person, "sotamies A. Snellman")
        False
        >>> person = {'properties': props, 'matches': ['kenraalikunta A. Snellman', 'A. Snellman'], 'id': 'id'}
        >>> v.has_consistent_rank(person, "kenraalikunta A. Snellman")
        True

        This is a bit unfortunate, but it shouldn't be a problem.
        >>> person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}
        >>> v.has_consistent_rank(person, "upseeri A. Snellman")
        False

        >>> props = {'death_date': ['"1942-04-28"^^xsd:date'],
        ...    'promotion_date': ['"1942-04-26"^^xsd:date'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'rank': ['"Sotamies"']}
        >>> person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id'}
        >>> v.has_consistent_rank(person, "kenraalikunta A. Snellman")
        False
        """

        text_rank_re = r'\b(\w+)\b\s+'
        text_ranks = []

        for match in set(person['matches']):
            ranks_in_text = re.findall(text_rank_re + match, text)
            for r in ranks_in_text:
                if all_ranks_regex.findall(r) or all_rank_classes_regex.findall(r):
                    text_ranks.append(r.lower())
        if text_ranks:
            props = person['properties']
            ranks = [r.replace('"', '').lower() for r in set(props['rank'])]
            hierarchy = [r.replace('"', '').lower() for r in set(props['hierarchy'])]
            for t_rank in text_ranks:
                if t_rank in ranks or t_rank in hierarchy:
                    # Consistent rank found in context.
                    return True
            # Inconsistent rank found in context.
            return False
        # No rank found in context.
        return True

    def get_rank_score(self, person, s_date, text):
        """
        >>> from datetime import date
        >>> v = Validator(None)
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
        ...    'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        >>> person = {'properties': ranks, 'matches': ['Kenraali Karpalo']}
        >>> v.get_rank_score(person, date(1941, 3, 5), "Kenraali Karpalo")
        30
        >>> v.get_rank_score(person, date(1940, 3, 5), "Kenraali Karpalo")
        0
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1946-03-01"^^xsd:date'],
        ...    'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        >>> person = {'properties': ranks, 'matches': ['kenraali Karpalo']}
        >>> v.get_rank_score(person, None, "kenraali Karpalo")
        0
        >>> ranks = {'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
        ...    'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        >>> person = {'properties': ranks, 'matches': ['kenraalikunta Karpalo']}
        >>> v.get_rank_score(person, date(1941, 3, 5), "kenraalikunta Karpalo")
        30
        >>> v.get_rank_score(person, None, "kenraalikunta Karpalo")
        21
        >>> ranks = {'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"NA"'],
        ...    'rank': ['"NA"']}
        >>> person = {'properties': ranks, 'matches': ['Adolf Hitler']}
        >>> v.get_rank_score(person, date(1941, 3, 5), "Adolf Hitler")
        0
        >>> ranks = {'promotion_date': ['"NA"', '"NA"'],
        ...    'hierarchy': ['"Aliupseeri"', '"virkahenkilostö"'],
        ...    'rank': ['"Alikersantti"', '"Sotilasvirkamies"']}
        >>> person = {'properties': ranks, 'matches': ['Kari Suomalainen']}
        >>> v.get_rank_score(person, date(1941, 3, 5), "Piirros: Kari Suomalainen")
        0
        """

        if not self.has_consistent_rank(person, text):
            return -10

        props = person['properties']
        rank_classes = {r.replace('"', '') for r in props.get('hierarchy')}
        score = max([RANK_CLASS_SCORES.get(s, 0) for s in rank_classes])
        matches = set(person.get('matches'))
        rank_type = None

        if any([m for m in matches if all_ranks_regex.match(m.lower())]):
            rank_type = 'rank'
        elif any([m for m in matches if all_rank_classes_regex.match(m.lower())]):
            rank_type = 'hierarchy'
        else:
            # No rank found in matches.
            return score

        current_rank = None
        if s_date:
            # Event has a date
            ranks = self.get_fuzzy_current_ranks(person, s_date, rank_type)
            if ranks:
                current_rank = r'({})'.format(r'\b|\b'.join(ranks))
                additional_score = 20
            else:
                # Current rank not found, match ranks with unknown promotion dates
                ranks = self.get_ranks_with_unknown_date(person)
                if ranks:
                    current_rank = r'({})'.format(r'\b|\b'.join(ranks))
                    additional_score = 11
                else:
                    # No current ranks or ranks with unknown promotion dates
                    current_rank = 'NA'
        else:
            # Unknown event date, match any rank
            ranks = self.filter_promotions_after_wars(person, rank_type) or ['NA']
            current_rank = r'({})'.format(r'\b|\b'.join(ranks))
            additional_score = 11

        cur_rank_re = r'\b{}\b'.format(current_rank.lower())

        if any([m for m in matches if re.match(cur_rank_re, m, re.I)]):
            score += additional_score
        else:
            # This person did not have the matched rank at this time
            logger.info('Reducing score because of inconsistent rank from {} {} ({})'.format(
                ', '.join(props.get('rank', [])),
                person.get('label'),
                person.get('id')))
            score -= 10

        return score

    def get_date_score(self, person, s_date, s, e_label):
        """
        >>> from datetime import date
        >>> v = Validator(None)
        >>> props = {'death_date': ['"1940-02-01"^^xsd:date', '"1940-02-01"^^xsd:date',
        ...    '"1940-03-01"^^xsd:date']}
        >>> person = {'properties': props}
        >>> v.get_date_score(person, date(1941, 3, 5), None, None)
        -20
        >>> props = {'death_date': ['"1940-02-01"^^xsd:date', '"1940-02-01"^^xsd:date',
        ...    '"1940-03-01"^^xsd:date']}
        >>> person = {'properties': props}
        >>> v.get_date_score(person, date(1939, 3, 5), None, None)
        0
        >>> v.get_date_score(person, None, None, None)
        0
        >>> props = {}
        >>> person = {'properties': props}
        >>> v.get_date_score(person, date(1939, 3, 5), None, None)
        0
        """
        score = 0
        death_date = self.get_death_date(person)
        try:
            diff = s_date - death_date
        except:
            # Either date is unknown, no score adjustment
            pass
        else:
            if diff.days > 30:
                logger.info(
                    "DEAD PERSON: {p_label} ({p_uri}) died ({death_date}) more than a month"
                    "({diff} days) before start ({s_date}) of event {e_label} ({e_uri})"
                    .format(p_label=person.get('label'), p_uri=person.get('id'), diff=diff,
                        death_date=death_date, s_date=s_date, e_uri=s, e_label=e_label))
                score -= 20
            elif diff.days >= 0:
                logger.info(
                    "RECENTLY DEAD PERSON: {p_label} ({p_uri}) died {diff} days ({death_date}) before start "
                    "({s_date}) of event {e_label} ({e_uri})".format(p_label=person.get('label'), p_uri=person.get('id'),
                        diff=diff.days, death_date=death_date, s_date=s_date, e_uri=s, e_label=e_label))
        return score

    def get_name_score(self, person):
        """
        >>> v = Validator(None)
        >>> person = {'properties': {'first_names': ['"Turo Tero"']}, 'matches': ['kenraali Karpalo'], 'id': 'id'}
        >>> v.get_name_score(person)
        0
        >>> person = {'properties': {'first_names': ['"Turo Tero"']}, 'matches': ['Tero Karpalo'], 'id': 'id'}
        >>> v.get_name_score(person)
        5
        >>> person = {'properties': {'first_names': ['"Turo Tero"']}, 'matches': ['Turo Karpalo'], 'id': 'id'}
        >>> v.get_name_score(person)
        10
        >>> person = {'properties': {'first_names': ['"Turo"']}, 'matches': ['Turo Karpalo'], 'id': 'id'}
        >>> v.get_name_score(person)
        10
        """
        first_names = person['properties'].get('first_names', [None])[0]
        if not first_names:
            return 0

        first_names = first_names.replace('"', '')

        score = 0
        very_first_name = re.sub(r'^(\S+)\b.*$', r'\\b\1\\b', first_names)
        first_names = r'(\b{}\b)'.format(re.sub(r'\s+', r'\\b|\\b', first_names.strip()))
        matches = ' '.join(set(person.get('matches')))
        if re.search(first_names, matches):
            score += 5
            if re.search(very_first_name, matches):
                score += 5

        return score

    def get_score(self, person, s, s_date, text, results, ranked_matches):
        """
        >>> from datetime import date
        >>> v = Validator(None)
        >>> props = {'death_date': ['"1942-02-01"^^xsd:date', '"1942-02-01"^^xsd:date', '"1942-03-01"^^xsd:date'],
        ...    'promotion_date': ['"1940-02-01"^^xsd:date', '"1940-03-01"^^xsd:date', '"1941-03-01"^^xsd:date'],
        ...    'hierarchy': ['"Miehistö"', '"Miehistö"', '"Kenraalikunta"'],
        ...    'rank': ['"Sotamies"', '"Korpraali"', '"Kenraali"']}
        >>> person = {'properties': props, 'matches': ['kenraali Karpalo'], 'id': 'id'}
        >>> results = [person]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1941, 3, 5), 'kenraali Karpalo', results, ranked_matches)
        30
        >>> props = {'death_date': ['"1945-04-30"^^xsd:date', '"1945-04-30"^^xsd:date', '"1945-04-30"^^xsd:date'],
        ...    'first_names': ['"Adolf"', '"Adolf"'],
        ...    'promotion_date': ['"NA"', '"NA"', '"NA"'],
        ...    'hierarchy': ['"NA"', '"NA"', '"NA"'],
        ...    'rank': ['"NA"', '"NA"', '"NA"']}
        >>> person = {'properties': props, 'matches': ['Adolf Hitler'], 'id': 'id'}
        >>> results = [person]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1941, 3, 5), 'Adolf Hitler', results, ranked_matches)
        10
        >>> props = {'death_date': ['"1944-09-02"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Komppaniaupseeri"'],
        ...    'rank': ['"Vänrikki"']}
        >>> person = {'properties': props, 'matches': ['A. Snellman'], 'id': 'id1'}
        >>> props2 = {'death_date': ['"1942-04-28"^^xsd:date'],
        ...    'promotion_date': ['"1942-04-26"^^xsd:date'],
        ...    'hierarchy': ['"Kenraalikunta"'],
        ...    'rank': ['"Kenraalimajuri"']}
        >>> person2 = {'properties': props2, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'id2'}
        >>> results = [person, person2]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1942, 4, 27), 'Kenraalimajuri A. Snellman', results, ranked_matches)
        -30
        >>> v.get_score(person2, None, date(1942, 4, 27), 'Kenraalimajuri A. Snellman', results, ranked_matches)
        30
        >>> props = {'death_date': ['"1942-04-28"^^xsd:date'],
        ...    'promotion_date': ['"1942-04-26"^^xsd:date'],
        ...    'hierarchy': ['"Kenraalikunta"'],
        ...    'rank': ['"Kenraalimajuri"']}
        >>> person = {'properties': props, 'matches': ['A. Snellman', 'Kenraalimajuri A. Snellman'], 'id': 'id'}
        >>> results = [person]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1941, 11, 20), 'Kenraalimajuri A. Snellman', results, ranked_matches)
        0
        >>> props = {'death_date': ['"1976-09-02"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Aliupseeri"'],
        ...    'rank': ['"Lentomestari"']}
        >>> person = {'properties': props, 'matches': ['lentomestari Oiva Tuominen', 'Oiva Tuominen'], 'id': 'id1'}
        >>> props2 = {'death_date': ['"1944-04-28"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'rank': ['"Korpraali"']}
        >>> person2 = {'properties': props2, 'matches': ['Oiva Tuominen'], 'id': 'id2'}
        >>> props3 = {'death_date': ['"1940-04-28"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'rank': ['"Sotamies"']}
        >>> person3 = {'properties': props3, 'matches': ['Oiva Tuominen'], 'id': 'id3'}
        >>> results = [person, person2, person3]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1942, 4, 27), 'lentomestari Oiva Tuominen', results, ranked_matches)
        6
        >>> v.get_score(person2, None, date(1942, 4, 27), 'lentomestari Oiva Tuominen', results, ranked_matches)
        -30
        >>> v.get_score(person3, None, date(1942, 4, 27), 'lentomestari Oiva Tuominen', results, ranked_matches)
        -50
        >>> props = {'death_date': ['"1944-06-30"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'first_names': ['Arvi Petteri'],
        ...    'rank': ['"Sotamies"']}
        >>> person = {'properties': props, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id1'}
        >>> props2 = {'death_date': ['"1943-09-22"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'first_names': ['Petteri'],
        ...    'rank': ['"Sotamies"']}
        >>> person2 = {'properties': props2, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id2'}
        >>> props3 = {'death_date': ['"1940-02-02"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'first_names': ['Petteri Arvi'],
        ...    'rank': ['"Sotamies"']}
        >>> person3 = {'properties': props3, 'matches': ['sotamies Arvi Pesonen', 'Arvi Pesonen'], 'id': 'id3'}
        >>> results = [person, person2, person3]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1944, 5, 31), 'sotamies Arvi Pesonen', results, ranked_matches)
        11
        >>> v.get_score(person2, None, date(1944, 5, 31), 'sotamies Arvi Pesonen', results, ranked_matches)
        -19
        >>> v.get_score(person3, None, date(1944, 5, 31), 'sotamies Arvi Pesonen', results, ranked_matches)
        -14
        >>> props = {'death_date': ['"1944-06-15"^^xsd:date'],
        ...    'promotion_date': ['"NA"'],
        ...    'hierarchy': ['"Miehistö"'],
        ...    'first_names': ['"Tuomas"'],
        ...    'family_name': ['"Noponen"'],
        ...    'rank': ['"Korpraali"']}
        >>> person = {'properties': props, 'matches': ['Tuomas Noponen'], 'id': 'id1'}
        >>> results = [person]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1941, 8, 4), 'Tuomas Noponen', results, ranked_matches)
        0
        >>> props = {'death_date': ['"1999-08-10"^^xsd:date', '"1999-08-10"^^xsd:date'],
        ...    'promotion_date': ['"NA"', '"NA"'],
        ...    'first_names': ['"Kari"', '"Kari"'],
        ...    'family_name': ['"SUOMALAINEN"', '"SUOMALAINEN"'],
        ...    'hierarchy': ['"Aliupseeri"', '"virkahenkilostö"'],
        ...    'rank': ['"Alikersantti"', '"Sotilasvirkamies"']}
        >>> person = {'properties': props, 'matches': ['Kari Suomalainen'], 'id': 'id'}
        >>> results = [person]
        >>> ranked_matches = v.get_match_scores(results)
        >>> v.get_score(person, None, date(1941, 3, 5), 'Piirros Kari Suomalainen', results, ranked_matches)
        10
        """
        person_id = person.get('id')
        if person_id == 'http://ldf.fi/warsa/actors/person_1':
            # "Suomen marsalkka" is problematic as a rank so let's just always
            # score Mannerheim highly
            return 50
        rms = ranked_matches.get(person.get('id'), 0)
        ds = self.get_date_score(person, s_date, s, text)
        rs = self.get_rank_score(person, s_date, text)
        ns = self.get_name_score(person)

        return rms + ds + rs + ns

    def validate(self, results, text, s):
        if not results:
            return results
        res = []
        ranked = self.get_ranked_matches(results)
        s_date = self.get_s_start_date(s)
        for person in results:
            score = self.get_score(person, s, s_date, text, results, ranked)
            log_msg = "{} {} ({}) scored {}".format(
                ', '.join(person.get('properties', {}).get('rank', [])),
                person.get('label'),
                person.get('id'),
                score)

            if score > 0:
                log_msg = "PASS: " + log_msg
                res.append(person)
            else:
                log_msg = "FAIL: " + log_msg

            logger.info(log_msg)

        logger.info("{}/{} passed validation".format(len(res), len(results)))

        return res

        # l = graph.value(s, SKOS.prefLabel)


_name_part = r'[A-ZÄÖÅ]' + r'(?:(?:\.\s*|\w+\s+)?[A-ZÄÖÅ])?' * 2
list_regex = r'\b(?::)?\s*' + (r'(?:(' + _name_part + r'\w+,)(?:\s*))?') * 10 + \
    r'(?:(' + _name_part + r'\w+)?(?:\s+ja\s+)?([A-ZÄÖÅ](?:(?:\w|\.\s*|\w+\s+)?[A-ZÄÖÅ])?\w+)?)?'

_g_re = r'\b[Kk]enraali(?:t)?' + list_regex
g_regex = re.compile(_g_re)

_mg_re = r'\b[Kk]enraalimajur(?:i(?:t))|(?:eiksi)' + list_regex
mg_regex = re.compile(_mg_re)

_e_re = r'\b[Ee]verstit' + list_regex
e_regex = re.compile(_e_re)

_el_re = r'\b[Ee]verstiluutnantit' + list_regex
el_regex = re.compile(_el_re)

_ma_re = r'\b[Mm]ajurit' + list_regex
ma_regex = re.compile(_ma_re)

_m_re = r'[Mm]inisterit' + list_regex
m_regex = re.compile(_m_re)

_c_re = r'\b[Kk]apteenit' + list_regex
c_regex = re.compile(_c_re)

_l_re = r'\b[Ll]uutnantit' + list_regex
l_regex = re.compile(_l_re)

_v_re = r'\b[Vv]änrikit' + list_regex
v_regex = re.compile(_v_re)

_k_re = r'\b[Kk]ersantit' + list_regex
k_regex = re.compile(_k_re)

_ak_re = r'\b[Aa]likersantit' + list_regex
ak_regex = re.compile(_ak_re)

_sv_re = r'[Ss]ot(?:(?:ilasvirk(?:(?:\.\s*)|(?:(?:ailija[t]?|amies|amiehet)\s+)))|(?:\.\s*virk\.\s*))' + list_regex
sv_regex = re.compile(_sv_re)


def repl(groups):

    def rep(m):
        res = r''
        for i in groups:
            if m.group(i):
                res = res + ' § {}'.format(m.group(i))
        res = '{}'.format(res) if res else m.group(0)
        return res

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
    """
    >>> replace_general_list('kenraali Walden  # kenraalikunta Mannerheim # junassa aterialla.')
    ' kenraali Walden  # kenraalikunta Mannerheim # junassa aterialla.'

    This is unfortunate, but whatcha gonna do.
    >>> replace_general_list("Kenraali Weckman, Saksan Sota-akatemian komentaja vierailulla Suomessa: Saksan sotilasasiamiehen eversti Kitschmannin seurassa.")
    ' kenraali Weckman, kenraali Saksan Sota-akatemian komentaja vierailulla Suomessa: Saksan sotilasasiamiehen eversti Kitschmannin seurassa.'
    """
    return add_titles(g_regex, 'kenraali', text)


def replace_major_general_list(text):
    return add_titles(g_regex, 'kenraalimajuri', text)


def replace_e_list(text):
    return add_titles(e_regex, 'eversti', text)


def replace_el_list(text):
    return add_titles(el_regex, 'everstiluutnantti', text)


def replace_minister_list(text):
    return add_titles(m_regex, 'ministeri', text)


def replace_major_list(text):
    """
    >>> replace_major_list("Vas: insinööri L.Jyväskorpi, Tampella, insinööri E.Ilmonen, Tampella, eversti A.Salovirta, Tväl.os/PM, insinööri Donner, Tampella, majuri A.Vara, Tväl.os/PM.")
    'Vas: insinööri L.Jyväskorpi, Tampella, insinööri E.Ilmonen, Tampella, eversti A.Salovirta, Tväl.os/PM, insinööri Donner, Tampella, majuri A.Vara, Tväl.os/PM.'
    >>> replace_major_general_list("Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, majurit: Müller, Pennanen, Kalpamaa, Varko.")
    'Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, majurit: Müller, Pennanen, Kalpamaa, Varko.'
    """
    return add_titles(ma_regex, 'majuri', text)


def replace_captain_list(text):
    return add_titles(c_regex, 'kapteeni', text)


def replace_lieutenant_list(text):
    """
    >>> replace_lieutenant_list("Rautaristin saajat: Eversti A. Puroma, majurit A.K Airimo ja V. Lehvä, luutnantit K. Sarva ja U. Jalkanen, vänrikit T. Laakso, R. Kanto, N. Vuolle ja Y. Nuortio, kersantit T. Aspegren ja H. Kalliaisenaho, alikersantit L. Nousiainen, V. Launonen ja Salmi sekä korpraali R. Keihta.")
    'Rautaristin saajat: Eversti A. Puroma, majurit A.K Airimo ja V. Lehvä,  luutnantti K. Sarva luutnantti U. Jalkanen, vänrikit T. Laakso, R. Kanto, N. Vuolle ja Y. Nuortio, kersantit T. Aspegren ja H. Kalliaisenaho, alikersantit L. Nousiainen, V. Launonen ja Salmi sekä korpraali R. Keihta.'
    """
    return add_titles(l_regex, 'luutnantti', text)


def replace_v_list(text):
    return add_titles(v_regex, 'vänrikki', text)


def replace_k_list(text):
    return add_titles(k_regex, 'kersantti', text)


def replace_ak_list(text):
    return add_titles(ak_regex, 'alikersantti', text)


def replace_sv_list(text):
    """
    >>> replace_sv_list("TK-rintamakirjeenvaihtaja Yläjärvellä (vas. Sot.virk. Kapra, Jalkanen, vänr. Rahikainen).")
    'TK-rintamakirjeenvaihtaja Yläjärvellä (vas.  sotilasvirkamies Kapra, sotilasvirkamies Jalkanen,vänr. Rahikainen).'
    >>> replace_sv_list("Sotilasvirk. Kapra, Jalkanen, vänr. Rahikainen).")
    ' sotilasvirkamies Kapra, sotilasvirkamies Jalkanen,vänr. Rahikainen).'
    >>> replace_sv_list("Sotilasvirkailija Kapra, Jalkanen, vänr. Rahikainen).")
    ' sotilasvirkamies Kapra, sotilasvirkamies Jalkanen,vänr. Rahikainen).'
    >>> replace_sv_list("Komentajasta oikealla: Björnsson Mehlem, sot.virk.Zenker, Farr, luutnantti Miettinen,etualalla oikealla Scott.")
    'Komentajasta oikealla: Björnsson Mehlem,  sotilasvirkamies Zenker, sotilasvirkamies Farr,luutnantti Miettinen,etualalla oikealla Scott.'
    """
    return add_titles(sv_regex, 'sotilasvirkamies', text)


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
    "Kenraali",
    "Kapteeni",
    "Kersantti",
    "Vänrikki"
)


def preprocessor(text, *args):
    """
    >>> preprocessor("Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka," \
            " everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, majurit: Müller, Pennanen, Kalpamaa, Varko.")
    'Kuva ruokailusta. Ruokailussa läsnä: kenraalimajuri Martola,  # Juho Koivisto, ministeri Salovaara, ministeri Horelli, ministeri Arola, ministeri Honka, everstiluutnantti Varis, everstiluutnantti Ehnrooth, everstiluutnantti Juva, everstiluutnantti Heimolainen, everstiluutnantti Björnström, majuri Müller, majuri Pennanen, majuri Kalpamaa, majuri Varko.'
    >>> preprocessor("Kenraali Hägglund seuraa maastoammuntaa Aunuksen kannaksen mestaruuskilpailuissa.")
    ' kenraalikunta Hägglund seuraa maastoammuntaa Aunuksen kannaksen mestaruuskilpailuissa.'
    >>> preprocessor("Kenraali Karl Oesch seuraa maastoammuntaa.")
    ' kenraalikunta Karl Oesch seuraa maastoammuntaa.'
    >>> preprocessor("Korkeaa upseeristoa maastoammunnan Aunuksen kannaksen mestaruuskilpailuissa.")
    'Korkeaa upseeristoa maastoammunnan Aunuksen kannaksen mestaruuskilpailuissa.'
    >>> preprocessor("Presidentti Ryti, sotamarsalkka Mannerheim, pääministeri, kenraalit  Neuvonen,Walden,Mäkinen, eversti Sihvo, kenraali Airo,Oesch, eversti Hersalo ym. klo 12.45.")
    '# Risto Ryti #, sotamarsalkka Mannerheim, pääministeri,  kenraalikunta Neuvonen, kenraalikunta Walden, kenraalikunta Mäkinen, eversti Sihvo,  kenraalikunta Airo, kenraalikunta Oesch, eversti Hersalo ym. klo 12.45.'
    >>> preprocessor("Sotamarsalkka Raasulissa.")
    '# kenraalikunta Mannerheim # Raasulissa.'
    >>> preprocessor("Eräs Brewster-koneista, jotka seurasivat marsalkan seuruetta.")
    'Eräs Brewster-koneista, jotka seurasivat # kenraalikunta Mannerheim # seuruetta.'
    >>> preprocessor("Kenraali Walden Marsalkan junassa aterialla.")
    ' kenraalikunta Walden # kenraalikunta Mannerheim # junassa aterialla.'
    >>> preprocessor('"Eläköön Sotamarsalkka"')
    'Eläköön # kenraalikunta Mannerheim #'
    >>> preprocessor("Fältmarsalk Mannerheim mattager Hangögruppens anmälar av Öv. Koskimies.")
    'sotamarsalkka Mannerheim mattager Hangögruppens anmälar av Öv. Koskimies.'
    >>> preprocessor("Majuri Laaksonen JR 8:ssa.")
    'majuri Sulo Laaksonen JR 8:ssa.'
    >>> preprocessor("Everstiluutnantti Laaksonen")
    'everstiluutnantti Sulo Laaksonen'
    >>> preprocessor("Vas: eversti Laaksonen, kapteeni Karu, ylikersantti Vorho, ja alikersantit Paajanen ja Nordin filmattavina. Oik. komentajakapteeni Arho juttelee muiden Mannerheim-ritarien kanssa.")
    'Vas: everstiluutnantti Sulo Laaksonen, kapteeni Karu, ylikersantti Vorho, ja  alikersantti Paajanen alikersantti Nordin filmattavina. Oik. komentajakapteeni Arho juttelee muiden Mannerheim-ritarien kanssa.'
    >>> preprocessor("Majuri Laaksosen komentopaikka mistä johdettiin viivytystaistelua Karhumäkilinjalla. Majuri Laaksonen seisomassa kuvan keskellä.")
    'Majuri Laaksosen komentopaikka mistä johdettiin viivytystaistelua Karhumäkilinjalla. Majuri Laaksonen seisomassa kuvan keskellä.'
    >>> preprocessor("Luutn. Juutilainen Saharan kauhu jouluk. Alussa.")
    '# kapteeni Juutilainen # # kapteeni Juutilainen # jouluk. Alussa.'
    >>> preprocessor("Kapteenit Palolampi ja Juutilainen ratsailla Levinassa.")
    ' kapteeni Palolampi kapteeni Juutilainen ratsailla Levinassa.'
    >>> preprocessor("kenraalit keskustelevat pienen tauon aikana, vas: eversti Paasonen, kenraalimajuri Palojärvi, kenraalimajuri Svanström, Yl.Esikuntapäällikkö jalkaväenkenraali Heinrichs ja eversti Vaala.")
    'kenraalit keskustelevat pienen tauon aikana, vas: eversti Paasonen, kenraalimajuri Palojärvi, kenraalimajuri Svanström, Yl.Esikuntapäällikkö jalkaväenkenraali Heinrichs ja eversti Vaala.'
    >>> preprocessor("Radioryhmän toimintaa: Selostaja työssään ( Vänrikki Seiva, sot.virk. Kumminen ja Westerlund).")
    'Radioryhmän toimintaa: Selostaja työssään ( vänrikki Seiva,  sotilasvirkamies Kumminen sotilasvirkamies Westerlund).'
    >>> preprocessor("TK-rintamakirjeenvaihtaja Yläjärvellä (vas. Sot.virk. Kapra, Jalkanen, vänr. Rahikainen).")
    ' sotilasvirkamies Yläjärvellä (vas.  sotilasvirkamies Kapra, sotilasvirkamies Jalkanen, vänrikki  Rahikainen).'
    >>> preprocessor("Ulkomaisten lehtimiesten retkikunta etulinjan komentopaikalla Tornion rintamalla 3/10-44. Komentaja, everstiluutnantti Halsti selostaa tilannetta kaistallaan piirtäen kepillä kartan maantiehen. Komentajasta oikealla: Björnsson Mehlem, sot.virk.Zenker, Farr, luutnantti Miettinen,etualalla oikealla Scott.")
    'Ulkomaisten lehtimiesten retkikunta etulinjan komentopaikalla Tornion rintamalla 3/10-44. Komentaja, everstiluutnantti Halsti selostaa tilannetta kaistallaan piirtäen kepillä kartan maantiehen. Komentajasta oikealla: Björnsson Mehlem,  sotilasvirkamies Zenker, sotilasvirkamies Farr, luutnantti Miettinen, etualalla oikealla Scott.'
    >>> preprocessor("Viestiosasto 1: Sotilasradiosähköttäjien tutkinossa 27.4.1942 todistuksen saaneet, vas. oikealle: Vänrikki Aro, korpraali Räsänen, vänrikki Nordberg, sotilasmestari Kivi, luutnantti Päiviö, sotilasmestari Lavola, sot.virk. Halonen, alikersantti Rosenberg, vänrikki Lindblad, sot.virk. Österman, alikersantti Salenius.")
    'Viestiosasto 1: Sotilasradiosähköttäjien tutkinossa 27.4.1942 todistuksen saaneet, vas. oikealle: vänrikki Aro, korpraali Räsänen, vänrikki Nordberg, sotilasmestari Kivi, luutnantti Päiviö, sotilasmestari Lavola,  sotilasvirkamies Halonen, alikersantti Rosenberg, vänrikki Lindblad,  sotilasvirkamies Österman, alikersantti Salenius.'
    >>> preprocessor("Ev. luutn.Paasonen ja saks. Amiraali keskuselevat")
    'everstiluutnantti Paasonen ja saks. Amiraali keskuselevat'
    >>> preprocessor("Ev. luutnantti Vänttinen")
    'everstiluutnantti Vänttinen'
    >>> preprocessor("Ev. luutn. Rauramo")
    'everstiluutnantti  Rauramo'
    >>> preprocessor("TK-Pärttyli Virkki erään lennon jälkeen.")
    'sotilasvirkamies Pärttyli Virkki erään lennon jälkeen.'
    >>> preprocessor("Virkki,erään lennon jälkeen.")
    'Virkki, erään lennon jälkeen.'
    >>> preprocessor("TK-mies Hiisivaara.")
    ' sotilasvirkamies Hiisivaara.'
    >>> preprocessor("Tk-miehet Varo, Itänen ja Tenkanen kuvaamassa Väinämöisen ammuntaa")
    ' sotilasvirkamies Varo, sotilasvirkamies Itänen sotilasvirkamies Tenkanen kuvaamassa Väinämöisen ammuntaa'
    >>> preprocessor("Rautaristin saajat: Eversti A. Puroma, majurit A.K Airimo ja V. Lehvä, luutnantit K. Sarva ja U. Jalkanen, vänrikit T. Laakso, R. Kanto, N. Vuolle ja Y. Nuortio, kersantit T. Aspegren ja H. Kalliaisenaho, alikersantit L. Nousiainen, V. Launonen ja Salmi sekä korpraali R. Keihta.")
    'Rautaristin saajat: eversti A. Puroma,  majuri A.G. Airimo majuri V. Lehvä,  luutnantti K. Sarva luutnantti U. Jalkanen,  vänrikki T. Laakso, vänrikki R. Kanto, vänrikki N. Vuolle vänrikki Y. Nuortio,  kersantti T. Aspegren kersantti H. Kalliaisenaho,  alikersantti L. Nousiainen, alikersantti V. Launonen alikersantti Salmi sekä korpraali R. Keihta.'
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
        if text == "Piirros Aarne Nopsanen: Eversti Snellman.":
            return "Aarne Nopsanen # kenraalimajuri Snellman"
        return 'kenraalimajuri Snellman'
    if text == 'Eversti Snellman ja Eversti Vaala.':
        logger.info('Snellman and Vaala: {}'.format(text))
        return 'kenraalimajuri Snellman # eversti Vaala'

    orig = text

    # Mannerheim
    text = text.replace('Fältmarsalk', 'sotamarsalkka')
    text = re.sub(r'(?<![Ss]otamarsalkka )(?<![Mm]arsalkka )Mannerheim(?!-)(in|ille|ia)?\b', '# kenraalikunta Mannerheim #', text)
    text = re.sub(r'([Ss]ota)?[Mm]arsalk(ka|an|alle|en)?\b(?! Mannerheim)', '# kenraalikunta Mannerheim #', text)
    text = re.sub(r'[Yy]lipäällik(kö|ön|ölle|köä|kön)\b', '# kenraalikunta Mannerheim #', text)
    text = re.sub(r'Marski(n|a|lle)?\b', '# kenraalikunta Mannerheim #', text)

    # E.g. von Bonin -> von_Bonin
    text = re.sub(r'\bvon\s+(?=[A-ZÄÅÖ])', 'von_', text)

    text = text.replace('A.K Airimo', 'A.G. Airimo')

    # E.g. "TK-mies"
    text = re.sub(r'[Tk][Kk]-[a-zäåö]+', r'sotilasvirkamies', text)

    for r in to_be_lowercased:
        text = text.replace(r, r.lower())
    text = text.replace('hal.neuv.', '')
    text = text.replace("luutnantti Herman ja Yrjö Nykäsen", "luutnantti Herman Nykänen # luutnantti Yrjö Nykänen")
    text = replace_general_list(text)
    text = replace_minister_list(text)
    text = replace_el_list(text)
    text = replace_major_list(text)
    text = replace_captain_list(text)
    text = replace_sv_list(text)
    text = replace_v_list(text)
    text = replace_k_list(text)
    text = replace_ak_list(text)
    text = replace_lieutenant_list(text)

    text = re.sub(r'\b[Kk]enr\.\s*([a-z])', r'kenraali§\1', text)
    text = re.sub(r'\b[Ee]v\.\s*([a-z])', r'eversti§\1', text)
    text = re.sub(r'\b[Ee]v\.', 'eversti ', text)
    text = re.sub(r'\b[Ll]uu(tn|nt)\.', 'luutnantti ', text)
    text = re.sub(r'\b[Mm]aj\.', 'majuri ', text)
    text = re.sub(r'\b[Kk]apt\.\s*([a-z])', r'kapteeni§\1', text)
    text = re.sub(r'\b[Kk]apt\.', 'kapteeni ', text)
    text = text.replace('§', '')
    text = re.sub(r'\b[Vv]änr\.', 'vänrikki ', text)
    text = re.sub(r'\b[Ss]ot\.\s*[Vv]irk\.', 'sotilasvirkamies ', text)
    text = re.sub(r'[Ll]entomies', 'lentomestari', text)
    text = re.sub(r'[Gg]eneralmajor(s)?', 'kenraalimajuri', text)
    text = re.sub(r'\b[Ee]verstil\.', 'everstiluutnantti', text)
    text = re.sub(r'[Tt]ykistökenraali', 'tykistönkenraali', text)
    text = re.sub(r'[Tk][Kk]-([A-ZÄÖÅ])', r'sotilasvirkamies \1', text)
    text = re.sub(r'\bkenraali\b', 'kenraalikunta', text)

    text = re.sub(r'[Ll]ääkintäkenraali\b', 'kenraalikunta', text)

    text = text.replace('Paavo Nurmi', '#')
    text = text.replace('Heinrichsin', 'Heinrichs')
    text = text.replace('Laiva Josif Stalin', '#')
    text = re.sub(r'(Aleksandra\W)?Kollontai(\b|lle|n|hin)', 'Alexandra Kollontay', text)
    text = re.sub(r'Blick(\b|ille|in)', 'Aarne Leopold Blick', text)
    text = text.replace('A.-E. Martola', 'kenraalikunta Ilmari Martola')
    text = re.sub(r'(?<!alikersantti\W)(?<!kenraalimajuri\W)Neno(nen|selle|sen)\b', '# kenraalikunta Nenonen', text)
    # Some young guy in one photo
    text = text.replace('majuri V.Tuompo', '#')
    text = text.replace('Tuompo, Viljo Einar', 'kenraalikunta Tuompo')
    text = text.replace('Erfurth & Tuompo', 'Erfurth ja kenraalikunta Tuompo')
    text = text.replace('Erfurth', 'Waldemar Erfurth')
    text = text.replace('[Kk]enraali(majuri|luutnantti) Siilasvuo', '# Hjalmar Fridolf Siilasvuo #')
    text = text.replace('Wuolijoki', '# Hella Wuolijoki')
    text = text.replace('Presidentti ja rouva R. Ryti', 'Risto Ryti # Gerda Ryti')
    text = re.sub('[Pp]residentti Ryti', '# Risto Ryti #', text)
    text = re.sub(r'[Mm]inisteri Koivisto', '# Juho Koivisto', text)
    text = re.sub(r'[Pp]residentti Kallio', '# Kyösti Kallio #', text)
    text = re.sub(r'[Rr](ou)?va(\.)? Kallio', '# Kaisa Kallio #', text)
    # John Rosenbröijer is also a possibility, but photos were checked manually
    text = re.sub(r'[RB]osenbröijer(in|ille|ia)?\b', '# Edvin Rosenbröijer #', text)
    text = re.sub(r'Turo Kart(on|olle|toa)\b', '# Turo Kartto #', text)

    text = text.replace('Hitler', '# Adolf Hitler')

    text = re.sub(r'(Saharan|Marokon) kauhu', '# kapteeni Juutilainen #', text)
    text = re.sub(r'luutnantti\s+Juutilainen', '# kapteeni Juutilainen #', text)

    text = re.sub(r'(?<!patterin päällikkö )[Kk]apteeni (Joppe )?Karhu(nen|sen)', '# kapteeni Jorma Karhunen #', text)
    text = text.replace(r'Wind', '# luutnantti Wind #')
    text = re.sub(r'(?<!3\. )(?<!III )(luutnantti|[Vv]änrikki|Lauri Wilhelm) Nissi(nen|sen)\b', '# vänrikki Lauri Nissinen #', text)
    text = text.replace('Cajander', 'Aimo Kaarlo Cajander')
    text = re.sub(r'[Ee]versti(luutnantti)? Laaksonen', 'everstiluutnantti Sulo Laaksonen', text)
    if 'JR 8' in text.upper():
        text = re.sub(r'\b[Mm]ajuri Laaksonen', 'majuri Sulo Laaksonen', text)
    # Needs tweaking for photos
    # text = text.replace('Kuusisen hallituksen', '## O. W. Kuusinen')
    # text = text.replace('E. Mäkinen', '## kenraalimajuri Mäkinen')
    text = re.sub(r'(?<!Aimo )(?<!Aukusti )(?<!Y\.)Tanner', '# Väinö Tanner #', text)
    # text = text.replace('Niukkanen', '## Juho Niukkanen')
    # text = text.replace('Söderhjelm', '## Johan Otto Söderhjelm')
    text = re.sub(r'(?<![Ee]verstiluutnantti )Paasikivi', '# Juho Kusti Paasikivi', text)
    text = re.sub(r'[Mm]inisteri Walden', '# kenraalikunta Walden', text)
    text = re.sub(r'(?<![Ee]versti )(?<![Kk]enraaliluutnantti )(?<![Kk]enraalimajuri )(?<![Kk]enraalikunta )Walden', '# kenraaliluutnantti Walden #', text)
    text = re.sub(r'[vV]ääpeli( Oiva)? Tuomi(nen|selle|sen)', '# lentomestari Oiva Tuominen', text)
    text = re.sub(r'Ukko[ -]Pekka(\W+Svinhufvud)?', 'Pehr Evind Svinhufvud', text)
    text = re.sub(r'[Pp]residentti Svinhufvud', 'Pehr Evind Svinhufvud', text)
    text = re.sub(r'[Pp]residentti\s+ja\s+rouva\s+Svinhufvud', 'Pehr Evind Svinhufvud # Ellen Svinhufvud #', text)
    text = re.sub(r'[Rr]ouva\s+Svinhufvud', '# Ellen Svinhufvud ', text)
    text = text.replace('Öhqvist', 'Öhquist')

    # Add a space after commas where it's missing
    text = re.sub(r'(?<=\S),(?=\S)', ', ', text)

    # Pretty sure this is the guy
    text = text.replace('Tuomas Noponen', 'korpraali Tuomas Noponen')

    text = text.replace('Sotamies Pihlajamaa', 'sotamies Väinö Pihlajamaa')

    # Events only
    # text = text.replace('Ryti', '## Risto Ryti')
    # text = text.replace('Tanner', '## Väinö Tanner')
    # text = re.sub(r'(?<!M\.\W)Kallio(lle|n)?\b', '## Kyösti Kallio', text)
    # text = text.replace('Molotov', '## V. Molotov')  # not for photos
    # text = re.sub(r'(?<!Josif\W)Stalin(ille|in|iin)?\b', 'Josif Stalin', text)

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

name_re_exclude = r"((\b[a-zäåö]+|\W+)$)|#"
name_re_exclude_compiled = re.compile(name_re_exclude)


def pruner(candidate):
    """
    >>> pruner('Kenraali Engelbrecht')
    'Kenraali Engelbrecht'
    >>> pruner('Kenraali Engelbrecht retkellä')
    >>> pruner('höpö höpö Engelbrecht')
    'höpö höpö Engelbrecht'
    >>> pruner('Höpö höpö Engelbrecht')
    'Höpö höpö Engelbrecht'
    >>> pruner('höpö höpö Engelbrecht:')
    >>> pruner('höpö höpö Engelbrecht ')
    >>> pruner('kapteeni kissa')
    >>> pruner('höpö')
    >>> pruner('Engelbrecht')
    >>> pruner('#retkellä Engelbrecht')
    """
    if name_re_compiled.fullmatch(candidate):
        if not name_re_exclude_compiled.search(candidate):
            return candidate
    return None


def set_dataset(args):
    if str(args.tprop) == 'http://purl.org/dc/terms/subject':
        logger.info('Handling as photos')
        Validator.dataset = 'photo'
    else:
        logger.info('Handling as events')
        Validator.dataset = 'event'


if __name__ == '__main__':
    if sys.argv[1] == 'test':
        import doctest
        doctest.testmod()
        exit()

    process_stage(sys.argv, ignore=ignore, validator=Validator, preprocessor=preprocessor,
            pruner=pruner, set_dataset=set_dataset)
