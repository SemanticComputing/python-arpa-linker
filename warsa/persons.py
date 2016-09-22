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
    'Komppaniaupseeri': 1,
    'Upseeri': 1,
    'kirkollinen henkilöstö': 1,
    'Aliupseeri': -5,
    'Miehistö': -10,
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

RANK_HIERARCHY = {
    'suomen marsalkka': 25,
    'sotamarsalkka': 24,
    'amiraali': 23,
    'kenraali': 23,
    'kenraaliluutnantti': 22,
    'vara-amiraali': 22,
    'kenraalimajuri': 21,
    'kontra-amiraali': 21,
    'lippueamiraali': 20,
    'prikaatikenraali': 20,
    'eversti': 19,
    'kommodori': 19,
    'everstiluutnantti': 18,
    'komentaja': 18,
    'komentajakapteeni': 17,
    'majuri': 17,
    'kapteeni': 16,
    'kapteeniluutnantti': 16,
    'yliluutnantti': 15,
    'luutnantti': 14,
    'aliluutnantti': 12,
    'vänrikki': 12,
    'sotilasmestari': 11,
    'ylipursimies': 8,
    'ylivääpeli': 8,
    'pursimies': 7,
    'vääpeli': 7,
    'ylikersantti': 6,
    'kersantti': 5,
    'neuvostoliiton marsalkka': 5,
    '1. luokan armeijankomentaja': 4,
    'alikersantti': 4,
    '2. luokan armeijankomentaja': 3,
    'armeijakunnankomentaja': 2,
    'hauptzugführer': 2,
    'divisioonankomentaja': 1,
    'korpraali': 1,
    'oberzugführer': 1,
    'ylimatruusi': 1
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
    # 'komentaja',
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

knight_re = re.compile(r'ritar[ie]', re.I)


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
            except (ValueError, IndexError):
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
                promotion_date = self.parse_date(props.get('promotion_date')[i])
                latest_promotion_date = self.parse_date(props.get('latest_promotion_date')[i])
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
                return score + 20
            else:
                # Current rank not found, match ranks with unknown promotion dates
                ranks = self.get_ranks_with_unknown_date(person, rank_type)
                if self._check_rank(ranks, matches):
                    return score + 11
        else:
            # Unknown event date, match any rank
            ranks = self.filter_promotions_after_wars(person, rank_type) or ['NA']
            if self._check_rank(ranks, matches):
                return score + 11

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
                    "DEAD PERSON: {p_label} ({p_uri}) died ({death_date}) more than a month"
                    "({diff} days) before start ({s_date}) of event {e_label} ({e_uri})"
                    .format(p_label=person.get('label'), p_uri=person.get('id'), diff=diff,
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
            score += 5
            if re.search(very_first_name, match_str):
                score += 5

        return score

    def get_source_score(self, person):
        sources = {r.replace('"', '') for r in person['properties'].get('source', [])}
        if not sources:
            return 0

        score = max([SOURCES.get(s, 0) for s in sources])
        score += len(sources) - 1
        return score

    def is_knight(self, person):
        sources = person.get('properties', {}).get('source', [])
        if MANNERHEIM_RITARIT in sources:
            return True
        return False

    def get_knight_score(self, person, text, results):
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

        ranked_matches = self.get_ranked_matches(results)
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
        if units.intersection(set(person.get('unit', []))):
            return 10
        return 0

    def get_score(self, person, s, s_date, text, original_text, results, units):
        person_id = person.get('id')
        logger.debug('Scoring {} ({}) [{}]'.format(person.get('label'), person_id,
            ', '.join(set(person.get('properties', {}).get('rank', [])))))
        if person_id == 'http://ldf.fi/warsa/actors/person_1':
            # "Suomen marsalkka" is problematic as a rank so let's just always
            # score Mannerheim highly
            logger.debug('Mannerheim score')
            return 50

        ranked_matches = self.get_match_scores(results)
        rms = ranked_matches.get(person.get('id'), 0)
        logger.debug('Match score: {}'.format(rms))

        ds = self.get_date_score(person, s_date, s, text)
        logger.debug('Date score: {}'.format(ds))

        rs = self.get_rank_score(person, s_date, text)
        logger.debug('Rank score: {}'.format(rs))

        ns = self.get_name_score(person)
        logger.debug('Name score: {}'.format(ns))

        ss = self.get_source_score(person)
        logger.debug('Source score: {}'.format(ss))

        ks = self.get_knight_score(person, original_text, results)
        logger.debug('Knight score: {}'.format(ks))

        return rms + ds + rs + ns + ss + ks

    def validate(self, results, text, s):
        if not results:
            return results
        res = []
        s_date = self.get_s_start_date(s)
        for person in results:
            original_text = self.graph.value(s, URIRef('http://www.w3.org/2004/02/skos/core#prefLabel'))
            units = {str(u) for u in self.graph.objects(s, URIRef('http://ldf.fi/warsa/photographs/unit'))}
            score = self.get_score(person, s, s_date, text, original_text, results, units)
            log_msg = "{} ({}) scored {} [{}]".format(
                person.get('label'),
                person.get('id'),
                score,
                ', '.join(set(person.get('properties', {}).get('rank', []))))

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
    text = re.sub(r'\b[Tt]km\.', 'tykkimies ', text)

    text = re.sub(r'[Ll]ääkintäkenraali\b', 'kenraalikunta', text)

    text = text.replace('Paavo Nurmi', '#')
    text = text.replace('Heinrichsin', 'Heinrichs')
    text = text.replace('Laiva Josif Stalin', '#')
    text = re.sub(r'(Aleksandra\W)?Kollontai(\b|lle|n|hin)', 'Alexandra Kollontay', text)
    text = re.sub(r'Blick(\b|ille|in)', 'Aarne Leopold Blick', text)
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
    # text = text.replace('E. Mäkinen', '## kenraalimajuri Mäkinen')
    text = re.sub(r'(?<!Aimo )(?<!Aukusti )(?<!Y\.)Tanner', '# Väinö Tanner #', text)
    # text = text.replace('Niukkanen', '## Juho Niukkanen')
    # text = text.replace('Söderhjelm', '## Johan Otto Söderhjelm')
    text = re.sub(r'(?<![Ee]verstiluutnantti )Paasikivi', '# Juho Kusti Paasikivi', text)
    text = re.sub(r'[Mm]inisteri Walden', '# kenraalikunta Walden', text)
    text = re.sub(r'(?<![Ee]versti )(?<![Kk]enraaliluutnantti )(?<![Kk]enraalimajuri )(?<![Kk]enraalikunta )(?<!Rudolf )Walden', '# kenraalikunta Walden #', text)
    text = re.sub(r'[vV]ääpeli( Oiva)? Tuomi(nen|selle|sen)', '# lentomestari Oiva Tuominen', text)
    text = re.sub(r'Ukko[ -]Pekka(\W+Svinhufvud)?', 'Pehr Evind Svinhufvud', text)
    text = re.sub(r'[Pp]residentti Svinhufvud', 'Pehr Evind Svinhufvud', text)
    text = re.sub(r'[Pp]residentti\s+ja\s+rouva\s+Svinhufvud', 'Pehr Evind Svinhufvud # Ellen Svinhufvud #', text)
    text = re.sub(r'[Rr]ouva\s+Svinhufvud', '# Ellen Svinhufvud ', text)
    text = text.replace('Öhqvist', 'Öhquist')
    text = text.replace('Jörgen Hageman', 'Jörgen Hagemann')
    text = re.sub('[Ee]versti(luutnantti)?( [KA].)? Paasonen', 'eversti Antero Paasonen', text)
    text = re.sub('[Ee]verstiluutnantti M. Nurmi', 'eversti Martti Nurmi', text)
    text = re.sub('[VW]inell(in|ille|illa|ia|ista)', 'Winell', text)

    # Add a space after commas where it's missing
    text = re.sub(r'(?<=\S),(?=\S)', ', ', text)

    # Pretty sure this is the guy
    text = text.replace('Tuomas Noponen', 'korpraali Tuomas Noponen')

    text = text.replace('Sotamies Pihlajamaa', 'sotamies Väinö Pihlajamaa')

    # Events only
    if Validator.dataset == 'event':
        text = text.replace('Ryti', '# Risto Ryti')
        text = text.replace('Tanner', '# Väinö Tanner')
        text = re.sub(r'(?<!M\.\W)Kallio(lle|n)?\b', '# Kyösti Kallio', text)
        text = text.replace('Molotov', '# V. Molotov')  # not for photos
        text = re.sub(r'(?<!Josif\W)Stalin(ille|ilta|in|iin)?\b', 'Josif Stalin', text)
        text = text.replace('eversti L. Haanterä', 'everstiluutnantti L. Haanterä')

    text = text.strip()
    text = re.sub(r'\s+', ' ', text)

    if text != orig:
        logger.info('Preprocessed to: {}'.format(text))

    return text


ignore = [
    'Ensio Pehr Hjalmar Siilasvuo',
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
        Validator.dataset = 'event'
    elif dataset_name == 'photo':
        print('Handling as photos')
        Validator.dataset = 'photo'
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
