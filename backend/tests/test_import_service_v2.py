"""Persisted import plans: real fixtures, rollback, resume and canonical references."""
from pathlib import Path
import os
from uuid import uuid4
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import event, select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base
from app.models.client import Client
from app.models.site import Site
from app.models.equipment import Equipment
from app.models.intervention import Intervention
from app.models.import_batch import ImportRecord, ImportReference
from app.services.import_service import ImportService

FIXTURES = Path(__file__).parent / 'fixtures' / 'excel'
CLIENT_CSV = b'ID_ancien;Nom;Telephone;Adresse_facturation\nC1;Alpha;0612345678;Paris\nC2;Bravo;0623456789;Lyon\n'


@pytest_asyncio.fixture
async def environment():
    url = os.environ.get('TERVO_IMPORT_TEST_DATABASE_URL')
    schema = 'import_test_' + uuid4().hex
    if url:
        admin_engine = create_async_engine(url)
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA {schema}'))
        engine = create_async_engine(url,connect_args={'server_settings':{'search_path':schema}})
    else:
        engine = create_async_engine('sqlite+aiosqlite:///:memory:')
        @event.listens_for(engine.sync_engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        yield ImportService(db), factory
    await engine.dispose()
    if url:
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        await admin_engine.dispose()


async def stage_clients(service, content=CLIENT_CSV):
    preview = await service.stage(content, 'clients.csv', 'archive', [{'kind':'clients'}])
    return await service.validate(preview['id'])


@pytest.mark.asyncio
async def test_idempotence_and_cross_file_references(environment):
    service, factory = environment
    plan = await stage_clients(service)
    assert plan['counts'].get('create') == 2, plan
    result = await service.execute(plan['id'], plan['plan_token'])
    assert result['status'] == 'success'
    assert result['counts']['committed'] == 2
    assert (await service.execute(plan['id'], plan['plan_token']))['status'] == 'success'
    assert (await stage_clients(service))['id'] == plan['id']
    other = await stage_clients(service, CLIENT_CSV.replace(b'C1;', b'C9;') + b'\n')
    assert other['counts'].get('associate') == 2, other
    assert (await service.execute(other['id'], other['plan_token']))['status'] == 'success'
    async with factory() as db:
        for model, count in [(Client,2),(ImportRecord,4),(ImportReference,3)]:
            assert await db.scalar(select(func.count()).select_from(model)) == count


@pytest.mark.asyncio
async def test_second_chunk_rollback_and_resume(environment):
    service, factory = environment
    plan = await stage_clients(service)
    async def fail_second(index):
        if index == 1:
            raise RuntimeError('simulated failure')
    service._before_chunk = fail_second
    result = await service.execute(plan['id'], plan['plan_token'], batch_size=1)
    assert result['status'] == 'failed'
    assert result['counts']['committed'] == 1
    assert (await service.errors(plan['id']))[-1]['code'] == 'BATCH_ROLLBACK'
    async def no_failure(index):
        pass
    service._before_chunk = no_failure
    result = await service.execute(plan['id'], plan['plan_token'], batch_size=1)
    assert result['status'] == 'success'
    assert result['counts']['committed'] == 2
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(Client)) == 2


@pytest.mark.asyncio
async def test_stale_snapshot_and_wrong_approval_token(environment):
    service, factory = environment
    plan = await stage_clients(service)
    with pytest.raises(HTTPException) as error:
        await service.execute(plan['id'], '0'*64)
    assert error.value.status_code == 409
    async with factory() as db:
        db.add(Client(full_name='External',phone='0600000000',address='Other'))
        await db.commit()
    with pytest.raises(HTTPException) as error:
        await service.execute(plan['id'], plan['plan_token'])
    assert error.value.status_code == 409
    new = await service.validate(plan['id'])
    assert new['plan_token'] != plan['plan_token']
    assert (await service.execute(new['id'], new['plan_token']))['status'] == 'success'


