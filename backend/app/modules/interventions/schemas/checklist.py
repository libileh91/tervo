"""Checklist template and snapshot API contract."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, StrictBool, StrictInt, field_validator, model_validator

from app.modules.interventions.schemas.intervention import ChecklistItemRef


class TemplateItem(BaseModel):
    model_config = {"extra": "forbid"}
    label: str = Field(min_length=1, max_length=255)
    category: Literal["pre_intervention", "post_intervention"]
    position: StrictInt = Field(ge=0)

    @field_validator("label")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("label must be nonblank")
        return value


class ChecklistTemplateCreate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=255)
    intervention_type: str = Field(min_length=1, max_length=100)
    active: StrictBool = True
    items: list[TemplateItem] = Field(min_length=1)

    @field_validator("name", "intervention_type")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("value must be nonblank")
        return value


class ChecklistTemplateUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str | None = Field(None, min_length=1, max_length=255)
    intervention_type: str | None = Field(None, min_length=1, max_length=100)
    active: StrictBool | None = None
    items: list[TemplateItem] | None = Field(None, min_length=1)

    @field_validator("name", "intervention_type", "active", "items")
    @classmethod
    def not_null_or_blank(cls, value):
        if value is None or isinstance(value, str) and not value.strip():
            raise ValueError("value must not be null or blank")
        return value

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set:
            raise ValueError("at least one template field is required")
        return self


class ChecklistTemplateResponse(ChecklistTemplateCreate):
    id: int
    version: StrictInt = Field(ge=1)
    model_config = {"from_attributes": True}


class InterventionChecklistResponse(BaseModel):
    id: int
    intervention_id: int
    template_id: int | None
    template_name: str
    template_version: int
    created_at: datetime
    items: list[ChecklistItemRef]
    model_config = {"from_attributes": True}
