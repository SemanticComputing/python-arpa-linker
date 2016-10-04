from collections import defaultdict
from datetime import date, datetime, timedelta
from arpa_linker.link_helper import process_stage
from rdflib import URIRef
# from rdflib.namespace import SKOS
import logging
import re
import sys
import os

logger = logging.getLogger('arpa_linker.arpa')

MANNERHEIM_RITARIT = '<http://ldf.fi/warsa/sources/source5>'

SOURCES = {
    '<http://ldf.fi/warsa/sources/source1>': 0,
    '<http://ldf.fi/warsa/sources/source10>': 1,  # Wikipedia
    '<http://ldf.fi/warsa/sources/source11>': 0,
    '<http://ldf.fi/warsa/sources/source12>': 0,
    '<http://ldf.fi/warsa/sources/source13>': 0,
    '<http://ldf.fi/warsa/sources/source2>': 0,
    '<http://ldf.fi/warsa/sources/source3>': 0,
    '<http://ldf.fi/warsa/sources/source4>': 0,
    MANNERHEIM_RITARIT: 1,
    '<http://ldf.fi/warsa/sources/source6>': 0,
    '<http://ldf.fi/warsa/sources/source7>': 0,
    '<http://ldf.fi/warsa/sources/source8>': 0,
    '<http://ldf.fi/warsa/sources/source9>': 0
}