async def import_physical(service):
    file = next(FIXTURES.glob('01*.xlsx'))
    preview = await service.stage(file.read_bytes(), file.name, 'pack', [
        {'sheet':'Clients','kind':'clients'}, {'sheet':'Sites','kind':'sites'},
        {'sheet':'Equipements','kind':'equipment'}])
    decisions = {
        'Clients:6:clients':dict(action='associate',associate_source_id='C001',note='Doublon confirmé'),
        'Clients:7:clients':dict(action='ignore',note='Coordonnées à retrouver'),
        'Sites:6:sites':dict(action='ignore',note='Adresse à retrouver'),
        'Equipements:5:equipment':dict(action='create',corrections={'replaced_by_source_id':'E005'},note='Remplacement confirmé'),
        'Equipements:6:equipment':dict(action='create',note='Nouvelle instance confirmée'),
    }
    for row in range(2,6):
        decisions[f'Sites:{row}:sites'] = dict(action='create',corrections={'site_name':f'Site {row}'},note='Nom confirmé')
    plan = await service.validate(preview['id'], decisions)
    assert plan['counts'].get('pending',0) == 0, [(e['key'],e.get('planning_error')) for e in plan['items']]
    result = await service.execute(plan['id'],plan['plan_token'])
    assert result['status'] == 'success', await service.errors(plan['id'])
    return result


@pytest.mark.asyncio
async def test_fixture_two_passes_replacement_and_orphans(environment):
    service, factory = environment
    await import_physical(service)
    file = next(FIXTURES.glob('02*.xlsx'))
    preview = await service.stage(file.read_bytes(),file.name,'pack',[{'kind':'interventions'}])
    decisions = {f'Interventions:{row}:interventions':dict(action='create',
        corrections={'title':f'Historique {row}','status':'COMPLETED'},note='Statut historique confirmé') for row in range(2,9)}
    plan = await service.validate(preview['id'],decisions)
    assert plan['counts'].get('create') == 7, plan
    assert plan['counts'].get('pending') == 1
    result = await service.execute(plan['id'],plan['plan_token'],batch_size=3)
    assert result['status'] == 'partial', await service.errors(plan['id'])
    async with factory() as db:
        for model,count in [(Client,4),(Site,4),(Equipment,5),(Intervention,7)]:
            assert await db.scalar(select(func.count()).select_from(model)) == count
        old = await db.scalar(select(Equipment).where(Equipment.serial_number=='GT20-2009-018'))
        assert old.replaced_by_id is not None
        assert old.lifecycle_status.value == 'REPLACED'
        diagnostic = await db.scalar(select(Intervention).where(Intervention.title=='Historique 7'))
        assert diagnostic.equipment_id is None
    assert await service.errors(plan['id'])


@pytest.mark.asyncio
async def test_missing_phone_and_orphan_remain_pending(environment):
    service, factory = environment
    plan = await stage_clients(service,b'Nom;Telephone;Adresse_facturation\nIncomplet;;Paris\n')
    assert plan['counts'].get('pending') == 1
    assert any(a['code']=='MISSING_PHONE' for a in plan['items'][0]['anomalies'])
    assert (await service.execute(plan['id'],plan['plan_token']))['status'] == 'partial'
    preview = await service.stage(b'ID_site;Date;Titre\nS999;2025-01-01;Visite\n','orphan.csv','archive',[{'kind':'interventions'}])
    orphan = await service.validate(preview['id'])
    assert orphan['items'][0]['planning_error']['code'] == 'ORPHAN'
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(Client)) == 0


