from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


NonEmptyText = Annotated[str, Field(min_length=1, pattern=r"\S")]
PageNumber = Annotated[int, Field(ge=1, strict=True)]
LocalID = Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$")]


class CVModel(BaseModel):
    # Catch unknown fields instead of silently dropping extracted information.
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SourceReference(CVModel):
    source_pages: list[PageNumber] = Field(default_factory=list)
    source_heading: str | None = None
    source_text: str | None = None


class Table(CVModel):
    caption: str | None = None
    column_headers: list[str] = Field(default_factory=list)
    rows: list[list[str | None]] = Field(default_factory=list)


class ContentBlock(SourceReference):
    type: Literal["paragraph", "bullet", "numbered_item", "table", "other"]
    text: str | None = None
    table: Table | None = None

    @model_validator(mode="after")
    def check_content(self) -> Self:
        if self.type == "table":
            if self.table is None:
                raise ValueError("A table block requires table data.")
        else:
            if self.text is None or not self.text.strip():
                raise ValueError("A non-table block requires nonblank text.")
            if self.table is not None:
                raise ValueError("Table data requires a table block.")
        return self


class AdditionalSection(SourceReference):
    heading: str | None = None
    content: list[ContentBlock] = Field(default_factory=list)
    subsections: list[AdditionalSection] = Field(default_factory=list)


class CVEntry(SourceReference):
    entry_id: LocalID | None = None
    additional_sections: list[AdditionalSection] = Field(default_factory=list)


class DateRange(CVModel):
    raw_text: str | None = None
    start: str | None = None
    end: str | None = None
    is_current: bool | None = None
    duration: str | None = None


class Location(SourceReference):
    raw_text: str | None = None
    label: str | None = None
    address: str | None = None
    postal_code: str | None = None
    city: str | None = None
    region: str | None = None
    country: str | None = None


class ContactMethod(SourceReference):
    type: Literal["email", "phone", "fax", "messaging", "other"]
    value: NonEmptyText
    label: str | None = None
    platform: str | None = None


class Weblink(SourceReference):
    url: NonEmptyText
    label: str | None = None
    type: str | None = None
    platform: str | None = None


class Organization(CVEntry):
    name: str | None = None
    department: str | None = None
    industry: str | None = None
    description: str | None = None
    locations: list[Location] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)


class Proficiency(CVModel):
    type: Literal[
        "text", "stars", "dots", "bars", "percentage", "fraction", "numeric", "other"
    ] | None = None
    raw_value: str | None = None
    value: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    scale_description: str | None = None
    cefr_level: str | None = None

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ValueError("Proficiency minimum exceeds maximum.")
        if self.value is not None:
            if self.minimum is not None and self.value < self.minimum:
                raise ValueError("Proficiency value is below minimum.")
            if self.maximum is not None and self.value > self.maximum:
                raise ValueError("Proficiency value exceeds maximum.")
        return self


class Skill(CVEntry):
    name: NonEmptyText
    category: str | None = None
    proficiency: Proficiency | None = None
    experience_duration: str | None = None
    last_used: str | None = None
    description: str | None = None


class PersonalInformation(CVEntry):
    full_name: str | None = None
    preferred_name: str | None = None
    given_names: str | None = None
    family_name: str | None = None
    professional_titles: list[str] = Field(default_factory=list)
    headline: str | None = None
    current_occupation: str | None = None
    contacts: list[ContactMethod] = Field(default_factory=list)
    locations: list[Location] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)
    date_of_birth: str | None = None
    place_of_birth: str | None = None
    nationalities: list[str] = Field(default_factory=list)
    pronouns: str | None = None
    gender: str | None = None
    marital_status: str | None = None


class Profile(CVEntry):
    type: Literal["summary", "objective", "personal_statement", "other"] | None = None
    heading: str | None = None
    text: NonEmptyText


