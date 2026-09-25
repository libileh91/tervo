"""Capture immutable source rows for a manifest; no database or web dependency."""
from pathlib import Path
from tempfile import TemporaryDirectory
from app.importers.excel_reader import ExcelReader
from app.importers.format_detector import FormatDetector, ImportKind
from app.importers.validators import Validator


def read_sources(content: bytes, filename: str, namespace: str, selections: list[dict]):
    if not selections:
        raise ValueError('Sélectionner au moins une feuille et sa nature')
    if len(content) > 10 * 1024 * 1024:
        raise ValueError('Fichier supérieur à 10 Mio')
    if Path(filename).suffix.lower() not in {'.xlsx', '.csv'}:
        raise ValueError('Format non supporté')
    results, seen = [], set()
    with TemporaryDirectory(prefix='tervo-import-') as folder:
        path = Path(folder) / ('source' + Path(filename).suffix.lower())
        path.write_bytes(content)
        for selection in selections:
            kind = ImportKind(selection['kind'])
            if kind == ImportKind.MIXED:
                raise ValueError('Choisir une nature explicite par sélection')
            options = {k:selection[k] for k in ('sheet','header_row','encoding','separator') if k in selection}
            frame = ExcelReader().read(path, source_namespace=namespace, **options)
            frame.attrs['source']['file'] = filename
            if path.suffix == '.csv':
                frame.attrs['source']['sheet'] = Path(filename).stem
            mapping = FormatDetector().detect(list(frame.columns), kind, selection.get('mapping'))
            validated = Validator().validate(frame, mapping, kind, two_digit_year_base=selection.get('two_digit_year_base'))
            for record in validated.records:
                key = f"{record['source']['sheet']}:{record['source']['row']}:{kind.value}"
                if key in seen:
                    raise ValueError('Sélection de ligne dupliquée')
                seen.add(key)
                results.append(dict(key=key, kind=kind.value, mapping=mapping.to_dict(), **record))
    return results
