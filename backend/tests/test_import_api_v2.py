"""INT-101: real JWT roles and the complete persisted approval workflow."""
import json
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, func
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User, Role
from app.models.client import Client
from app.models.import_batch import ImportBatch, ImportRecord
from tests.test_import_service_v2 import environment, CLIENT_CSV, FIXTURES

PREFIX = '/api/v1/admin/import'


@pytest_asyncio.fixture
async def api(environment):
    service, factory = environment
    async with factory() as db:
        admin = User(username='admin-import',email='admin-import@example.test',hashed_password='unused',role=Role.ADMIN)
        tech = User(username='tech-import',email='tech-import@example.test',hashed_password='unused',role=Role.TECHNICIAN)
        db.add_all([admin,tech])
        await db.commit()
        tokens = {role:{'Authorization':'Bearer '+create_access_token(user.id)} for role,user in [('admin',admin),('tech',tech)]}
    async def database():
        async with factory() as db:
            yield db
    app.dependency_overrides[get_db] = database
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            yield client,tokens,factory
    finally:
        app.dependency_overrides.clear()


async def preview(api, content=CLIENT_CSV, filename='clients.csv', selections=None):
    client,tokens,_ = api
    return await client.post(PREFIX+'/preview',headers=tokens['admin'],
        data={'source_namespace':'archive','selections':json.dumps(selections or [{'kind':'clients'}])},
        files={'file':(filename,content)})


@pytest.mark.parametrize('method,path',[
    ('POST','/preview'),('POST','/validate'),('POST','/execute'),
    ('GET','/batches'),('GET','/batches/1'),('GET','/batches/1/errors'),
])
@pytest.mark.parametrize('role',['anonymous','tech'])
async def test_all_routes_require_admin(api,method,path,role):
    client,tokens,factory = api
    response = await client.request(method,PREFIX+path,headers=tokens.get(role,{}))
    assert response.status_code in ((401,403) if role=='anonymous' else (403,))
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(ImportBatch)) == 0


async def test_preview_approval_execution_and_paginated_reports(api):
    client,tokens,factory = api
    content = ('ID_ancien;Nom;Telephone;Adresse_facturation\n'+''.join(
        f'C{i};Client {i};06{i:08d};Adresse {i}\n' for i in range(12))).encode()
    response = await preview(api,content)
    assert response.status_code == 200, response.text
    batch = response.json()
    assert batch['total']==12 and len(batch['items'])==10
    first = batch['items'][0]
    assert first['source']['file']=='clients.csv'
    assert first['source']['sheet']=='clients' and first['source']['row']==2
    assert first['source']['header_row']==1 and first['source']['encoding']=='utf-8-sig'
    assert first['mapping']['fields']['phone']=='Telephone'
    assert 'source_bytes' not in batch
    assert batch['selections'][0]['kind']=='clients'
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(Client)) == 0
    pending = await client.post(PREFIX+'/execute',headers=tokens['admin'],json={'batch_id':batch['id'],'plan_token':'0'*64})
    assert pending.status_code==409
    validated = await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':batch['id']})
    assert validated.status_code==200,validated.text
    plan = validated.json()
    assert plan['counts']['ready']==12
    payload = {'batch_id':batch['id'],'plan_token':plan['plan_token']}
    executed = await client.post(PREFIX+'/execute',headers=tokens['admin'],json=payload)
    assert executed.status_code==200,executed.text
    assert executed.json()['status']=='success'
    assert executed.json()['counts']['committed']==12
    assert (await client.post(PREFIX+'/execute',headers=tokens['admin'],json=payload)).json()['counts']['committed']==12
    assert (await preview(api,content)).json()['id']==batch['id']
    listing = (await client.get(PREFIX+'/batches?page_size=1',headers=tokens['admin'])).json()
    assert listing['total']==1 and listing['pages']==1
    assert 'items' not in listing['items'][0]
    detail = (await client.get(PREFIX+f"/batches/{batch['id']}?page=2&page_size=10",headers=tokens['admin'])).json()
    assert len(detail['items'])==2
    errors = await client.get(PREFIX+f"/batches/{batch['id']}/errors",headers=tokens['admin'])
    assert errors.status_code==200
    assert errors.json()['total']==0
    async with factory() as db:
        record = await db.scalar(select(ImportRecord).limit(1))
        assert record.decision['approved_by'] is not None


