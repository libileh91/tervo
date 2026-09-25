"""Build reviewable operations against a snapshot, including in-file dependencies."""
from copy import deepcopy
from pydantic import ValidationError
from app.importers.format_detector import FormatDetector, ImportKind
from app.importers.multi_matcher import MultiLevelMatcher, SOURCE_FIELDS
from app.importers.normalizer import Normalizer as N
from app.schemas.client import ClientCreate
from app.schemas.site import SiteCreate
from app.schemas.equipment import EquipmentCreate
from app.schemas.product import ProductCreate
from app.schemas.intervention import InterventionCreate


class PendingRow(ValueError):
    def __init__(self, code, message, details=None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ImportPlanner:
    def __init__(self, namespace, pools, references, completed=None):
        self.namespace = namespace
        self.pools = deepcopy(pools)
        self.refs = dict(references)
        self.completed = completed or {}
        self.matcher = MultiLevelMatcher()

    def reference(self, kind, source_id, explicit=None):
        if explicit is not None:
            if not isinstance(explicit, int) or isinstance(explicit, bool) or explicit <= 0:
                raise PendingRow('INVALID_REFERENCE', 'Identifiant interne positif attendu')
            target = explicit
        elif source_id:
            target = self.refs.get((self.namespace, kind, N.text(source_id)))
        else:
            return None
        if target is None and kind == 'products' and source_id:
            target = next((p['id'] for p in self.pools['products'] if p.get('reference') == source_id), None)
        if target is None or not any(p['id'] == target for p in self.pools[kind]):
            raise PendingRow('ORPHAN', f'Référence {kind} introuvable : {source_id or explicit}')
        return target

    def entity(self, kind, entity_id):
        return next((r for r in self.pools[kind] if r['id'] == entity_id), None)

    def parent_site(self, v):
        site = self.reference('sites', v.get('site_source_id'), v.get('site_id'))
        client = self.reference('clients', v.get('client_source_id'), v.get('client_id'))
        if site is None and v.get('site_address'):
            if client is None and v.get('client_name'):
                match = self.matcher.match('clients',dict(full_name=v['client_name'],phone=v.get('phone')),
                                           self.pools['clients'])
                client = match.entity_id
            if client is not None:
                match = self.matcher.match('sites',dict(address=v['site_address'],city=v.get('city')),
                                           self.pools['sites'],parent_id=client)
                site = match.entity_id
                if site is None and match.candidates:
                    raise PendingRow('PARENT_REQUIRES_REVIEW','Confirmer le site proposé',
                                     {'parent_match':match.to_dict()})
        if site is None:
            raise PendingRow('ORPHAN','Site non résolu ; confirmer site_id ou sa référence source')
        if client is not None and self.entity('sites',site)['client_id'] != client:
            raise PendingRow('REFERENCE_CONFLICT','Le site appartient à un autre client')
        return site

    def body(self, kind, v):
        if kind == 'clients':
            return {k:v.get(k) for k in ('full_name','phone','email','address','postal_code','city','notes')}
        if kind == 'products':
            return dict(reference=v.get('product_reference'), name=v.get('product_name'),
                brand=v.get('product_brand'),model=v.get('product_model'),category=v.get('product_category'),
                characteristics=v.get('product_characteristics'),active=v.get('product_active') if v.get('product_active') is not None else True,
                description=v.get('description'))
        if kind == 'sites':
            client = self.reference('clients',v.get('client_source_id'),v.get('client_id'))
            if client is None:
                match = self.matcher.match('clients',dict(full_name=v.get('client_name')),self.pools['clients'])
                client = match.entity_id
            if client is None:
                raise PendingRow('ORPHAN','Client du site non résolu')
            return dict(client_id=client,name=v.get('site_name'),address=v.get('site_address'),
                        postal_code=v.get('postal_code'),city=v.get('city'),notes=v.get('notes'))
        site = self.parent_site(v)
        if kind == 'equipment':
            product = self.reference('products',v.get('product_reference'),v.get('product_id'))
            # Catalogue references can also predate the import journal.
            return dict(site_id=site,product_id=product,serial_number=v.get('serial_number'),
                installed_at=v.get('installation_date'),commissioned_at=v.get('commissioned_at'),
                warranty_start=v.get('warranty_start'),warranty_end=v.get('warranty_end'),
                lifecycle_status=v.get('lifecycle_status') or 'ACTIVE',notes=v.get('notes'))
        equipment = self.reference('equipment',v.get('equipment_source_id'),v.get('equipment_id'))
        if equipment is not None and self.entity('equipment',equipment)['site_id'] != site:
            raise PendingRow('REFERENCE_CONFLICT','Équipement hors du site de l’intervention')
        return dict(site_id=site,equipment_id=equipment,title=v.get('title'),description=v.get('description'),
            scheduled_date=v.get('scheduled_date'),under_warranty=v.get('under_warranty',False),
            status=v.get('status'),technician_id=v.get('technician_id'),observations=v.get('observations'))

    def validate_body(self, kind, body, v):
        schemas = dict(clients=ClientCreate,sites=SiteCreate,equipment=EquipmentCreate,
                       products=ProductCreate,interventions=InterventionCreate)
        values = dict(body)
        virtual = {k:x for k,x in values.items() if k.endswith('_id') and isinstance(x,int) and x < 0}
        values.update({k:abs(x) for k,x in virtual.items()})
        replacement = None
        if kind == 'equipment' and values['lifecycle_status'] == 'REPLACED':
            replacement = self.reference('equipment',v.get('replaced_by_source_id'),v.get('replaced_by_id'))
            if replacement is None:
                raise PendingRow('REPLACEMENT_REQUIRES_REVIEW','Confirmer la référence du nouvel équipement')
            if self.entity('equipment',replacement)['site_id'] != body['site_id']:
                raise PendingRow('REFERENCE_CONFLICT','Remplacement sur un autre site')
            values['lifecycle_status'] = 'OUT_OF_SERVICE'
        if kind == 'interventions':
            if values.get('status') not in {'PLANNED','IN_PROGRESS','COMPLETED','CANCELLED'}:
                raise PendingRow('HISTORICAL_MAPPING_REQUIRES_REVIEW','Confirmer le statut opérationnel historique')
            if values.get('technician_id') and not any(u['id'] == values['technician_id'] for u in self.pools['users']):
                raise PendingRow('ORPHAN','Technicien inconnu')
        result = schemas[kind](**values).model_dump(mode='json')
        result.update(virtual)
        if kind == 'interventions':
            result.update({k:body[k] for k in ('status','technician_id','observations')})
        if replacement is not None:
            result.update(lifecycle_status='REPLACED',replaced_by_id=replacement)
        return result

    def plan_one(self, entry, decision, virtual_id):
        kind, v = entry['kind'], dict(entry['normalized'])
        corrections = decision.get('corrections',{})
        allowed = {f.value for f in FormatDetector.EXPECTED_FIELDS[ImportKind(kind)]}
        allowed |= {'client_id','site_id','product_id','equipment_id','status','under_warranty','technician_id',
                    'replaced_by_source_id','replaced_by_id'}
        if set(corrections) - allowed:
            raise PendingRow('INVALID_CORRECTION','Champ de correction inconnu')
        v.update(corrections)
        if v.get('phone'):
            v['phone'] = N.phone(v['phone'])
        for field in ('scheduled_date','installation_date','commissioned_at','warranty_start','warranty_end'):
            if v.get(field):
                v[field] = N.date(v[field])
        if decision.get('action') == 'ignore':
            return dict(op='ignore',decision=decision,body={},target_id=None)
        # Invalid raw data cannot be silently ignored merely by selecting create.
        for anomaly in entry['anomalies']:
            if anomaly['code'] in {'INVALID_VALUE','VALUE_TOO_LONG','INVALID_WARRANTY_RANGE'}:
                keys = [k for k,c in entry['mapping']['fields'].items() if c == anomaly['column']]
                if not any(k in corrections for k in keys):
                    raise PendingRow(anomaly['code'],anomaly['error'])
        body = self.body(kind,v)
        incoming = {**v,**body}
        parent = body.get('client_id') if kind == 'sites' else body.get('site_id')
        match = self.matcher.match(kind,incoming,self.pools[kind],parent_id=parent,
                                   namespace=self.namespace,references=self.refs)
        action, target = decision.get('action'), decision.get('entity_id')
        if action == 'associate':
            if target is None and decision.get('associate_source_id'):
                target = self.reference(kind, decision['associate_source_id'])
            obj = self.entity(kind,target)
            if obj is None:
                raise PendingRow('ORPHAN','Cible d’association introuvable')
            if parent is not None and obj.get('client_id' if kind == 'sites' else 'site_id') != parent:
                raise PendingRow('REFERENCE_CONFLICT','Association vers un autre parent')
        elif action == 'create':
            if match.zone == 'auto':
                raise PendingRow('DUPLICATE_AMBIGUOUS','Une correspondance fiable existe ; associer ou corriger les données')
        elif match.zone == 'auto':
            action, target = 'associate', match.entity_id
        elif match.zone == 'human_review':
            entry['match'] = match.to_dict()
            raise PendingRow('DUPLICATE_AMBIGUOUS',match.reason)
        else:
            action = 'create'
        if (not decision or decision.get('action') == 'review') and any(a['severity'] == 'review' for a in entry['anomalies']):
            # Missing structural titles/names can be harmless for a proved association.
            harmless = {'SITE_NAME_REQUIRES_CONFIRMATION','TITLE_REQUIRES_CONFIRMATION',
                        'HISTORICAL_MAPPING_REQUIRES_REVIEW'} if action == 'associate' else set()
            if any(a['severity']=='review' and a['code'] not in harmless for a in entry['anomalies']):
                raise PendingRow('HUMAN_REVIEW_REQUIRED','Confirmer les propositions et champs sans mapping')
        if action == 'create':
            body = self.validate_body(kind,body,v)
            target = virtual_id
        source_id = N.text(v.get(SOURCE_FIELDS[kind]))
        if source_id and len(source_id) > 255:
            raise PendingRow('INVALID_REFERENCE', 'Référence source trop longue')
        if source_id:
            key = (self.namespace,kind,source_id)
            if key in self.refs and self.refs[key] != target:
                raise PendingRow('REFERENCE_CONFLICT','Référence source déjà attribuée à une autre cible')
            self.refs[key] = target
        if action == 'create':
            self.pools[kind].append(dict(id=target,**body))
        elif kind == 'clients':
            for anomaly in entry['anomalies']:
                if anomaly['code'] in {'MISSING_PHONE','MISSING_ADDRESS'}:
                    anomaly['severity'] = 'warning'
        return dict(op=action,target_id=target,body=body,source_id=source_id,
                    decision=decision,match=match.to_dict(),effective_values=v)

    def build(self, records, decisions):
        unknown = set(decisions) - {r['key'] for r in records}
        if unknown:
            raise ValueError('Décisions pour des lignes inconnues')
        order = {'products':0,'clients':1,'sites':2,'equipment':3,'interventions':4}
        queue = sorted(enumerate(deepcopy(records)),key=lambda pair:order[pair[1]['kind']])
        output = []
        while queue:
            next_queue, progress = [], False
            for index, entry in queue:
                if entry['key'] in self.completed:
                    output.append({**entry,'op':'done','target_id':self.completed[entry['key']]})
                    progress = True
                    continue
                try:
                    planned = self.plan_one(entry,decisions.get(entry['key'],{}),-index-1)
                    entry.pop('planning_error', None)
                    output.append({**entry,**planned})
                    progress = True
                except (PendingRow,ValidationError,ValueError) as exc:
                    entry.update(getattr(exc,'details',{}))
                    entry['planning_error'] = dict(code=getattr(exc,'code','VALIDATION_ERROR'),message=str(exc))
                    next_queue.append((index,entry))
            if not progress:
                output.extend({**entry,'op':'pending'} for _,entry in next_queue)
                break
            queue = next_queue
        return output
