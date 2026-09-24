"""INT-98: real fixture formats, conservative validation, read-only provenance."""
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from openpyxl import Workbook
import pandas as pd
import pytest

from app.importers import ExcelReader, FormatDetector, ImportKind, Normalizer, Validator

FIXTURES = Path(__file__).parent / 'fixtures/excel'


def analyze(filename, kind, sheet=0, **options):
    reader = ExcelReader()
    frame = reader.read(FIXTURES / filename, sheet, source_namespace='fictif-dg')
    mapping = FormatDetector().detect(list(frame.columns), kind)
    return frame, Validator().validate(frame, mapping, kind, **options)


def codes(record):
    return {e['code'] for e in record['anomalies']}


def test_clients_and_missing_phone_are_traceable():
    frame, result = analyze('01_clients_sites_equipements.xlsx', ImportKind.CLIENTS, 'Clients')
    assert result.total == 6
    assert len(result.valid) == 4
    assert result.records[0]['normalized']['full_name'] == 'jean dupont'
    assert result.records[0]['normalized']['phone'] == '0612345678'
    assert 'DUPLICATE_REQUIRES_REVIEW' in codes(result.records[4])
    missing = result.records[5]
    assert {'MISSING_PHONE', 'MISSING_ADDRESS'} <= codes(missing)
    assert missing['source']['row'] == 7
    assert missing['source']['sheet'] == 'Clients'
    assert missing['original']['Nom'] == 'Bernard'
    assert missing['normalized']['phone'] is None
    assert len(result.records) == result.total
    json.dumps(result.to_dict(), allow_nan=False)
    assert frame.iloc[0]['Telephone'] == '06 12 34 56 78'


def test_certain_association_warns_without_filling_missing_phone():
    _, result = analyze('01_clients_sites_equipements.xlsx', ImportKind.CLIENTS, 'Clients',
                        confirmed_existing_clients={7: 42})
    record = result.records[-1]
    assert record['disposition'] == 'candidate'
    assert record['proposals']['associate_client_id'] == 42
    assert all(e['severity'] == 'warning' for e in record['anomalies'])
    assert record['normalized']['phone'] is None
    assert result.total == 6 and result.error_count == 1


def test_site_and_equipment_anomalies():
    _, sites = analyze('01_clients_sites_equipements.xlsx', ImportKind.SITES, 'Sites')
    assert sites.records[2]['normalized']['site_address'] == '17 rue des Écoles'
    assert sites.records[2]['proposals']['site_name'] == '17 rue des Écoles'
    assert 'MISSING_SITE_ADDRESS' in codes(sites.records[-1])
    _, equipment = analyze('01_clients_sites_equipements.xlsx', ImportKind.EQUIPMENT, 'Equipements')
    assert 'MISSING_SERIAL_NUMBER' in codes(equipment.records[2])
    assert equipment.records[2]['normalized']['serial_number'] is None
    assert equipment.records[0]['normalized']['lifecycle_status'] == 'ACTIVE'
    assert equipment.records[3]['normalized']['lifecycle_status'] == 'REPLACED'
    assert 'REPLACEMENT_REQUIRES_REVIEW' in codes(equipment.records[4])
    assert all(r['proposals']['product_id'] is None for r in equipment.records)


def test_intervention_null_equipment_and_invalid_date():
    _, result = analyze('02_interventions_2018_2025.xlsx', ImportKind.INTERVENTIONS)
    diagnostic = result.records[5]
    assert diagnostic['normalized']['equipment_source_id'] is None
    assert diagnostic['normalized']['site_source_id'] == 'S003'
    assert 'MISSING_EQUIPMENT_REFERENCE' not in codes(diagnostic)
    invalid = result.records[-1]
    assert {'INVALID_VALUE', 'MISSING_SITE_REFERENCE'} <= codes(invalid)
    assert invalid['original']['Date'] == '31/02/2022'
    assert invalid['normalized']['client_source_id'] == 'C999'
    # Unknown C999 is resolved as ORPHAN by INT-99/100, never guessed here.
    assert result.records[2]['normalized']['intervention_result'] == 'PART_REQUIRED'


def test_legacy_dates_need_explicit_century():
    _, result = analyze('03_export_ancien_format.xlsx', ImportKind.INTERVENTIONS)
    assert result.records[0]['normalized']['scheduled_date'] == '2024-09-15'
    assert 'INVALID_VALUE' in codes(result.records[2])
    _, approved = analyze('03_export_ancien_format.xlsx', ImportKind.INTERVENTIONS,
                          two_digit_year_base=2000)
    assert approved.records[2]['normalized']['scheduled_date'] == '2024-11-04'


def test_csv_latin1_and_source_immutability():
    path = FIXTURES / '04_export_clients_latin1.csv'
    before = sha256(path.read_bytes()).hexdigest()
    frame, result = analyze(path.name, ImportKind.CLIENTS)
    assert frame.attrs['source']['encoding'] == 'latin-1'
    assert frame.attrs['source']['separator'] == ';'
    assert result.records[0]['normalized']['phone'] == '0612345678'
    assert 'MISSING_ADDRESS' in codes(result.records[0])
    assert sha256(path.read_bytes()).hexdigest() == before
    assert len(ExcelReader().sheets(FIXTURES / '01_clients_sites_equipements.xlsx')) == 3