@pytest.mark.asyncio
async def test_500_rows_commit_and_failure_after_write_rolls_back_whole_second_chunk(environment):
    service, factory = environment
    content = 'ID_ancien;Nom;Telephone;Adresse_facturation\n' + ''.join(
        f'C{i};Client {i};06{i:08d};Adresse {i}\n' for i in range(502))
    plan = await stage_clients(service,content.encode())
    assert plan['counts'].get('create') == 502
    original_write = service._write
    async def fail_after_write(db,batch,entry,ids):
        await original_write(db,batch,entry,ids)
        if entry['source']['row'] == 503:
            raise RuntimeError('Failure after a database flush')
    service._write = fail_after_write
    result = await service.execute(plan['id'],plan['plan_token'])
    assert result['status'] == 'failed'
    assert result['counts']['committed'] == 500
    async with factory() as db:
        for model in (Client,ImportRecord,ImportReference):
            assert await db.scalar(select(func.count()).select_from(model)) == 500
    service._write = original_write
    assert (await service.execute(plan['id'],plan['plan_token']))['counts']['committed'] == 502


@pytest.mark.asyncio
async def test_revalidate_partial_with_correction_and_keep_source(environment):
    service, factory = environment
    plan = await stage_clients(service,b'ID_ancien;Nom;Telephone;Adresse_facturation\nC1;Alpha;0612345678;Paris\nC2;Bravo;;Lyon\n')
    await service.execute(plan['id'],plan['plan_token'])
    key = next(e['key'] for e in plan['items'] if e['op']=='pending')
    changed = await service.validate(plan['id'],{key:dict(action='create',corrections={'phone':'06 23 45 67 89'},note='Téléphone vérifié')})
    assert changed['counts'].get('create') == 1
    assert (await service.execute(changed['id'],changed['plan_token']))['status'] == 'success'
    async with factory() as db:
        record = await db.scalar(select(ImportRecord).where(ImportRecord.row_key==key))
        assert record.original_values['Telephone'] == ''
        assert record.normalized_values['phone'] == '0623456789'
        assert record.decision['human']['note'] == 'Téléphone vérifié'
    with pytest.raises(HTTPException) as error:
        # A completed import is immutable; status=success returns its existing report.
        # Check mapping rejection on another partially committed import.
        partial = await stage_clients(service,b'ID_ancien;Nom;Telephone;Adresse_facturation\nC9;Charlie;0634567890;Nice\nC10;Delta;;Lille\n')
        await service.execute(partial['id'],partial['plan_token'])
        await service.validate(partial['id'],selections=[{'kind':'clients','header_row':1}])
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_missing_phone_association_preserves_existing_data(environment):
    service, factory = environment
    first = await stage_clients(service)
    await service.execute(first['id'],first['plan_token'])
    plan = await stage_clients(service,b'ID_ancien;Nom;Telephone;Adresse_facturation\nC1;Alpha;;\n')
    assert plan['counts'].get('associate') == 1, plan
    assert any(a['code']=='MISSING_PHONE' and a['severity']=='warning' for a in plan['items'][0]['anomalies'])
    assert (await service.execute(plan['id'],plan['plan_token']))['status'] == 'success'
    async with factory() as db:
        client = await db.scalar(select(Client).where(Client.full_name=='alpha'))
        assert client.phone == '0612345678'
        assert client.address == 'Paris'


@pytest.mark.asyncio
async def test_active_lease_blocks_other_import_and_expired_lease_can_resume(environment):
    from datetime import timedelta
    from app.models.import_batch import ImportBatch
    from app.services.import_service import now
    service, factory = environment
    first = await stage_clients(service)
    second = await stage_clients(service,CLIENT_CSV+b'\n')
    async with factory() as db:
        batch = await db.get(ImportBatch,first['id'])
        batch.status, batch.execution_slot, batch.execution_token = 'running',1,'old-worker'
        batch.lease_until = now()+timedelta(minutes=10)
        await db.commit()
    with pytest.raises(HTTPException) as error:
        await service.execute(second['id'],second['plan_token'])
    assert error.value.status_code == 409
    async with factory() as db:
        batch = await db.get(ImportBatch,first['id'])
        batch.lease_until = now()-timedelta(minutes=1)
        await db.commit()
    assert (await service.execute(first['id'],first['plan_token']))['status'] == 'success'


