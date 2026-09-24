import pytest
from app.importers.multi_matcher import MultiLevelMatcher
from app.importers.matcher import ClientMatcher

M = MultiLevelMatcher()
CLIENTS = [dict(id=1, full_name='Jean Dupont', phone='0612345678', city='Massy')]


def test_client_exact_missing_phone_ambiguous_and_flagged():
    assert M.match('clients', CLIENTS[0], CLIENTS).entity_id == 1
    assert M.match('clients', dict(full_name='Dupont Jean'), CLIENTS).zone == 'human_review'
    assert M.match('clients', {**CLIENTS[0], 'notes':'DOUBLON probable'}, CLIENTS).zone == 'human_review'
    assert M.match('clients', CLIENTS[0], [*CLIENTS, {**CLIENTS[0], 'id':2}]).zone == 'human_review'
    assert M.match('clients', dict(full_name='Autre', phone='0123456789'), CLIENTS).zone == 'new'
    assert ClientMatcher().match(CLIENTS[0], CLIENTS).is_auto


def test_source_reference_scoping_and_conflict():
    refs = {('archive', 'clients','C001'):1}
    candidate = dict(client_source_id='C001', full_name='Dupont Jean')
    result = M.match('clients', candidate, CLIENTS, namespace='archive', references=refs)
    assert result.entity_id == 1 and result.evidence == 'source_reference'
    assert M.match('clients', candidate, CLIENTS, namespace='other', references=refs).zone == 'human_review'
    assert M.match('clients', {**candidate,'phone':'0123456789'}, CLIENTS, namespace='archive', references=refs).zone == 'human_review'


def test_site_parent_and_house_number():
    sites = [dict(id=1, client_id=7, address='12 rue des Lilas', city='Massy',postal_code='91300')]
    incoming = dict(address='12 RUE DES LILAS', city='Massy',postal_code='91300')
    assert M.match('sites', incoming, sites, parent_id=7).entity_id == 1
    assert M.match('sites', incoming, sites, parent_id=8).zone == 'new'
    assert M.match('sites', incoming, sites).zone == 'human_review'
    assert M.match('sites', {**incoming,'address':'14 rue des Lilas'}, sites, parent_id=7).zone != 'auto'


def test_equipment_serial_conflict_and_missing():
    existing = [dict(id=1,site_id=7,serial_number='ABC-123',product_id=5)]
    assert M.match('equipment', existing[0], existing,parent_id=7).entity_id == 1
    assert M.match('equipment',{**existing[0],'serial_number':'ABC-124'},existing,parent_id=7).zone == 'new'
    assert M.match('equipment',dict(product_id=5),existing,parent_id=7).zone == 'human_review'
    refs = {('a','equipment','E1'):1}
    assert M.match('equipment',dict(equipment_source_id='E1'),existing,parent_id=9,namespace='a',references=refs).zone == 'human_review'


def test_intervention_candidates_do_not_merge_diagnostic_and_repair():
    rows = [dict(id=1,site_id=7,scheduled_date='2025-02-03',description='Diagnostic panne')]
    assert M.match('interventions',dict(scheduled_date='2025-02-03',description='Diagnostic'),rows,parent_id=7).zone == 'human_review'
    assert M.match('interventions',dict(scheduled_date='2025-02-10',description='Réparation'),rows,parent_id=7).zone == 'new'


@pytest.mark.parametrize('score,zone', [(0,'new'),(79.9,'new'),(80,'human_review'),(94.9,'human_review'),(95,'auto'),(100,'auto')])
def test_thresholds(score,zone):
    assert M.classify(score) == zone


def test_reject_bad_configuration():
    with pytest.raises(ValueError): MultiLevelMatcher(auto_threshold=70,review_threshold=80)
    with pytest.raises(ValueError): M.classify(float('nan'))


def test_pack_duplicate_clients():
    from pathlib import Path
    from app.importers import ExcelReader, FormatDetector, ImportKind, Validator
    path = Path(__file__).parent / 'fixtures/excel/01_clients_sites_equipements.xlsx'
    frame = ExcelReader().read(path, 'Clients')
    rows = Validator().validate(frame, FormatDetector().detect(list(frame.columns), ImportKind.CLIENTS), ImportKind.CLIENTS).records
    assert M.match('clients', rows[4]['normalized'], [{**rows[0]['normalized'], 'id':1}]).zone == 'human_review'