RANK_CLASS_SCORES = {
    'Kenraalikunta': 1,
    'Esiupseeri': 1,
    'Komppaniaupseeri': 0,
    'Upseeri': 0,
    'kirkollinen henkilöstö': 1,
    'Aliupseeri': -7,
    'Miehistö': -7,
    'lottahenkilöstö': 0,
    'virkahenkilöstö': 0,
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

ALL_RANKS = {
    'alisotilasohjaaja': 0,
    'alisotilasvirkamies': 0,
    'aliupseerioppilas': 0,
    'alokas': 0,
    'apusisar': 0,
    'armeijakenraali': 0,
    'asemestari': 0,
    'cadet': 0,
    'erikoismestari': 0,
    'gewehrführer': 0,
    'hauptzugführer': 0,
    'hilfsgewehrführer': 0,
    'hilfsgruppenführer': 0,
    'kadetti': 0,
    'kadettialikersantti': 0,
    'kadettikersantti': 0,
    'kadettipursimies': 0,
    'kadettivääpeli': 0,
    'kadettiylikersantti': 0,
    'kansiupseeri': 0,
    'kenraalieversti': 0,
    'kenttäpostimestari': 0,
    'lentomekaanikko': 0,
    'linnoitustyönjohtaja': 0,
    'luotsi': 0,
    'lähetti': 0,
    'lääkintävirkamies': 0,
    'mekaanikko': 0,
    'merivartija': 0,
    'oberzugführer': 0,
    'offizierstellvertreter': 0,
    'oppilas': 0,
    'paikallispäällikkö': 0,
    'rottenführer': 0,
    'sairaanhoitaja': 0,
    'sairaanhoitajaoppilas': 0,
    'siviili': 0,
    'soitto-oppilas': 0,
    'sotainvalidi': 0,
    'sotakirjeenvaihtaja': 0,
    'sotaylituomari': 0,
    'sotilasalivirkamies': 0,
    'sotilasdiakoni': 0,
    'sotilaskotisisar': 0,
    'sotilaspoika': 0,
    'sotilaspoliisi': 0,
    'sotilasvirkamies': 0,
    'suojeluskunta-alokas': 0,
    'suojeluskuntaupseeri': 0,
    'toisen luokan nostomies': 0,
    'tuntematon': 0,
    'työvelvollinen': 0,
    'vapaaehtoinen': 0,
    'varusmiesdiakoni': 0,
    'varusmiespappi': 0,
    'vizefeldwebel': 0,
    'yleisesikuntaupseeri': 0,
    'ylihoitaja': 0,
    'zugführer': 0,
    'autosotamies': 1,
    'erikoisjääkäri': 1,
    'erikoisrajajääkäri': 1,
    'ilmasuojelumies': 1,
    'ilmasuojelusotamies': 1,
    'ilmavalvontalotta': 1,
    'jääkäri': 1,
    'kaartinjääkäri': 1,
    'kanslialotta': 1,
    'kenttälotta': 1,
    'lentosotamies': 1,
    'lotta': 1,
    'lääkintälotta': 1,
    'lääkintäsotamies': 1,
    'matruusi': 1,
    'muonituslotta': 1,
    'panssarijääkäri': 1,
    'panssarimies': 1,
    'pioneeri': 1,
    'rajajääkäri': 1,
    'rakuuna': 1,
    'rannikkojääkäri': 1,
    'ratsujääkäri': 1,
    'ratsumies': 1,
    'schütze': 1,
    'sotamies': 1,
    'suojelumies': 1,
    'suojeluskuntasotamies': 1,
    'tykkimies': 1,
    'valonheitinlotta': 1,
    'viestimies': 1,
    'gefreiter': 2,
    'jefreitteri': 2,
    'korpraali': 2,
    'lääkintäkorpraali': 2,
    'rajakorpraali': 2,
    'sturmmann': 2,
    'suojeluskuntakorpraali': 2,
    'ylimatruusi': 2,
    'alikersantti': 3,
    'lääkintäalikersantti': 3,
    'unterscharführer': 3,
    'upseerioppilas': 3,
    'kersantti': 4,
    'lääkintäkersantti': 4,
    'upseerikokelas': 4,
    'varavahtimestari': 5,
    'varavääpeli': 5,
    'ylikersantti': 5,
    'lääkintävääpeli': 6,
    'pursimies': 6,
    'rajavääpeli': 6,
    'ratsuvääpeli': 6,
    'reservin vääpeli': 6,
    'suojeluskuntavääpeli': 6,
    'vahtimestari': 6,
    'vääpeli': 6,
    'ylipursimies': 7,
    'ylivääpeli': 7,
    'lentomestari': 8,
    'sotilasmestari': 8,
    'tykkimestari': 8,
    'aliluutnantti': 9,
    'kornetti': 9,
    'musiikkivänrikki': 9,
    'reservin aliluutnantti': 9,
    'reservin kornetti': 9,
    'reservin vänrikki': 9,
    'untersturmführer': 9,
    'vänrikki': 9,
    'eläinlääkintäluutnantti': 10,
    'insinööriluutnantti': 10,
    'luutnantti': 10,
    'lääkintäluutnantti': 10,
    'musiikkiluutnantti': 10,
    'obersturmführer': 10,
    'reservin luutnantti': 10,
    'yliluutnantti': 11,
    'eläinlääkintäkapteeni': 12,
    'hauptmann': 12,
    'insinöörikapteeni': 12,
    'insinöörikapteeniluutnantti': 12,
    'kapteeni': 12,
    'kapteeniluutnantti': 12,
    'lääkintäkapteeni': 12,
    'musiikkikapteeni': 12,
    'ratsumestari': 12,
    'reservin kapteeni': 12,
    'sotilaspastori': 12,
    'eläinlääkintämajuri': 13,
    'insinöörimajuri': 13,
    'komentajakapteeni': 13,
    'lääkintämajuri': 13,
    'majuri': 13,
    'eläinlääkintäeverstiluutnantti': 14,
    'everstiluutnantti': 14,
    'insinöörieverstiluutnantti': 14,
    'kenttärovasti': 14,
    # 'komentaja': 14,
    'lääkintäeverstiluutnantti': 14,
    'eläinlääkintäeversti': 15,
    'eversti': 15,
    'kommodori': 15,
    'lääkintäeversti': 15,
    'kenttäpiispa': 16,
    'lippueamiraali': 16,
    'prikaatikenraali': 16,
    'prikaatinkomentaja': 16,
    'divisioonankomentaja': 17,
    'eläinlääkintäkenraalimajuri': 17,
    'insinöörikenraalimajuri': 17,
    'kenraalimajuri': 17,
    'kontra-amiraali': 17,
    'lääkintäkenraalimajuri': 17,
    'armeijakunnankomentaja': 18,
    'gruppenführer': 18,
    'kenraaliluutnantti': 18,
    'lääkintäkenraaliluutnantti': 18,
    'vara-amiraali': 18,
    '2. luokan armeijankomentaja': 19,
    'amiraali': 19,
    'jalkaväenkenraali': 19,
    'jääkärikenraali': 19,
    'kenraali': 19,
    'lääkintäamiraali': 19,
    'ratsuväenkenraali': 19,
    'tykistönkenraali': 19,
    '1. luokan armeijankomentaja': 20,
    'sotamarsalkka': 20,
    'neuvostoliiton marsalkka': 21,
    'suomen marsalkka': 21,
}

all_rank_classes_regex = re.compile(r'\b{}\b'.format(r'\b|\b'.join(RANK_CLASS_SCORES.keys())), re.I)
all_ranks_regex = re.compile(r'\b{}\b'.format(r'\b|\b'.join(ALL_RANKS.keys())), re.I)

knight_re = re.compile(r'ritar[ie]', re.I)


def parse_date(d):
    str_date = '-'.join(d.replace('"', '').split('^')[0].split('-')[0:3])
    return datetime.strptime(str_date, "%Y-%m-%d").date()


class ValidationContext:
    dataset = ''

    def __init__(self, graph, results, s):
        self.s = s
        self.graph = graph
        self.original_text = graph.value(s, URIRef('http://www.w3.org/2004/02/skos/core#prefLabel'))
        self.s_date = self.get_s_start_date(s)
        self.units = {'<{}>'.format(u) for u in graph.objects(s, URIRef('http://ldf.fi/warsa/photographs/unit')) if u}
        self.results = results
        self.ranked_matches = self.get_ranked_matches(results)
        self.match_scores = self.get_match_scores(results)

    def get_s_start_date(self, s):
        def get_event_date():
            date_uri = self.graph.value(s, URIRef('http://www.cidoc-crm.org/cidoc-crm/P4_has_time-span'))
            try:
                d = str(date_uri).split('time_')[1]
                return parse_date(d)
            except (ValueError, IndexError):
                logger.warning("Invalid time-span URI: {}".format(date_uri))
                return None

        def get_photo_date():
            date_value = self.graph.value(s, URIRef('http://purl.org/dc/terms/created'))
            d = str(date_value)
            try:
                return parse_date(d)
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
        rd = self.get_ranked_matches(results)
        scores = {}
        for k, v in rd.items():
            for uri in v['uris']:
                scores[uri] = v['score']

        return scores


class Validator:
    def __init__(self, graph, *args, **kwargs):
        self.graph = graph

    def get_death_date(self, person):
        """
        >>> v = Validator(None)
        >>> ranks = {'death_date': ['"1940-02-01"^^xsd:date']}
        >>> person = {'properties': ranks}
        >>> v.get_death_date(person)
        datetime.date(1940, 2, 1)
        """
        try:
            death_date = parse_date(person['properties']['death_date'][0])
        except (KeyError, ValueError):
            logger.info("No death date found for {}".format(person.get('id')))
            return None
        return death_date

    def get_current_rank(self, person, event_date):
        """
        Get the latest rank the person had attained by the date given.
        """
        props = person['properties']
        res = None
        latest_date = None
        for i, rank in enumerate(props.get('rank')):
            try:
                promotion_date = parse_date(props.get('promotion_date')[i])
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
        props = person['properties']
        res = set()
        latest_date = None
        potential_lowest_ranks = set()
        for i, rank in enumerate(props.get(rank_type)):

            rank = rank.replace('"', '')
            if rank == 'Yleisesikuntaupseeri':
                # Yleisesikuntaupseeri is not an actual rank.
                continue

            try:
                promotion_date = parse_date(props.get('promotion_date')[i])
                latest_promotion_date = parse_date(props.get('latest_promotion_date')[i])
            except:
                # Unknown date
                continue

            delta = timedelta(date_range)

            if promotion_date > event_date + delta:
                # promotion_date > upper boundary
                continue

            if latest_promotion_date > event_date - delta:
                # lower boundary < promotion_date < upper boundary
                res.add(rank)
                continue

            if not latest_date or promotion_date > latest_date:

                potential_lowest_ranks.add((rank, latest_promotion_date))

                latest_date = promotion_date
                temp_set = set()
                for r in potential_lowest_ranks:
                    if not r[1] < latest_date:
                        temp_set.add(r)
                potential_lowest_ranks = temp_set
                continue

            if latest_promotion_date >= latest_date:
                potential_lowest_ranks.add((rank, latest_promotion_date))

            # event_date < latest_date

        for r in potential_lowest_ranks:
            res.add(r[0])

        return res

    def get_rank_level(self, props, i):
        try:
            return int(re.sub(r'"(\d+)".*', r'\1', props.get('rank_level')[i]))
        except Exception:
            return 0

    def get_lowest_rank_level(self, person, date, rank_type):
        props = person['properties']
        ranks = self.get_fuzzy_current_ranks(person, date, 'rank', 0)
        ranks = {r.lower() for r in ranks}
        logger.debug('RANKS: {}'.format(ranks))
        lowest_rank = None
        for rank in ranks:
            if not lowest_rank or ALL_RANKS.get(rank, 0) > ALL_RANKS.get(lowest_rank, 0):
                lowest_rank = rank
        if lowest_rank:
            return ALL_RANKS.get(lowest_rank, 0)
        for rank in props.get('ranks', []):
            if not lowest_rank or ALL_RANKS.get(rank, 0) < ALL_RANKS.get(lowest_rank, 0):
                lowest_rank = rank
        return ALL_RANKS.get(lowest_rank, 0)

    def filter_promotions_outside_wars(self, person, rank_type):
        props = person['properties']
        res = set()
        lowest_level = self.get_lowest_rank_level(person, date(1939, 1, 1), rank_type)
        logger.debug('LOWEST LEVEL: {}'.format(lowest_level))
        for i, rank in enumerate([r.lower() for r in props.get(rank_type, [])]):
            rank = rank.replace('"', '')
            if rank == 'Yleisesikuntaupseeri':
                # Yleisesikuntaupseeri is not an actual rank.
                continue
            if self.get_rank_level(props, i) < lowest_level:
                logger.debug('TOO LOW: {} ({})'.format(rank, self.get_rank_level(props, i)))
                continue
            try:
                promotion_date = parse_date(props.get('promotion_date')[i])
            except:
                # Unknown date
                res.add(rank)
                continue
            if promotion_date < date(1946, 1, 1):
                res.add(rank)

        logger.debug('PROMS: {}'.format(res))
        return res

    def get_ranks_with_unknown_date(self, person, rank_type):
        res = []
        props = person['properties']
        for i, rank in enumerate(props.get(rank_type)):
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
        """

        # The match might be misleading: e.g. "Aarne Snellman"
        # in "sotamies Antero Aarne Snellman" is not preceded by a rank, yet
        # the rank is obviously inconsistent if "Aarne Snellman" is e.g. "eversti".
        # Thus look one word further if the preceding word is name-like.
        text_rank_re = r'\b(\w+)\s+(?:(?:\w+\s+)|(?:[A-ZÄÅÖÜ]\.\s+))?'
        text_ranks = []

        for match in set(person['matches']):
            if all_ranks_regex.findall(match) or all_rank_classes_regex.findall(match):
                # Rank already in match
                return True
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

    def _check_rank(self, ranks, matches):
        if not ranks:
            return False
        current_rank = r'({})'.format(r'\b|\b'.join(ranks))
        cur_rank_re = r'\b{}\b'.format(current_rank.lower())
        return any([m for m in matches if re.match(cur_rank_re, m, re.I)])

    def get_rank_score(self, person, s_date, text):
        props = person['properties']

        rank_set = {r.replace('"', '').lower() for r in props.get('rank', [])}
        if not (len(rank_set) == 1 and 'na' in rank_set) and not self.has_consistent_rank(
                person, text):
            logger.info(
                'Reducing score because an inconsistent rank was found in context: {} ({}) [{}]'.format(
                    person.get('label'),
                    person.get('id'),
                    ', '.join(set(props.get('rank', [])))))
            return -10

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

        if s_date:
            # Event has a date
            ranks = self.get_fuzzy_current_ranks(person, s_date, rank_type)
            if self._check_rank(ranks, matches):
                return score + 8
            else:
                # Current rank not found, match ranks with unknown promotion dates
                ranks = self.get_ranks_with_unknown_date(person, rank_type)
                if self._check_rank(ranks, matches):
                    return score + 7
        else:
            # Unknown event date, match any rank
            ranks = self.filter_promotions_outside_wars(person, rank_type) or ['NA']
            if self._check_rank(ranks, matches):
                return score + 7

        # This person did not have the matched rank at this time
        logger.info('Reducing score because of inconsistent rank: {} ({}) [{}]'.format(
            person.get('label'),
            person.get('id'),
            ', '.join(set(props.get('rank', [])))))
        score -= 15

        return score

    def get_date_score(self, person, s_date, s, e_label):
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
                    "DEAD PERSON: {p_label} ({p_uri}) died ({death_date}) more than a month "
                    "({diff} days) before start ({s_date}) of event {e_label} ({e_uri})"
                    .format(p_label=person.get('label'), p_uri=person.get('id'), diff=diff.days,
                        death_date=death_date, s_date=s_date, e_uri=s, e_label=e_label))
                score -= 30
            elif diff.days >= 0:
                logger.info(
                    "RECENTLY DEAD PERSON: {p_label} ({p_uri}) died {diff} days ({death_date}) before start "
                    "({s_date}) of event {e_label} ({e_uri})".format(p_label=person.get('label'), p_uri=person.get('id'),
                        diff=diff.days, death_date=death_date, s_date=s_date, e_uri=s, e_label=e_label))
        return score

    def get_name_score(self, person):
        first_names = person['properties'].get('first_names', [None])[0]
        if not first_names:
            return 0

        score = 0

        matches = set(person.get('matches'))
        match_str = ' '.join(matches)

        first_names = first_names.replace('"', '').strip()

        if '.' in match_str:
            longest_match_len = 0
            initials = re.findall(r'\b\w', first_names)
            for m in matches:
                match_initials = re.findall(r'[A-ZÄÅÖÜ](?=\.)', m)
                m_len = len(os.path.commonprefix([initials, match_initials]))
                if m_len > longest_match_len:
                    longest_match_len = m_len
            score += max([(longest_match_len - 1) * 5, 0])

        very_first_name = re.sub(r'^(\S+)\b.*$', r'\\b\1\\b', first_names)
        first_names = r'(\b{}\b)'.format(re.sub(r'\s+', r'\\b|\\b', first_names))
        if re.search(first_names, match_str):
            score += 3
            if re.search(very_first_name, match_str):
                score += 2

        return score

    def get_source_score(self, person):
        sources = {r.replace('"', '') for r in person['properties'].get('source', [])}
        if not sources:
            return 0

        score = max([SOURCES.get(s, 0) for s in sources])
        # Give one extra point if the person has multiple sources
        score += 1 if len(sources) > 1 else 0
        return score

    def is_knight(self, person):
        sources = person.get('properties', {}).get('source', [])
        if MANNERHEIM_RITARIT in sources:
            return True
        return False

    def get_knight_score(self, person, text, results, ranked_matches):
        """
        A person that is a knight of the Mannerheim cross get a higher score
        if the context mentions knighthood. Non-knights' scores are reduced
        in this case.
        """
        if not knight_re.search(text):
            # No mention of knighthood in context.
            return 0

        if self.is_knight(person):
            logger.debug('Knight')
            return 20

        logger.debug('Not a knight')

        result_dict = {x['id']: x for x in results}

        for match, val in ranked_matches.items():
            uris = val['uris']
            if person['id'] in uris:
                for uri in uris:
                    other = result_dict[uri]
                    if self.is_knight(other):
                        logger.info(('Reducing score for {} ({}): is not a knight, but '
                                '{} ({}) is.').format(
                                    person.get('label'), person['id'],
                                    other.get('label'), other['id']))
                        return -20
        return 0

    def get_unit_score(self, person, units):
        """
        Score person higher if the photo has the same unit as the person.
        """
        person_units = set(person['properties'].get('unit', []))
        logger.debug('PERSON UNITS: {}'.format(person_units))
        logger.debug('PHOTO UNITS: {}'.format(units))
        if units.intersection(person_units):
            return 15
        return 0

    def get_score(self, person, text, ctx):
        person_id = person.get('id')
        logger.debug('Scoring {} ({}) [{}]'.format(person.get('label'), person_id,
            ', '.join(set(person.get('properties', {}).get('rank', [])))))
        if person_id == 'http://ldf.fi/warsa/actors/person_1':
            # "Suomen marsalkka" is problematic as a rank so let's just always
            # score Mannerheim highly
            logger.debug('Mannerheim score')
            return 50

        rms = ctx.match_scores.get(person.get('id'), 0)
        logger.debug('Match score: {}'.format(rms))

        ds = self.get_date_score(person, ctx.s_date, ctx.s, ctx.original_text)
        logger.debug('Date score: {}'.format(ds))

        rs = self.get_rank_score(person, ctx.s_date, text)
        logger.debug('Rank score: {}'.format(rs))

        ns = self.get_name_score(person)
        logger.debug('Name score: {}'.format(ns))

        ss = self.get_source_score(person)
        logger.debug('Source score: {}'.format(ss))

        ks = self.get_knight_score(person, ctx.original_text, ctx.results, ctx.ranked_matches)
        logger.debug('Knight score: {}'.format(ks))

        us = self.get_unit_score(person, ctx.units)
        logger.debug('Unit score: {}'.format(us))

        return rms + ds + rs + ns + ss + ks + us

    def choose_best(self, res):
        if res and len(res) > 1:
            match_dict = {}
            logger.info("Choosing the best score")
            for person in res:
                for match in set(person['matches']):
                    # {'kapteeni Kalpamaa': {'score': 1, 'persons': [persons]}}
                    best_match_score = match_dict.get(match, {}).get('score', 0)
                    if person['score'] > best_match_score:
                        if match_dict.get(match):
                            for p in match_dict[match]['persons']:
                                logger.warning("LOW SCORE: {} score {}".format(p['id'], p['score']))
                        match_dict[match] = {'score': person['score'], 'persons': [person]}
                    elif person['score'] == best_match_score:
                        match_dict[match]['persons'].append(person)
                    else:
                        logger.warning("LOW SCORE: {} score {}".format(person['id'], person['score']))
            best = []
            ids = set()
            for m, val in match_dict.items():
                for p in val['persons']:
                    if p['id'] not in ids:
                        ids.add(p['id'])
                        best.append(p)
                logger.info("BEST: {} score {} ({})".format([p['id'] for p in val['persons']],
                    val['score'], m))
            logger.info("{}/{} chosen".format(len(best), len(res)))
            return best
        return res

    def validate(self, results, text, s):
        if not results:
            return results
        res = []
        context = ValidationContext(self.graph, results, s)
        logger.info('ORIG: {}'.format(context.original_text))
        for person in results:
            score = self.get_score(person, text, context)

            log_msg = "{} ({}) scored {} [{}]".format(
                person.get('label'),
                person.get('id'),
                score,
                ', '.join(set(person.get('properties', {}).get('rank', []))))

            if score > 0:
                log_msg = "PASS: " + log_msg
                person['score'] = score
                res.append(person)
            else:
                log_msg = "FAIL: " + log_msg

            logger.info(log_msg)

        logger.info("{}/{} passed validation".format(len(res), len(results)))
        return self.choose_best(res)


_name_part = r'[A-ZÄÖÅ]' + r'(?:(?:\.\s*|\w+\s+)?[A-ZÄÖÅ])?' * 2
list_regex = r'\b(?::)?\s*' + (r'(?:(' + _name_part + r'\w+,)(?:\s*))?') * 10 + \
    r'(?:(' + _name_part + r'\w+)?(?:\s+ja\s+)?([A-ZÄÖÅ](?:(?:\w|\.\s*|\w+\s+)?[A-ZÄÖÅ])?\w+)?)?'

_g_re = r'\b[Kk]enraali(?:t)?' + list_regex
g_regex = re.compile(_g_re)

_gl_re = r'\b[Kk]enraaliluutnantit' + list_regex
gl_regex = re.compile(_gl_re)

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

_mc_re = r'\b[Mm]usiikkiapteenit' + list_regex
mc_regex = re.compile(_mc_re)

_l_re = r'\b[Ll]uutnant(?:ti|it)' + list_regex
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


def replace_gl_list(text):
    return add_titles(gl_regex, 'kenraaliluutnantti', text)


def replace_major_general_list(text):
    """
    >>> replace_major_general_list("Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, majurit: Müller, Pennanen, Kalpamaa, Varko.")
    'Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, majurit: Müller, Pennanen, Kalpamaa, Varko.'
    """
    return add_titles(mg_regex, 'kenraalimajuri', text)


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
    >>> replace_major_list("Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström, majurit: Müller, Pennanen, Kalpamaa, Varko.")
    'Kuva ruokailusta. Ruokailussa läsnä: Kenraalimajuri Martola, ministerit: Koivisto, Salovaara, Horelli, Arola, hal.neuv. Honka, everstiluutnantit: Varis, Ehnrooth, Juva, Heimolainen, Björnström,  \
majuri Müller, majuri Pennanen, majuri Kalpamaa, majuri Varko.'
    >>> replace_major_list("Rautaristin saajat: eversti A. Puroma, majurit A.G. Airimo ja V. Lehvä")
    'Rautaristin saajat: eversti A. Puroma,  majuri A.G. Airimo majuri V. Lehvä'
    """
    return add_titles(ma_regex, 'majuri', text)


def replace_captain_list(text):
    return add_titles(c_regex, 'kapteeni', text)


def replace_music_captain_list(text):
    return add_titles(mc_regex, 'musiikkikapteeni', text)


def replace_lieutenant_list(text):
    """
    >>> replace_lieutenant_list("Rautaristin saajat: Eversti A. Puroma, majurit A.K Airimo ja V. Lehvä, luutnantit K. Sarva ja U. Jalkanen, vänrikit T. Laakso, R. Kanto, N. Vuolle ja Y. Nuortio, kersantit T. Aspegren ja H. Kalliaisenaho, alikersantit L. Nousiainen, V. Launonen ja Salmi sekä korpraali R. Keihta.")
    'Rautaristin saajat: Eversti A. Puroma, majurit A.K Airimo ja V. Lehvä,  luutnantti K. Sarva luutnantti U. Jalkanen, vänrikit T. Laakso, R. Kanto, N. Vuolle ja Y. Nuortio, kersantit T. Aspegren ja H. Kalliaisenaho, alikersantit L. Nousiainen, V. Launonen ja Salmi sekä korpraali R. Keihta.'
    >>> replace_lieutenant_list("Aamutee teltassa. Luutnantti Kauppinen, Wind, kapteeni Karhunen.")
    'Aamutee teltassa.  luutnantti Kauppinen, luutnantti Wind,kapteeni Karhunen.'
    >>> replace_lieutenant_list("luutnantti Pulliainen, Voutilainen, kapteeni Ruoho,")
    ' luutnantti Pulliainen, luutnantti Voutilainen,kapteeni Ruoho,'
    """
    return add_titles(l_regex, 'luutnantti', text)


def replace_v_list(text):
    return add_titles(v_regex, 'vänrikki', text)


def replace_k_list(text):
    return add_titles(k_regex, 'kersantti', text)


def replace_ak_list(text):
    return add_titles(ak_regex, 'alikersantti', text)


def replace_sv_list(text):
    return add_titles(sv_regex, 'sotilasvirkamies', text)


to_be_lowercased = (
    "Eversti",
    "Luutnantti",
    "Kenraali",
    "Kapteeni",
    "Kersantti",
    "Vänrikki"
)


def process_lists(text):
    text = replace_general_list(text)
    text = replace_minister_list(text)
    text = replace_e_list(text)
    text = replace_el_list(text)
    text = replace_major_list(text)
    text = replace_major_general_list(text)
    text = replace_gl_list(text)
    text = replace_captain_list(text)
    text = replace_sv_list(text)
    text = replace_v_list(text)
    text = replace_k_list(text)
    text = replace_ak_list(text)
    text = replace_lieutenant_list(text)

    return text


def handle_specific_people(text):
    # Mannerheim
    text = text.replace('Fältmarsalk', 'sotamarsalkka')
    text = re.sub(r'(?<![Ss]otamarsalkka )(?<![Mm]arsalkka )Mannerheim(?!-)(in|ille|ia)?\b', '# kenraalikunta Mannerheim #', text)
    text = re.sub(r'([Ss]ota)?[Mm]arsalk(ka|an|alle|en)?\b(?! Mannerheim)', '# kenraalikunta Mannerheim #', text)
    text = re.sub(r'[Yy]lipäällik(kö|ön|ölle|köä|kön)\b', '# kenraalikunta Mannerheim #', text)
    text = re.sub(r'Marski(n|a|lle)?\b', '# kenraalikunta Mannerheim #', text)

    text = re.sub(r'Blick(\b|ille|in)', 'Aarne Leopold Blick', text)
    text = re.sub(r'^Nenonen\b', 'kenraalikunta Nenonen', text)
    # Some young guy in one photo
    text = text.replace('majuri V.Tuompo', '#')
    text = text.replace('Tuompo, Viljo Einar', 'kenraalikunta Tuompo')
    text = text.replace('Erfurth & Tuompo', 'kenraalikunta Erfurth ja kenraalikunta Tuompo')
    text = text.replace('Wuolijoki', '# Hella Wuolijoki')
    text = text.replace('Presidentti ja rouva R. Ryti', 'Risto Ryti # Gerda Ryti')
    text = re.sub('[Pp]residentti Ryti', 'Risto Ryti', text)
    text = re.sub(r'[Mm]inisteri Koivisto', 'Juho Koivisto', text)
    text = re.sub(r'[Pp]residentti Kallio', 'Kyösti Kallio', text)
    text = re.sub(r'[Rr](ou)?va(\.)? Kallio', 'Kaisa Kallio', text)
    # John Rosenbröijer is also a possibility, but photos were checked manually
    text = re.sub(r'[RB]osenbröijer(in|ille|ia)?\b', '# Edvin Rosenbröijer #', text)
    # Problem with baseforming
    text = re.sub(r'Turo Kart(on|olle|toa)\b', 'Turo Kartto ', text)

    text = re.sub(r'Onni Palomä(ki|en)', 'Olli Palomäki', text)

    text = re.sub(r'[Ee]versti Somersalo', 'everstiluutnantti Somersalo', text)

    text = text.replace('(!<!Adolf )Hitler', 'Adolf Hitler')

    text = re.sub(r'(Saharan|Marokon) kauhu', '# kapteeni Juutilainen #', text)
    text = re.sub(r'luutnantti\s+Juutilainen', '# kapteeni Juutilainen #', text)

    text = re.sub(r'(?<!patterin päällikkö )[Kk]apteeni (Joppe )?Karhu(nen|sen)', '# kapteeni Jorma Karhunen #', text)
    text = re.sub(r'(?<!3\. )(?<!III )(luutnantti|[Vv]änrikki|Lauri Wilhelm) Nissi(nen|sen)\b', '# vänrikki Lauri Nissinen #', text)
    text = text.replace('Cajander', 'Aimo Kaarlo Cajander')
    # Needs tweaking for photos
    # text = text.replace('E. Mäkinen', '## kenraalimajuri Mäkinen')
    text = re.sub(r'(?<!Aimo )(?<!Aukusti )(?<!Y\.)Tanner', '# Väinö Tanner #', text)
    # text = text.replace('Niukkanen', '## Juho Niukkanen')
    # text = text.replace('Söderhjelm', '## Johan Otto Söderhjelm')
    text = re.sub(r'(?<![Ee]verstiluutnantti )Paasikivi', '# Juho Kusti Paasikivi', text)
    text = re.sub(r'([Pp]uolustus)?[Mm]inisteri Walden', 'kenraalikunta Walden', text)
    text = re.sub(r'[vV]ääpeli( Oiva)? Tuomi(nen|selle|sen)', '# lentomestari Oiva Tuominen', text)
    text = re.sub(r'Ukko[ -]Pekka(\W+Svinhufvud)?', 'Pehr Evind Svinhufvud', text)
    text = re.sub(r'[Pp]residentti Svinhufvud', 'Pehr Evind Svinhufvud', text)
    text = re.sub(r'[Pp]residentti\s+ja\s+rouva\s+Svinhufvud', 'Pehr Evind Svinhufvud ja Ellen Svinhufvud ', text)
    text = re.sub(r'[Rr]ouva\s+Svinhufvud', ' Ellen Svinhufvud ', text)
    text = text.replace('Öhqvist', 'Öhquist')
    text = text.replace('Jörgen Hageman', 'Jörgen Hagemann')
    # Only relevant in events
    text = re.sub('[Ee]verstiluutnantti M. Nurmi', 'eversti Martti Nurmi', text)
    text = re.sub('[VW]inell(in|ille|illa|ia|ista)', 'Winell', text)
    text = text.replace('Heinrichsin', 'Heinrichs')
    text = text.replace('Laiva Josif Stalin', '#')
    text = re.sub(r'(Aleksandra\W)?Kollontai(\b|lle|n|hin)', 'Alexandra Kollontay', text)

    # Pretty sure this is the guy
    text = text.replace('Tuomas Noponen', 'korpraali Tuomas Noponen')

    text = text.replace('Sotamies Pihlajamaa', 'sotamies Väinö Pihlajamaa')

    return text


def normalize_ranks(text):
    # E.g. "TK-mies"
    text = re.sub(r'[Tt][Kk]-[a-zäåö]+', 'sotilasvirkamies', text)

    # Sotilasvirkamies
    text = re.sub(r'\bsot(a|ilas)virkailija\b', 'sotilasvirkamies', text, flags=re.I)
    text = re.sub(r'\b[Ss]ot\.\s*[Vv]irk\.', 'sotilasvirkamies ', text)
    text = re.sub(r'\b[Tk][Kk]-([A-ZÄÖÅ])', r'sotilasvirkamies \1', text)

    text = re.sub(r'\b[Kk]enr\.\s*([a-z])', r'kenraali§\1', text)
    text = re.sub(r'\b[Ee]v\.\s*([a-z])', r'eversti§\1', text)
    text = re.sub(r'\b[Ee]v\.', 'eversti ', text)
    text = re.sub(r'\b[Ll]uu(tn|nt)\.', 'luutnantti ', text)
    text = re.sub(r'\b[Mm]aj\.', 'majuri ', text)
    text = re.sub(r'\b[Kk]apt\.\s*([a-z])', r'kapteeni§\1', text)
    text = re.sub(r'\b[Kk]apt\.', 'kapteeni ', text)

    # Swedish
    text = re.sub(r'\b[Öö]v(\.l|erstelöjtn)\.', 'everstiluutnantti ', text)
    text = re.sub(r'\b[Öö]v(\.|erste)\s*([a-z])', r'eversti§\1', text)
    text = re.sub(r'\b[Öö]v(\.|erste)', 'eversti ', text)
    text = re.sub(r'\b[Gg]en(\.|eral)\s*([a-z])', r'kenraali§\1', text)
    text = re.sub(r'\b[Gg]en(\.|eral)', 'kenraali ', text)
    text = re.sub(r'[Mm]ajors?.\?', 'majuri ', text)
    text = re.sub(r'\b[Ll]öjt(n?\.|nant)', 'luutnantti ', text)
    text = re.sub(r'\b[Ff]änr(\.|rik)', 'vänrikki ', text)

    text = text.replace('§', '')

    text = re.sub(r'\b[Tt]km\.', 'tykkimies ', text)
    text = re.sub(r'\b[Ss]tm(\.|\b)', 'sotamies ', text)
    text = re.sub(r'\b[Vv]änr\.', 'vänrikki ', text)
    text = re.sub(r'[Ll]entomies', 'lentomestari', text)
    text = re.sub(r'\b[Ee]verstil\.', 'everstiluutnantti', text)
    text = re.sub(r'[Tt]ykistökenraali', 'tykistönkenraali', text)

    return text


def preprocessor(text, *args):
    text = str(text).replace('"', '')
    logger.info('Preprocessing: {}'.format(text))
    if text.strip() == 'Illalla venäläisten viimeiset evakuointialukset mm. Josif Stalin lähtivät Hangosta.':
        return ''
    if text == "Lentomestari Oippa Tuominen.":
        text = "lentomestari Oiva Tuominen"
        logger.info('=> {}'.format(text))
        return text
    orig = text

    # v. -> von (exclude e.g. "6 v.")
    text = re.sub(r'(?<!\d[- ])(?<!\d)\bv\.\s*(?=[A-ZÄÖÅ])', 'von ', text)
    # E.g. von Bonin -> von_Bonin
    text = re.sub(r'\bvon\s+(?=[A-ZÄÅÖ])', 'von_', text)

    for r in to_be_lowercased:
        text = text.replace(r, r.lower())
    text = text.replace('hal.neuv.', '')

    # Has to be processed before the lists
    text = text.replace("luutnantti Herman ja Yrjö Nykäsen", "luutnantti Herman Nykänen ja luutnantti Yrjö Nykänen")

    text = normalize_ranks(text)

    text = process_lists(text)

    text = handle_specific_people(text)

    # Has to be done after the list processing
    text = re.sub(r'\bkenraali\b', 'kenraalikunta', text)

    text = re.sub(r'[Ll]ääkintäkenraali\b', 'kenraalikunta', text)

    # Add a space after commas where it's missing
    text = re.sub(r'(?<=\S),(?=\S)', ', ', text)

    # Events only
    if ValidationContext.dataset == 'event':
        text = text.replace('Ryti', '# Risto Ryti')
        text = text.replace('Tanner', '# Väinö Tanner')
        text = re.sub(r'(?<!M\.\W)Kallio(lle|n)?\b', '# Kyösti Kallio', text)
        text = text.replace('Molotov', '# V. Molotov')
        text = re.sub(r'(?<!Josif\W)Stalin(ille|ilta|in|iin)?\b', 'Josif Stalin', text)
        text = text.replace('eversti L. Haanterä', 'everstiluutnantti L. Haanterä')

    text = text.strip()
    text = re.sub(r'\s+', ' ', text)

    if text != orig:
        logger.info('Preprocessed to: {}'.format(text))

    return text


ignore = [
    'Eric Väinö Tanner',
    'Erik Gustav Martin Heinrichs'
]


ALLOWED_NAME_CHARS = 'a-zA-ZäÄöÖåÅÜüáàéèíìóòúùýỳ-'

name_re = (r'^((?:[a-zA-ZäÄåÅöÖ]\.[ ]*)|(?:[' + ALLOWED_NAME_CHARS +
    r']{3,}[ ]+))((?:-?[a-zA-ZäÄåÅöÖ]\.[ ]*)|(?:[' + ALLOWED_NAME_CHARS +
    r']{3,}[ ]+))?((?:[a-zA-ZäÄåÅöÖ]\.[ ]*)|(?:[' + ALLOWED_NAME_CHARS +
    r']{3,}[ ]+))*([A-ZÄÖÅÜ][_' + ALLOWED_NAME_CHARS + r']{2,})$')
name_re_compiled = re.compile(name_re)

name_re_exclude = r"((\b[a-zäåö]+|\W+)$)|#"
name_re_exclude_compiled = re.compile(name_re_exclude)


def pruner(candidate):
    if name_re_compiled.fullmatch(candidate):
        if not name_re_exclude_compiled.search(candidate):
            return candidate
    return None


def set_dataset(dataset_name):
    if dataset_name == 'event':
        print('Handling as events')
        ValidationContext.dataset = 'event'
    elif dataset_name == 'photo':
        print('Handling as photos')
        ValidationContext.dataset = 'photo'
    else:
        raise ValueError('Invalid dataset: {}'.format(dataset_name))


if __name__ == '__main__':
    if sys.argv[1] == 'test':
        import doctest
        doctest.testmod()
        exit()

    set_dataset(sys.argv[1])

    args = sys.argv[0:1] + sys.argv[2:]

    process_stage(args, ignore=ignore, validator_class=Validator,
            preprocessor=preprocessor, pruner=pruner, log_level='INFO')