class Position(CVEntry):
    title: str | None = None
    department: str | None = None
    employment_type: str | None = None
    dates: DateRange | None = None
    locations: list[Location] = Field(default_factory=list)
    work_arrangement: str | None = None
    description: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)


class WorkExperience(CVEntry):
    organization: Organization | None = None
    client: Organization | None = None
    dates: DateRange | None = None
    employment_type: str | None = None
    locations: list[Location] = Field(default_factory=list)
    description: str | None = None
    positions: list[Position] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)


class Project(CVEntry):
    name: str | None = None
    type: str | None = None
    role: str | None = None
    organization: Organization | None = None
    client: Organization | None = None
    dates: DateRange | None = None
    locations: list[Location] = Field(default_factory=list)
    description: str | None = None
    objectives: list[str] = Field(default_factory=list)
    contributions: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)
    related_experience_ids: list[LocalID] = Field(default_factory=list)
    related_position_ids: list[LocalID] = Field(default_factory=list)


class Grade(CVModel):
    raw_value: NonEmptyText
    scale: str | None = None
    rank: str | None = None


class Thesis(CVEntry):
    title: str | None = None
    type: str | None = None
    description: str | None = None
    supervisors: list[str] = Field(default_factory=list)
    grade: Grade | None = None
    weblinks: list[Weblink] = Field(default_factory=list)


class Education(CVEntry):
    institution: Organization | None = None
    degree: str | None = None
    qualification_level: str | None = None
    fields_of_study: list[str] = Field(default_factory=list)
    specializations: list[str] = Field(default_factory=list)
    dates: DateRange | None = None
    status: str | None = None
    study_mode: str | None = None
    locations: list[Location] = Field(default_factory=list)
    description: str | None = None
    coursework: list[str] = Field(default_factory=list)
    grade: Grade | None = None
    distinctions: list[str] = Field(default_factory=list)
    theses: list[Thesis] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)


class Certification(CVEntry):
    name: NonEmptyText
    type: str | None = None
    issuer: Organization | None = None
    date_achieved: str | None = None
    expiration_date: str | None = None
    credential_id: str | None = None
    status: str | None = None
    description: str | None = None
    grade: Grade | None = None
    skills: list[Skill] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)


class Training(CVEntry):
    name: NonEmptyText
    provider: Organization | None = None
    dates: DateRange | None = None
    duration: str | None = None
    delivery_mode: str | None = None
    locations: list[Location] = Field(default_factory=list)
    description: str | None = None
    topics: list[str] = Field(default_factory=list)
    grade: Grade | None = None
    skills: list[Skill] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)


class Language(CVEntry):
    name: NonEmptyText
    is_native: bool | None = None
    overall: Proficiency | None = None
    understanding: Proficiency | None = None
    listening: Proficiency | None = None
    reading: Proficiency | None = None
    speaking: Proficiency | None = None
    spoken_interaction: Proficiency | None = None
    spoken_production: Proficiency | None = None
    writing: Proficiency | None = None
    qualifications: list[str] = Field(default_factory=list)
    description: str | None = None


class Award(CVEntry):
    name: NonEmptyText
    issuer: Organization | None = None
    date: str | None = None
    category: str | None = None
    description: str | None = None
    amount: str | None = None
    weblinks: list[Weblink] = Field(default_factory=list)


class PublicationIdentifier(CVModel):
    type: NonEmptyText
    value: NonEmptyText


class Publication(CVEntry):
    title: NonEmptyText
    type: str | None = None
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    publisher: Organization | None = None
    date: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    status: str | None = None
    identifiers: list[PublicationIdentifier] = Field(default_factory=list)
    description: str | None = None
    weblinks: list[Weblink] = Field(default_factory=list)


class Presentation(CVEntry):
    title: NonEmptyText
    event: str | None = None
    organizer: Organization | None = None
    role: str | None = None
    date: str | None = None
    locations: list[Location] = Field(default_factory=list)
    co_presenters: list[str] = Field(default_factory=list)
    description: str | None = None
    weblinks: list[Weblink] = Field(default_factory=list)


