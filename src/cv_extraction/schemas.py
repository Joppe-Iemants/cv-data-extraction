from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

NonEmptyText = Annotated[str, Field(min_length=1, pattern=r"\S")]
PageNumber = Annotated[int, Field(ge=1, strict=True)]


class CVModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class CVEntry(CVModel):
    # Record-level provenance; empty when reliable page labels are unavailable.
    source_pages: list[PageNumber] = Field(default_factory=list)


class DateRange(CVModel):
    start: NonEmptyText | None = None
    end: NonEmptyText | None = None
    duration: NonEmptyText | None = None


class Weblink(CVModel):
    url: NonEmptyText
    platform: NonEmptyText | None = None


class PersonalInformation(CVEntry):
    full_name: NonEmptyText | None = None
    headline: NonEmptyText | None = None
    emails: list[NonEmptyText] = Field(default_factory=list)
    phones: list[NonEmptyText] = Field(default_factory=list)
    location: NonEmptyText | None = None
    weblinks: list[Weblink] = Field(default_factory=list)
    details: list[NonEmptyText] = Field(default_factory=list)


class Proficiency(CVModel):
    text: NonEmptyText | None = Field(default=None, description="Explicit wording, e.g. Fluent or B2; do not infer.")
    type: Literal["stars", "dots", "bars", "percentage", "fraction", "numeric"] | None = None
    value: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def check_rating(self) -> Self:
        if self.maximum is not None and self.maximum <= 0:
            raise ValueError("Proficiency maximum must be positive.")
        if self.value is not None:
            if self.value < 0:
                raise ValueError("Proficiency value must be nonnegative.")
            if self.maximum is not None and self.value > self.maximum:
                raise ValueError("Proficiency value exceeds maximum.")
        if self.text is None and self.value is None:
            raise ValueError("Proficiency requires explicit text or a numeric value.")
        return self


class Skill(CVEntry):
    name: NonEmptyText
    proficiency: Proficiency | None = None
    details: list[NonEmptyText] = Field(default_factory=list)


class Language(CVEntry):
    name: NonEmptyText
    proficiency: Proficiency | None = None
    # Separate speaking/writing levels, when supplied, remain in details.
    details: list[NonEmptyText] = Field(default_factory=list)


class WorkExperience(CVEntry):
    employer: NonEmptyText | None = None
    role: NonEmptyText | None = None
    client: NonEmptyText | None = None
    dates: DateRange | None = None
    location: NonEmptyText | None = None
    details: list[NonEmptyText] = Field(default_factory=list)
    skills: list[NonEmptyText] = Field(default_factory=list, description="Skills explicitly tied to this position only.")


class Project(CVEntry):
    name: NonEmptyText | None = None
    organization: NonEmptyText | None = None
    client: NonEmptyText | None = None
    role: NonEmptyText | None = None
    dates: DateRange | None = None
    details: list[NonEmptyText] = Field(default_factory=list)
    skills: list[NonEmptyText] = Field(default_factory=list, description="Skills explicitly tied to this project only.")


class Education(CVEntry):
    institution: NonEmptyText | None = None
    qualification: NonEmptyText | None = Field(default=None, description="Full qualification as written, including field of study.")
    dates: DateRange | None = None
    details: list[NonEmptyText] = Field(default_factory=list)


class Certification(CVEntry):
    name: NonEmptyText
    issuer: NonEmptyText | None = None
    date: NonEmptyText | None = None
    details: list[NonEmptyText] = Field(default_factory=list)


class Training(CVEntry):
    name: NonEmptyText
    provider: NonEmptyText | None = None
    dates: DateRange | None = None
    details: list[NonEmptyText] = Field(default_factory=list)


class AdditionalSection(CVEntry):
    heading: NonEmptyText | None = None
    text: NonEmptyText = Field(description="Preserve remaining content in source wording, including bullets and line breaks." )


class RawCV(CVModel):
    personal_information: PersonalInformation = Field(default_factory=PersonalInformation)
    summary: NonEmptyText | None = Field(default=None, description="Existing introductory profile text; do not write a new summary.")
    work_experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    training: list[Training] = Field(default_factory=list)
    additional_sections: list[AdditionalSection] = Field(default_factory=list, description="Other sections only, e.g. publications, references, interests or awards; do not duplicate core facts.")
