"""Pure canonicalization helpers; original values are retained by the reader/validator."""
from datetime import date, datetime
import math
import re
import unicodedata
import pandas as pd


class Normalizer:
    COUNTRY_PREFIXES = ("+33", "0033", "33")

    @staticmethod
    def fold_accents(value: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFKD", value)
                       if not unicodedata.combining(c))

    @staticmethod
    def text(value: object) -> str:
        if value is None or value is pd.NA or value is pd.NaT or (isinstance(value, float) and math.isnan(value)):
            return ""
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return " ".join(str(value).split())

    @staticmethod
    def name(value: object) -> str:
        return Normalizer.fold_accents(Normalizer.text(value)).casefold()

    @staticmethod
    def phone(value: object) -> str:
        raw = Normalizer.text(value)
        if not raw:
            return ""
        phone = re.sub(r"[\s.()\-]", "", raw)
        # Never silently strip letters or reconstruct a lost leading zero.
        if not re.fullmatch(r"\+?\d+", phone):
            raise ValueError("Téléphone invalide")
        for prefix in Normalizer.COUNTRY_PREFIXES:
            if phone.startswith(prefix) and len(phone[len(prefix):]) == 9:
                phone = "0" + phone[len(prefix):]
                break
        if not re.fullmatch(r"0\d{9}|\+[1-9]\d{7,14}", phone):
            raise ValueError("Téléphone incomplet ou format non reconnu")
        return phone

    @staticmethod
    def email(value: object) -> str:
        return Normalizer.text(value).casefold()

    @staticmethod
    def postal_code(value: object) -> str:
        return Normalizer.text(value)

    @staticmethod
    def serial_number(value: object) -> str:
        # Preserve punctuation: AB-12 and AB12 need not identify the same device.
        return Normalizer.text(value).upper()

    @staticmethod
    def date(value: object, *, two_digit_year_base: int | None = None) -> str | None:
        if value is None or Normalizer.text(value) == "":
            return None
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        text = Normalizer.text(value)
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                parsed = datetime.strptime(text, fmt)
                # strptime accepts short ISO years for some formats; require 4 digits.
                year = text.split('-')[0] if fmt == "%Y-%m-%d" else re.split(r"[/.-]", text)[-1]
                if len(year) == 4:
                    return parsed.date().isoformat()
            except ValueError:
                pass
        match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2})", text)
        if match and two_digit_year_base is not None:
            if two_digit_year_base % 100:
                raise ValueError("Le siècle doit être un multiple de 100")
            day, month, year = map(int, match.groups())
            return date(two_digit_year_base + year, month, day).isoformat()
        if match:
            raise ValueError("Année sur deux chiffres : siècle à confirmer")
        raise ValueError("Date impossible ou format non reconnu")

    warranty_date = date