async def test_phone_correction_original_values_and_error_history(api):
    client,tokens,factory = api
    batch = (await preview(api,b'Nom;Telephone;Adresse_facturation\nBravo;;Lyon\n')).json()
    assert any(a['code']=='MISSING_PHONE' for a in batch['items'][0]['anomalies'])
    first = (await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':batch['id']})).json()
    assert first['counts']['pending']==1
    errors = (await client.get(PREFIX+f"/batches/{batch['id']}/errors?page_size=1",headers=tokens['admin'])).json()
    assert errors['total']>=1 and len(errors['items'])==1
    assert errors['items'][0]['code']=='MISSING_PHONE'
    decision = {'action':'create','corrections':{'phone':'06 23 45 67 89'},'note':'Numéro confirmé auprès du client'}
    response = await client.post(PREFIX+'/validate',headers=tokens['admin'],json={
        'batch_id':batch['id'],'decisions':{batch['items'][0]['key']:decision}})
    assert response.status_code==200,response.text
    plan = response.json()
    assert plan['counts']['create']==1
    assert plan['items'][0]['original']['Telephone']==''
    assert plan['items'][0]['effective_values']['phone']=='0623456789'
    old = await client.post(PREFIX+'/execute',headers=tokens['admin'],json={'batch_id':batch['id'],'plan_token':first['plan_token']})
    assert old.status_code==409
    result = await client.post(PREFIX+'/execute',headers=tokens['admin'],json={'batch_id':batch['id'],'plan_token':plan['plan_token']})
    assert result.json()['status']=='success'
    async with factory() as db:
        record = await db.scalar(select(ImportRecord))
        assert record.decision['human']['note']==decision['note']
        assert record.original_values['Telephone']==''
        assert record.normalized_values['phone']=='0623456789'


async def test_manifest_changes_need_new_approval_and_immutable_execute(api):
    client,tokens,_ = api
    batch = (await preview(api)).json()
    first = (await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':batch['id']})).json()
    second = await client.post(PREFIX+'/validate',headers=tokens['admin'],json={
        'batch_id':batch['id'],'selections':[{'kind':'clients','header_row':1,'mapping':{'full_name':'Nom'}}]})
    assert second.status_code==200,second.text
    assert second.json()['plan_token']!=first['plan_token']
    payload={'batch_id':batch['id'],'plan_token':first['plan_token']}
    assert (await client.post(PREFIX+'/execute',headers=tokens['admin'],json=payload)).status_code==409
    payload['plan_token']=second.json()['plan_token']
    assert (await client.post(PREFIX+'/execute',headers=tokens['admin'],json={**payload,'decisions':{}})).status_code==422
    assert (await client.post(PREFIX+'/execute',headers=tokens['admin'],json=payload)).json()['status']=='success'


@pytest.mark.parametrize('filename,content',[
    ('bad.pdf',b'pdf'),('bad.xlsx',b'not a zip archive'),('empty.csv',b''),
    ('broken.csv',b'Nom;Telephone\n"unfinished'),
])
async def test_invalid_uploads_are_client_errors(api,filename,content):
    response = await preview(api,content,filename)
    assert response.status_code==422,response.text


async def test_upload_limits_and_malformed_selections(api):
    client,tokens,_ = api
    assert (await preview(api,b'x'*(10*1024*1024+1))).status_code==413
    for selections in ('not-json','{}','[]','[{"kind":"mixed"}]','[{"kind":"clients","unexpected":1}]'):
        response = await client.post(PREFIX+'/preview',headers=tokens['admin'],
            data={'source_namespace':'archive','selections':selections},files={'file':('a.csv',CLIENT_CSV)})
        assert response.status_code==422,response.text


async def test_missing_import_invalid_pagination_and_unknown_decision(api):
    client,tokens,_ = api
    for path in ('/batches/999','/batches/999/errors'):
        assert (await client.get(PREFIX+path,headers=tokens['admin'])).status_code==404
    for path in ('/batches?page=0','/batches?page_size=101','/batches/1?page_size=0'):
        assert (await client.get(PREFIX+path,headers=tokens['admin'])).status_code==422
    assert (await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':999})).status_code==404
    assert (await client.post(PREFIX+'/execute',headers=tokens['admin'],json={'batch_id':999,'plan_token':'0'*64})).status_code==404
    batch = (await preview(api)).json()
    response = await client.post(PREFIX+'/validate',headers=tokens['admin'],json={
        'batch_id':batch['id'],'decisions':{'unknown':{'action':'ignore','note':'test'}}})
    assert response.status_code==422


async def test_fixture_preview_preserves_site_and_replacement_proposals(api):
    path=FIXTURES/'01_clients_sites_equipements.xlsx'
    response=await preview(api,path.read_bytes(),path.name,[{'sheet':'Sites','kind':'sites'},{'sheet':'Equipements','kind':'equipment'}])
    assert response.status_code==200,response.text
    rows=response.json()['items']
    assert any(a['code']=='SITE_NAME_REQUIRES_CONFIRMATION' for e in rows for a in e['anomalies'])
    assert any(a['code']=='REPLACEMENT_REQUIRES_REVIEW' for e in rows for a in e['anomalies'])


async def test_human_association_and_stale_database_are_enforced(api):
    client,tokens,factory = api
    initial = (await preview(api)).json()
    plan = (await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':initial['id']})).json()
    async with factory() as db:
        db.add(Client(full_name='autre client',phone='0699999999',address='Autre adresse'))
        await db.commit()
    assert (await client.post(PREFIX+'/execute',headers=tokens['admin'],json={
        'batch_id':plan['id'],'plan_token':plan['plan_token']})).status_code==409
    plan = (await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':plan['id']})).json()
    assert (await client.post(PREFIX+'/execute',headers=tokens['admin'],json={
        'batch_id':plan['id'],'plan_token':plan['plan_token']})).json()['status']=='success'
    batch = (await preview(api,b'ID_ancien;Nom;Telephone;Adresse_facturation\nALIAS;A.;;\n')).json()
    choice = {'action':'associate','associate_source_id':'C1','note':'Identité confirmée sur archive'}
    approved = await client.post(PREFIX+'/validate',headers=tokens['admin'],json={
        'batch_id':batch['id'],'decisions':{batch['items'][0]['key']:choice}})
    assert approved.status_code==200,approved.text
    assert approved.json()['counts']['associate']==1
    result = await client.post(PREFIX+'/execute',headers=tokens['admin'],json={
        'batch_id':batch['id'],'plan_token':approved.json()['plan_token']})
    assert result.json()['status']=='success'
    async with factory() as db:
        assert await db.scalar(select(func.count()).select_from(Client))==3
        record = await db.scalar(select(ImportRecord).where(ImportRecord.import_batch_id==batch['id']))
        assert record.decision['human']['associate_source_id']=='C1'
        target = await db.get(Client,record.entity_id)
        assert target.phone=='0612345678'


@pytest.mark.parametrize('choice',[
    {'action':'associate','note':'sans cible'},
    {'action':'associate','entity_id':1,'associate_source_id':'C1','note':'deux cibles'},
    {'action':'create','entity_id':1,'note':'mauvaise action'},
    {'action':'ignore','note':'   '},
])
async def test_decision_contract_rejects_ambiguous_or_unjustified_choices(api,choice):
    client,tokens,_ = api
    batch = (await preview(api)).json()
    response = await client.post(PREFIX+'/validate',headers=tokens['admin'],json={
        'batch_id':batch['id'],'decisions':{batch['items'][0]['key']:choice}})
    assert response.status_code==422


async def test_partial_import_mapping_and_committed_decisions_are_frozen(api):
    client,tokens,_ = api
    batch = (await preview(api,b'Nom;Telephone;Adresse_facturation\nAlpha;0612345678;Paris\nBravo;;Lyon\n')).json()
    plan = (await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':batch['id']})).json()
    completed = next(e['key'] for e in plan['items'] if e['op']=='create')
    result = await client.post(PREFIX+'/execute',headers=tokens['admin'],json={
        'batch_id':batch['id'],'plan_token':plan['plan_token']})
    assert result.json()['status']=='partial'
    for extra in ({'selections':[{'kind':'clients','header_row':1}]},
                  {'decisions':{completed:{'action':'ignore','note':'Modification tardive'}}}):
        response = await client.post(PREFIX+'/validate',headers=tokens['admin'],json={'batch_id':batch['id'],**extra})
        assert response.status_code==409
