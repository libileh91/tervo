"""Pure hierarchical matching; high similarity never overrides conflicting identities."""
from dataclasses import dataclass, field
import math
import re

from rapidfuzz.fuzz import token_sort_ratio
from app.importers.normalizer import Normalizer as N

AUTO_MATCH_THRESHOLD = 95.0
HUMAN_REVIEW_THRESHOLD = 80.0
SOURCE_FIELDS = {'clients':'client_source_id', 'sites':'site_source_id',
                 'equipment':'equipment_source_id', 'interventions':'intervention_source_id',
                 'products':'product_reference'}
PARENTS = {'sites':'client_id', 'equipment':'site_id', 'interventions':'site_id'}


@dataclass
class EntityMatch:
    zone: str
    score: float = 0.0
    entity_id: int | None = None
    reason: str = ''
    candidates: list[dict] = field(default_factory=list)
    evidence: str | None = None

    def to_dict(self):
        return dict(zone=self.zone, score=round(self.score, 2), entity_id=self.entity_id,
                    reason=self.reason, candidates=self.candidates, evidence=self.evidence)


class MultiLevelMatcher:
    def __init__(self, auto_threshold=95.0, review_threshold=80.0, max_candidates=5):
        if not 0 <= review_threshold < auto_threshold <= 100 or max_candidates < 1:
            raise ValueError('Seuils ou nombre de candidats invalides')
        self.auto_threshold, self.review_threshold = auto_threshold, review_threshold
        self.max_candidates = max_candidates
        self.client_weights = (.6, .3, .1)

    def classify(self, score):
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError('Score invalide')
        return 'auto' if score >= self.auto_threshold else 'human_review' if score >= self.review_threshold else 'new'

    @staticmethod
    def phone(value):
        try:
            return N.phone(value)
        except ValueError:
            return ''

    def score(self, kind, incoming, existing):
        if kind == 'clients':
            fields = [(key, weight, key == 'phone') for key, weight in zip(('full_name', 'phone', 'city'), self.client_weights)]
        elif kind == 'sites':
            fields = [('address', .8, False), ('city', .2, False)]
        elif kind == 'equipment':
            a, b = N.serial_number(incoming.get('serial_number')), N.serial_number(existing.get('serial_number'))
            if a and b and a != b:
                return 0.0
            fields = [('serial_number', .8, True), ('product_id', .2, True)]
        elif kind == 'products':
            return 100.0 if incoming.get('reference') and incoming.get('reference') == existing.get('reference') else 0.0
        elif kind == 'interventions':
            if not incoming.get('scheduled_date') or str(incoming['scheduled_date']) != str(existing.get('scheduled_date')):
                return 0.0
            # A shared day/site is a candidate, never proof of a duplicate visit.
            return 80 + .2 * token_sort_ratio(N.name(incoming.get('description') or incoming.get('title')),
                                            N.name(existing.get('description') or existing.get('title')))
        else:
            raise ValueError('Nature inconnue')
        total, weights = 0.0, 0.0
        for key, weight, exact in fields:
            normalize = self.phone if key == 'phone' else N.serial_number if key == 'serial_number' else N.name
            a, b = normalize(incoming.get(key)), normalize(existing.get(key))
            if not a or not b:
                continue
            similarity = (100 if a == b else 0) if exact else token_sort_ratio(a, b)
            total += weight * similarity
            weights += weight
        return min(100.0, total / weights) if weights else 0.0

    def conflict(self, kind, incoming, existing):
        keys = {'clients':['phone'], 'sites':['postal_code'], 'equipment':['serial_number','product_id'],
                'interventions':['equipment_id','scheduled_date'], 'products':['reference']}[kind]
        for key in keys:
            a, b = incoming.get(key), existing.get(key)
            if a is not None and b is not None and N.text(a) and N.text(b):
                norm = self.phone if key == 'phone' else N.name
                if norm(a) != norm(b):
                    return True
        if kind == 'clients' and incoming.get('full_name') and existing.get('full_name'):
            if token_sort_ratio(N.name(incoming['full_name']), N.name(existing['full_name'])) < 80:
                return True
        if kind == 'sites':
            a, b = incoming.get('address'), existing.get('address')
            if a and b:
                if re.findall(r'\d+', str(a)) != re.findall(r'\d+', str(b)):
                    return True
                if token_sort_ratio(N.name(a), N.name(b)) < 80:
                    return True
        return False

    def match(self, kind, incoming, existing, *, parent_id=None, namespace=None, references=None, force_review=False):
        if kind not in SOURCE_FIELDS:
            raise ValueError('Nature inconnue')
        parent = PARENTS.get(kind)
        if parent and parent_id is None:
            return EntityMatch('human_review', reason='Parent à résoudre avant rapprochement')
        pool = [e for e in existing if not parent or e.get(parent) == parent_id]
        flagged = force_review or 'doublon' in N.name(incoming.get('notes'))
        key = (namespace, kind, N.text(incoming.get(SOURCE_FIELDS[kind])))
        target = (references or {}).get(key) if namespace and key[2] else None
        if target is not None:
            found = next((e for e in pool if e['id'] == target), None)
            if found is None:
                return EntityMatch('human_review', reason='Référence source vers une cible absente ou un autre parent')
            candidate = dict(entity_id=target, score=100.0)
            if flagged or self.conflict(kind, incoming, found):
                return EntityMatch('human_review', 100, reason='Référence source contradictoire ou revue demandée', candidates=[candidate])
            return EntityMatch('auto', 100, target, 'Référence source fiable', [candidate], 'source_reference')
        scored = sorted([(self.score(kind, incoming, e), e) for e in pool], key=lambda pair:(-pair[0], pair[1]['id']))
        candidates = [dict(entity_id=e['id'], score=round(s, 2)) for s,e in scored[:self.max_candidates] if s > 0]
        best, found = scored[0] if scored else (0, None)
        zone = self.classify(best)
        reason = 'Aucune correspondance suffisante'
        if flagged:
            return EntityMatch('human_review', best, reason='Doublon signalé : validation requise', candidates=candidates)
        if found is not None and zone == 'auto':
            strong = {
                'clients': bool(incoming.get('full_name') and self.phone(incoming.get('phone')) and
                                self.phone(incoming.get('phone')) == self.phone(found.get('phone'))),
                'sites': bool(incoming.get('address') and (incoming.get('city') or incoming.get('postal_code'))),
                'equipment': bool(incoming.get('serial_number') and found.get('serial_number')),
                'interventions': False,
                'products': True,
            }[kind]
            tied = len(scored) > 1 and scored[1][0] >= self.review_threshold
            if not strong or tied or self.conflict(kind, incoming, found):
                zone, reason = 'human_review', 'Identité insuffisante, conflit ou plusieurs candidats'
            else:
                return EntityMatch('auto', best, found['id'], 'Identité corroborée', candidates, 'corroborated')
        if zone == 'human_review':
            reason = reason if reason != 'Aucune correspondance suffisante' else 'Correspondance à confirmer'
        return EntityMatch(zone, best, reason=reason, candidates=candidates)
