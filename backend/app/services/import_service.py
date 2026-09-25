"""Staged imports: immutable sources, approved plans, per-chunk transactions and audit."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

from fastapi import HTTPException
from sqlalchemy import select, update, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.importers.ingestion import read_sources
from app.importers.report import DEFAULT_BATCH_SIZE
from app.models.client import Client
from app.models.site import Site
from app.models.product import Product
from app.models.equipment import Equipment
from app.models.intervention import Intervention
from app.models.user import User
from app.models.import_batch import ImportBatch, ImportRecord, ImportReference, ImportError
from app.schemas.imports import ImportDecision, SheetSelection
from app.services.import_planner import ImportPlanner

MODELS = dict(clients=Client,sites=Site,products=Product,equipment=Equipment,interventions=Intervention)


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,default=str,separators=(',',':')).encode()).hexdigest()


class ImportService:
    BATCH_SIZE = DEFAULT_BATCH_SIZE
    LEASE_MINUTES = 15

    def __init__(self, db):
        self.sessions = async_sessionmaker(db.bind, expire_on_commit=False)

    @staticmethod
    def compute_file_hash(path):
        with Path(path).open('rb') as stream:
            checksum = sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024),b''):
                checksum.update(chunk)
            return checksum.hexdigest()

    async def _get(self, db, batch_id, *, lock=False):
        query = select(ImportBatch).where(ImportBatch.id == batch_id)
        if lock:
            query = query.with_for_update()
        batch = await db.scalar(query)
        if batch is None:
            raise HTTPException(404,'Import introuvable')
        return batch

    async def _lock_domain(self, db):
        # Keep the checked snapshot stable until this chunk commits on PostgreSQL.
        if db.bind.dialect.name == 'postgresql':
            await db.execute(text('LOCK TABLE client, site, product, equipment, intervention, '
                                  '"user", import_reference IN SHARE ROW EXCLUSIVE MODE'))

    async def _load(self, db):
        pools = {}
        for kind, model in {**MODELS,'users':User}.items():
            columns = [model.id] if kind == 'users' else [c for c in model.__table__.columns if c.name not in {'created_at','updated_at'}]
            rows = (await db.execute(select(*columns).order_by(model.id))).mappings().all()
            pools[kind] = [{k:(v.isoformat() if isinstance(v,(date,datetime)) else v.value if hasattr(v,'value') else v)
                            for k,v in row.items()} for row in rows]
        refs = {(r.source_namespace,r.entity_type,r.source_id):r.entity_id
                for r in (await db.scalars(select(ImportReference).order_by(ImportReference.id))).all()}
        fingerprint = digest(dict(pools=pools,refs=sorted([list(key)+[value] for key,value in refs.items()])))
        return pools, refs, fingerprint

    async def stage(self, content, filename, namespace, selections, imported_by=None):
        namespace = namespace.strip()
        filename = Path(filename).name
        if not namespace or len(namespace)>100 or len(filename)>255:
            raise HTTPException(422,'Namespace ou nom de fichier invalide')
        selections = [SheetSelection.model_validate(s).model_dump(mode='json',exclude_none=True) for s in selections]
        checksum = sha256(content).hexdigest()
        async with self.sessions() as db:
            existing = await db.scalar(select(ImportBatch).where(ImportBatch.file_hash==checksum,ImportBatch.source_namespace==namespace))
            if existing:
                return await self.detail(existing.id,page_size=10)
            try:
                rows = read_sources(content,filename,namespace,selections)
            except (ValueError,KeyError,UnicodeError,BadZipFile,ParseError,IndexError) as exc:
                raise HTTPException(422,str(exc)) from exc
            if not rows:
                raise HTTPException(422,'Aucune ligne à importer')
            batch = ImportBatch(filename=filename,source_namespace=namespace,file_hash=checksum,
                source_bytes=content,selections=selections,source_records=rows,status='staged',imported_by=imported_by)
            db.add(batch)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                existing = await db.scalar(select(ImportBatch).where(ImportBatch.file_hash==checksum,ImportBatch.source_namespace==namespace))
                if existing is None:
                    raise
                return await self.detail(existing.id,page_size=10)
            return await self.detail(batch.id,page_size=10)

    async def validate(self, batch_id, decisions=None, selections=None, imported_by=None):
        async with self.sessions() as db:
            batch = await self._get(db,batch_id,lock=True)
            if batch.status in {'running','success'}:
                if batch.status == 'success':
                    return await self.detail(batch_id)
                raise HTTPException(409,'Import en cours')
            revision = batch.revision
            completed_rows = list(await db.scalars(select(ImportRecord).where(ImportRecord.import_batch_id==batch_id)))
            completed = {r.row_key:r.entity_id for r in completed_rows}
            choices = dict(batch.decisions or {})
            for key,value in (decisions or {}).items():
                choice = ImportDecision.model_validate(value).model_dump(mode='json')
                if key in completed and choice != choices.get(key):
                    raise HTTPException(409,'Une ligne déjà commitée ne peut pas être réécrite')
                choices[key] = choice
            rows = batch.source_records
            if selections is not None:
                if completed_rows:
                    raise HTTPException(409,'Mapping figé après le premier lot commité')
                selections = [SheetSelection.model_validate(s).model_dump(mode='json',exclude_none=True) for s in selections]
                try:
                    rows = read_sources(batch.source_bytes,batch.filename,batch.source_namespace,selections)
                except (ValueError,KeyError,UnicodeError,BadZipFile,ParseError,IndexError) as exc:
                    raise HTTPException(422,str(exc)) from exc
                if not rows:
                    raise HTTPException(422,'Aucune ligne à importer')
            pools,refs,fingerprint = await self._load(db)
            try:
                plan = ImportPlanner(batch.source_namespace,pools,refs,completed).build(rows,choices)
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from exc
            token = digest(dict(file_hash=batch.file_hash,namespace=batch.source_namespace,
                                plan=plan,choices=choices,revision=revision+1,selections=selections if selections is not None else batch.selections))
            # Optimistic revision check: simultaneous validation cannot overwrite approval.
            result = await db.execute(update(ImportBatch).where(ImportBatch.id==batch_id,
                ImportBatch.revision==revision,ImportBatch.status.notin_(['running','success']))
                .values(revision=revision+1,plan=plan,decisions=choices,plan_token=token,
                        database_snapshot=fingerprint,status='ready',imported_by=imported_by,
                        selections=selections if selections is not None else batch.selections,source_records=rows))
            if result.rowcount != 1:
                await db.rollback()
                raise HTTPException(409,'Import modifié pendant la validation')
            for entry in plan:
                for anomaly in entry.get('anomalies',[]):
                    self._error(db,batch_id,revision+1,entry,anomaly['code'],anomaly['error'],anomaly['severity'])
                if entry['op'] == 'pending':
                    error = entry['planning_error']
                    self._error(db,batch_id,revision+1,entry,error['code'],error['message'])
            await db.commit()
        return await self.detail(batch_id)

    @staticmethod
    def _error(db,batch_id,revision,entry,code,message,severity='error'):
        db.add(ImportError(import_batch_id=batch_id,revision=revision,row_key=entry['key'],code=code,
            severity=severity,message=message,source=entry['source'],original_values=entry['original']))

    async def _before_chunk(self, index):
        """Fault injection seam for transactional tests; never exposed in the API."""

    async def _write(self, db, batch, entry, ids):
        action, kind = entry['op'],entry['kind']
        target = entry.get('target_id')
        resolve = lambda x: ids[x] if isinstance(x,int) and x < 0 else x
        if action == 'create':
            values = {k:resolve(v) if k.endswith('_id') else v for k,v in entry['body'].items()}
            for key in ('installed_at','commissioned_at','warranty_start','warranty_end','scheduled_date'):
                if values.get(key):
                    values[key] = date.fromisoformat(values[key])
            entity = MODELS[kind](**values)
            db.add(entity)
            await db.flush()
            ids[target] = entity.id
            target = entity.id
        elif action == 'associate':
            target = resolve(target)
            if await db.get(MODELS[kind],target) is None:
                raise ValueError('Cible disparue')
        if action != 'ignore' and entry.get('source_id'):
            key = dict(source_namespace=batch.source_namespace,entity_type=kind,source_id=entry['source_id'])
            reference = await db.scalar(select(ImportReference).filter_by(**key))
            if reference and reference.entity_id != target:
                raise ValueError('Référence source contradictoire')
            if reference is None:
                db.add(ImportReference(**key,entity_id=target))
        db.add(ImportRecord(import_batch_id=batch.id,row_key=entry['key'],entity_type=kind,entity_id=target,
            action=action,source=entry['source'],original_values=entry['original'],
            normalized_values=entry.get('effective_values',entry['normalized']),
            decision=dict(human=entry.get('decision',{}),matcher=entry.get('match'),
                          approved_by=batch.imported_by,revision=batch.revision,plan_target=entry.get('target_id'))))

    async def execute(self, batch_id, plan_token, *, batch_size=None):
        execution_token = uuid4().hex
        size = self.BATCH_SIZE if batch_size is None else batch_size
        if not 1 <= size <= 500:
            raise ValueError('Taille de lot invalide')
        async with self.sessions() as db:
            async with db.begin():
                await db.execute(update(ImportBatch).where(ImportBatch.execution_slot==1,
                    ImportBatch.lease_until < now()).values(execution_slot=None,status='failed',lease_until=None,execution_token=None))
                batch = await self._get(db,batch_id)
                if batch.plan_token != plan_token or not batch.plan:
                    raise HTTPException(409,'Valider le plan actuel avant exécution')
                if batch.status == 'success':
                    return await self.detail(batch_id)
                if batch.status not in {'ready','partial','failed'}:
                    raise HTTPException(409,'Import non disponible')
                _,_,fingerprint = await self._load(db)
                if fingerprint != batch.database_snapshot:
                    raise HTTPException(409,'Référentiel modifié : revalider le plan')
                try:
                    claim = await db.execute(update(ImportBatch).where(ImportBatch.id==batch_id,
                        ImportBatch.status.in_(['ready','partial','failed']),ImportBatch.plan_token==plan_token)
                        .values(status='running',execution_slot=1,execution_token=execution_token,lease_until=now()+timedelta(minutes=self.LEASE_MINUTES)))
                    if claim.rowcount != 1:
                        raise HTTPException(409,'Import déjà pris en charge')
                except IntegrityError as exc:
                    raise HTTPException(409,'Un autre import est en cours') from exc
        # One transaction per chunk; the approved plan itself is never recomputed.
        async with self.sessions() as db:
            batch = await self._get(db,batch_id)
            records = list(await db.scalars(select(ImportRecord).where(ImportRecord.import_batch_id==batch_id)))
            done = {r.row_key for r in records}
            entries = [e for e in batch.plan if e['op'] in {'create','associate','ignore'} and e['key'] not in done]
            ids = {r.decision['plan_target']:r.entity_id for r in records if isinstance(r.decision.get('plan_target'),int) and r.decision['plan_target'] < 0}
        for index in range(0,len(entries),size):
            chunk = entries[index:index+size]
            try:
                async with self.sessions() as db:
                    async with db.begin():
                        batch = await self._get(db,batch_id,lock=True)
                        await self._lock_domain(db)
                        _,_,fingerprint = await self._load(db)
                        if batch.execution_token != execution_token or batch.status != 'running' or batch.plan_token != plan_token or fingerprint != batch.database_snapshot:
                            raise ValueError('Référentiel ou plan modifié')
                        await self._before_chunk(index // size)
                        for entry in chunk:
                            await self._write(db,batch,entry,ids)
                        await db.flush()
                        _,_,batch.database_snapshot = await self._load(db)
                        batch.lease_until = now()+timedelta(minutes=self.LEASE_MINUTES)
            except Exception as exc:
                async with self.sessions() as db:
                    async with db.begin():
                        batch = await self._get(db,batch_id,lock=True)
                        if batch.execution_token != execution_token:
                            raise HTTPException(409,'Exécution reprise par un autre processus')
                        batch.execution_token = None
                        batch.status, batch.execution_slot, batch.lease_until = 'failed',None,None
                        for entry in chunk:
                            self._error(db,batch_id,batch.revision,entry,'BATCH_ROLLBACK',
                                        f'Lot annulé ({type(exc).__name__}) ; aucune ligne de ce lot commitée')
                return await self.detail(batch_id)
        async with self.sessions() as db:
            async with db.begin():
                batch = await self._get(db,batch_id,lock=True)
                if batch.execution_token != execution_token:
                    raise HTTPException(409,'Exécution reprise par un autre processus')
                batch.execution_token = None
                batch.status = 'partial' if any(e['op']=='pending' for e in batch.plan) else 'success'
                batch.execution_slot, batch.lease_until, batch.completed_at = None,None,now()
        return await self.detail(batch_id)

    async def detail(self, batch_id, page=1, page_size=100):
        async with self.sessions() as db:
            batch = await self._get(db,batch_id)
            entries = batch.plan or batch.source_records
            committed = list(await db.scalars(select(ImportRecord).where(ImportRecord.import_batch_id==batch_id)))
            counts = Counter(e.get('op','unvalidated') for e in entries)
            counts.update({'committed':len(committed)})
            return dict(id=batch.id,filename=batch.filename,source_namespace=batch.source_namespace,
                file_hash=batch.file_hash,status=batch.status,revision=batch.revision,plan_token=batch.plan_token,
                total=len(entries),counts=dict(counts),items=entries[(page-1)*page_size:page*page_size],page=page,page_size=page_size)

    async def list_batches(self, page=1, page_size=25):
        async with self.sessions() as db:
            ids = list(await db.scalars(select(ImportBatch.id).order_by(ImportBatch.id.desc()).offset((page-1)*page_size).limit(page_size)))
        return [await self.detail(i,page_size=0) for i in ids]

    async def errors(self, batch_id, page=1, page_size=100):
        async with self.sessions() as db:
            await self._get(db,batch_id)
            errors = await db.scalars(select(ImportError).where(ImportError.import_batch_id==batch_id)
                .order_by(ImportError.id).offset((page-1)*page_size).limit(page_size))
            return [dict(id=e.id,revision=e.revision,key=e.row_key,code=e.code,severity=e.severity,
                         message=e.message,source=e.source,original=e.original_values) for e in errors]
