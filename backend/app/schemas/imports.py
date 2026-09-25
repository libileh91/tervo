"""Admin import contracts. Decisions are explicit and scoped to source row keys."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from app.importers.format_detector import ImportKind


class SheetSelection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sheet: int | str = 0
    kind: ImportKind
    header_row: int | None = Field(None, ge=1)
    encoding: Literal['utf-8','utf-8-sig','latin-1','cp1252'] | None = None
    separator: Literal[';',',','\t'] | None = None
    two_digit_year_base: Literal[1900,2000] | None = None
    mapping: dict[str,str] = Field(default_factory=dict)


class ImportDecision(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    action: Literal['create','associate','ignore','review']
    entity_id: int | None = Field(None, gt=0)
    associate_source_id: str | None = Field(None, min_length=1, max_length=255)
    corrections: dict[str, JsonValue] = Field(default_factory=dict)
    note: str = Field(min_length=1, max_length=2000)


    @model_validator(mode='after')
    def check_association_target(self):
        targets = int(self.entity_id is not None) + int(self.associate_source_id is not None)
        if self.action == 'associate' and targets != 1:
            raise ValueError('Choisir exactement une cible : entity_id ou associate_source_id')
        if self.action != 'associate' and targets:
            raise ValueError('Une cible est réservée à une association')
        return self


class ValidateImport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    batch_id: int = Field(gt=0)
    selections: list[SheetSelection] | None = None
    decisions: dict[str, ImportDecision] = Field(default_factory=dict)


class ExecuteImport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    batch_id: int = Field(gt=0)
    plan_token: str = Field(pattern=r'^[a-f0-9]{64}$')


class ImportRowResponse(BaseModel):
    key: str
    kind: str
    source: dict[str, JsonValue]
    original: dict[str, JsonValue]
    normalized: dict[str, JsonValue]
    op: str | None = None
    anomalies: list[dict[str, JsonValue]] = Field(default_factory=list)
    proposals: dict[str, JsonValue] = Field(default_factory=dict)
    match: dict[str, JsonValue] | None = None

    model_config = ConfigDict(extra='allow')


class ImportBatchResponse(BaseModel):
    id: int
    filename: str
    source_namespace: str
    file_hash: str
    status: str
    revision: int
    plan_token: str | None
    selections: list[SheetSelection]
    total: int
    counts: dict[str,int]
    items: list[ImportRowResponse]
    page: int = 1
    page_size: int = 100


class ImportBatchSummary(BaseModel):
    id: int
    filename: str
    source_namespace: str
    file_hash: str
    status: str
    revision: int
    total: int
    counts: dict[str, int]


class ImportBatchListResponse(BaseModel):
    items: list[ImportBatchSummary]
    total: int
    page: int
    page_size: int
    pages: int


class ImportErrorResponse(BaseModel):
    id: int
    revision: int
    key: str
    code: str
    severity: str
    message: str
    source: dict[str, JsonValue]
    original: dict[str, JsonValue]


class ImportErrorListResponse(BaseModel):
    items: list[ImportErrorResponse]
    total: int
    page: int
    page_size: int
    pages: int