def test_titles_blank_lines_and_excel_dates(tmp_path):
    path = tmp_path / 'title.xlsx'
    book = Workbook(); sheet = book.active
    sheet.append(['Liste de clients']); sheet.append([])
    sheet.append(['Nom', 'Telephone', 'Adresse_facturation'])
    sheet.append(['Élodie', '0612345678', 'Paris']); sheet.append([])
    sheet.append(['Marc', None, 'Lyon']); book.save(path)
    before = path.read_bytes()
    frame = ExcelReader().read(path)
    assert frame.attrs['source']['header_row'] == 3
    assert frame.attrs['source_rows'] == [4, 6]
    preview = ExcelReader().preview(frame)
    assert preview.source_rows == [4, 6]
    assert preview.total_rows == 2
    assert path.read_bytes() == before
    assert Normalizer.date(date(2018, 10, 18)) == '2018-10-18'


def test_context_mapping_and_overrides():
    detector = FormatDetector()
    assert detector.detect(['Type'], ImportKind.EQUIPMENT).fields == {'product_category':'Type'}
    assert detector.detect(['Type'], ImportKind.INTERVENTIONS).fields == {'intervention_type':'Type'}
    assert detector.detect(['Type'], ImportKind.MIXED).unmapped == ['Type']
    assert detector.detect(['Tel','Téléphone'], ImportKind.CLIENTS).fields == {}
    assert detector.detect(['Contact'], ImportKind.CLIENTS, {'phone':'Contact'}).overridden
    with pytest.raises(ValueError):
        detector.detect(['Contact'], ImportKind.CLIENTS, {'phone':'Absent'})


@pytest.mark.parametrize('value', ['31/02/2022', '04/11/24', 'yesterday', 45200])
def test_invalid_or_ambiguous_dates(value):
    with pytest.raises(ValueError):
        Normalizer.date(value)


@pytest.mark.parametrize('value', ['612345678', '06abc12345678', '000'])
def test_phone_never_invents_digits(value):
    with pytest.raises(ValueError):
        Normalizer.phone(value)


def test_normalization():
    assert Normalizer.phone('+33 6 12 34 56 78') == '0612345678'
    assert Normalizer.phone('0033612345678') == '0612345678'
    assert Normalizer.name(' Élodie  DUPONT ') == 'elodie dupont'
    assert Normalizer.serial_number(' ab-012 ') == 'AB-012'
    assert Normalizer.postal_code(91300.0) == '91300'
    assert Normalizer.text(pd.NA) == ''
    assert Normalizer.date(pd.NaT) is None


def test_products_and_warranty_validation():
    frame = pd.DataFrame([dict(reference='P01', nom_produit='PAC', marque='B', modele='M',
                               categorie='PAC', actif='non', caracteristiques='{"kw":12}')])
    mapping = FormatDetector().detect(list(frame.columns), ImportKind.PRODUCTS)
    result = Validator().validate(frame, mapping, ImportKind.PRODUCTS)
    assert len(result.valid) == 1
    assert result.valid[0]['product_active'] is False
    assert result.valid[0]['product_characteristics'] == {'kw':12}
    frame = pd.DataFrame([{'ID_site':'S1','Debut garantie':'2025-01-01','Fin garantie':'2024-01-01'}])
    result = Validator().validate(frame, FormatDetector().detect(list(frame.columns), ImportKind.EQUIPMENT), ImportKind.EQUIPMENT)
    assert 'INVALID_WARRANTY_RANGE' in codes(result.records[0])


def test_reject_unsupported_and_ambiguous_headers(tmp_path):
    with pytest.raises(ValueError):
        ExcelReader().read(tmp_path / 'legacy.xls')
    path = tmp_path / 'unknown.csv'; path.write_text('A;B\nx;y\n')
    with pytest.raises(ValueError):
        ExcelReader().read(path)
    assert len(ExcelReader().read(path, header_row=1)) == 1
    path.write_text('Nom;Nom\nx;y\n')
    with pytest.raises(ValueError):
        ExcelReader().read(path, header_row=1)


def test_csv_multiline_physical_row_and_formula(tmp_path):
    path = tmp_path / 'multiline.csv'
    path.write_text('Nom;Telephone;Adresse_facturation\n"Jean\nDupont";0612345678;Paris\nMarc;=1+1;Lyon\n')
    frame = ExcelReader().read(path)
    assert frame.attrs['source_rows'] == [2, 4]
    result = Validator().validate(frame, FormatDetector().detect(list(frame.columns), ImportKind.CLIENTS), ImportKind.CLIENTS)
    assert result.records[1]['source']['row'] == 4
    assert 'INVALID_VALUE' in codes(result.records[1])


def test_unmapped_values_lengths_and_original_are_preserved():
    frame = pd.DataFrame([{'Nom':'A' * 256, 'Telephone':'0612345678',
                           'Adresse_facturation':'Paris', 'Colonne inconnue':'à conserver'}])
    result = Validator().validate(frame, FormatDetector().detect(list(frame.columns), ImportKind.CLIENTS), ImportKind.CLIENTS)
    record = result.records[0]
    assert {'VALUE_TOO_LONG', 'UNMAPPED_COLUMN'} <= codes(record)
    anomaly = next(e for e in record['anomalies'] if e['code'] == 'UNMAPPED_COLUMN')
    assert anomaly['original_value'] == 'à conserver'
    assert result.valid == []


def test_report_counts_sheet_coordinates_and_excludes_warnings():
    from app.importers import ImportReport, RowError, ErrorStatus
    report = ImportReport(filename='multi.xlsx', file_hash='a' * 64)
    report.add_errors([
        RowError(row=2, source_sheet='Clients', status=ErrorStatus.VALIDATION_ERROR, error='x'),
        RowError(row=2, source_sheet='Sites', status=ErrorStatus.VALIDATION_ERROR, error='x'),
        RowError(row=3, source_sheet='Sites', severity='warning', status=ErrorStatus.VALIDATION_ERROR, error='x'),
    ])
    assert report.error_count == 2