@pytest.mark.asyncio
async def test_product_precedes_equipment_and_unknown_product_is_not_invented(environment):
    from io import BytesIO
    from openpyxl import Workbook
    from app.models.product import Product
    service, factory = environment
    await import_physical(service)
    book = Workbook()
    products = book.active
    products.title = 'Catalogue'
    products.append(['Reference produit','Nom produit','Marque','Modele','Categorie'])
    products.append(['P1','Chaudière','Marque','Modèle','Gaz'])
    equipment = book.create_sheet('Parc')
    equipment.append(['ID_equipement','ID_site','Reference produit','Numero_serie'])
    equipment.append(['E100','S001','P1','NEW-100'])
    equipment.append(['E101','S001','INCONNU','NEW-101'])
    stream = BytesIO()
    book.save(stream)
    preview = await service.stage(stream.getvalue(),'catalogue.xlsx','pack',[
        {'sheet':'Parc','kind':'equipment'},{'sheet':'Catalogue','kind':'products'}])
    plan = await service.validate(preview['id'])
    assert plan['counts'].get('create') == 2, plan
    assert plan['counts'].get('pending') == 1
    assert plan['items'][-1]['planning_error']['code'] == 'ORPHAN'
    assert (await service.execute(plan['id'],plan['plan_token']))['status'] == 'partial'
    async with factory() as db:
        product = await db.scalar(select(Product).where(Product.reference=='P1'))
        linked = await db.scalar(select(Equipment).where(Equipment.serial_number=='NEW-100'))
        assert linked.product_id == product.id
        assert await db.scalar(select(func.count()).select_from(Product)) == 1
        originals = list(await db.scalars(select(Equipment).where(Equipment.product_id.is_(None))))
        assert len(originals) == 5


@pytest.mark.asyncio
async def test_overlapping_historical_export_needs_human_association(environment):
    service, factory = environment
    await import_physical(service)
    recent_file = next(FIXTURES.glob('02*.xlsx'))
    recent = await service.stage(recent_file.read_bytes(),recent_file.name,'pack',[{'kind':'interventions'}])
    choices = {f'Interventions:{row}:interventions':dict(action='create',
        corrections={'title':f'Historique {row}','status':'COMPLETED'},note='Historique validé') for row in range(2,9)}
    plan = await service.validate(recent['id'],choices)
    await service.execute(plan['id'],plan['plan_token'])
    old_file = next(FIXTURES.glob('03*.xlsx'))
    old = await service.stage(old_file.read_bytes(),old_file.name,'pack',[{'kind':'interventions','two_digit_year_base':2000}])
    pending = await service.validate(old['id'])
    assert pending['counts'].get('pending') == 3, pending
    assert all(e['planning_error']['code'] in {'ORPHAN','PARENT_REQUIRES_REVIEW'} for e in pending['items']), pending
    sites = {e['key']:source for e,source in zip(pending['items'], ['S001','S003','S004'])}
    review = {key:dict(action='review',corrections={'site_source_id':site},note='Adresse composée comparée au site')
              for key,site in sites.items()}
    duplicates = await service.validate(old['id'],review)
    assert all(e['planning_error']['code']=='DUPLICATE_AMBIGUOUS' for e in duplicates['items']), str([(e['key'],e['normalized'],e.get('planning_error'),e.get('match')) for e in duplicates['items']])
    decisions = {e['key']:dict(action='associate',entity_id=e['match']['candidates'][0]['entity_id'],
                             corrections={'site_source_id':sites[e['key']]},
                             note='Intervention déjà importée, archive comparée') for e in duplicates['items']}
    approved = await service.validate(old['id'],decisions)
    assert approved['counts'].get('associate') == 3, approved
    assert (await service.execute(old['id'],approved['plan_token']))['status']=='success'
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(Intervention))==7