class Membership(CVEntry):
    organization: Organization | None = None
    role: str | None = None
    dates: DateRange | None = None
    membership_id: str | None = None
    description: str | None = None


class Interest(CVEntry):
    name: NonEmptyText
    category: str | None = None
    description: str | None = None


class Reference(CVEntry):
    name: str | None = None
    title: str | None = None
    organization: Organization | None = None
    relationship: str | None = None
    contacts: list[ContactMethod] = Field(default_factory=list)
    weblinks: list[Weblink] = Field(default_factory=list)
    statement: str | None = None


class DrivingLicense(CVEntry):
    category: NonEmptyText
    country: str | None = None
    date_issued: str | None = None
    expiration_date: str | None = None
    restrictions: str | None = None


class WorkAuthorization(CVEntry):
    country: str | None = None
    status: str | None = None
    valid_until: str | None = None
    description: str | None = None


class SecurityClearance(CVEntry):
    level: NonEmptyText
    authority: str | None = None
    status: str | None = None
    dates: DateRange | None = None
    description: str | None = None


class Availability(CVEntry):
    raw_text: str | None = None
    start_date: str | None = None
    notice_period: str | None = None
    hours: str | None = None


class EmploymentPreferences(CVEntry):
    desired_roles: list[str] = Field(default_factory=list)
    desired_locations: list[Location] = Field(default_factory=list)
    employment_types: list[str] = Field(default_factory=list)
    work_arrangements: list[str] = Field(default_factory=list)
    willingness_to_relocate: str | None = None
    willingness_to_travel: str | None = None
    desired_compensation: str | None = None
    availability: Availability | None = None
    work_authorizations: list[WorkAuthorization] = Field(default_factory=list)
    driving_licenses: list[DrivingLicense] = Field(default_factory=list)
    security_clearances: list[SecurityClearance] = Field(default_factory=list)


class Statement(CVEntry):
    type: str | None = None
    text: NonEmptyText
    date: str | None = None
    location: str | None = None
    signatory: str | None = None


def _iter_entries(value: Any) -> Iterator[CVEntry]:
    if isinstance(value, CVEntry):
        yield value
    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            yield from _iter_entries(getattr(value, name))
    elif isinstance(value, list):
        for item in value:
            yield from _iter_entries(item)


class RawCV(CVModel):
    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    profiles: list[Profile] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    training: list[Training] = Field(default_factory=list)
    awards: list[Award] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    presentations: list[Presentation] = Field(default_factory=list)
    volunteering: list[WorkExperience] = Field(default_factory=list)
    military_service: list[WorkExperience] = Field(default_factory=list)
    memberships: list[Membership] = Field(default_factory=list)
    interests: list[Interest] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    employment_preferences: EmploymentPreferences = Field(default_factory=EmploymentPreferences)
    weblinks: list[Weblink] = Field(default_factory=list)
    declarations: list[Statement] = Field(default_factory=list)
    additional_sections: list[AdditionalSection] = Field(default_factory=list)

    @model_validator(mode="after")
    def check_relationships(self) -> Self:
        seen: set[str] = set()
        for entry in _iter_entries(self):
            if entry.entry_id is not None:
                if entry.entry_id in seen:
                    raise ValueError(f"Duplicate entry_id: {entry.entry_id}")
                seen.add(entry.entry_id)

        experiences = self.work_experience + self.volunteering + self.military_service
        experience_ids = {
            entry.entry_id for entry in experiences if entry.entry_id is not None
        }
        position_ids = {
            position.entry_id
            for entry in experiences
            for position in entry.positions
            if position.entry_id is not None
        }
        for project in self.projects:
            for reference in project.related_experience_ids:
                if reference not in experience_ids:
                    raise ValueError(f"Unknown project experience reference: {reference}")
            for reference in project.related_position_ids:
                if reference not in position_ids:
                    raise ValueError(f"Unknown project position reference: {reference}")
        return self
