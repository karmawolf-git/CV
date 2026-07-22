from __future__ import annotations

from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    institution: str
    degree: str | None = None
    year: str | None = None


class LicenseItem(BaseModel):
    name: str
    year: str | None = None


class CareerItem(BaseModel):
    org: str
    role: str | None = None
    period: str | None = None


class Doctor(BaseModel):
    hospital: str
    hospital_url: str
    name: str
    position: str | None = None
    department: str | None = None
    specialty: list[str] = Field(default_factory=list)
    profile_url: str | None = None
    photo_url: str | None = None
    education: list[EducationItem] = Field(default_factory=list)
    licenses: list[LicenseItem] = Field(default_factory=list)
    career: list[CareerItem] = Field(default_factory=list)
    training: list[CareerItem] = Field(default_factory=list)  # 연수
    societies: list[str] = Field(default_factory=list)  # 학회활동
    awards: list[str] = Field(default_factory=list)  # 수상이력
    research: list[str] = Field(default_factory=list)  # 연구분야
    publications: list[str] = Field(default_factory=list)  # 논문·저서
    source_url: str
    crawled_at: str


class Hospital(BaseModel):
    id: str
    name: str
    base_url: str
    doctor_index_url: str
    notes: str | None = None
