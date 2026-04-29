from pydantic import BaseModel, Field, field_validator


class NaturalLanguageQuery(BaseModel):
    q: str = Field(..., min_length=1)
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=50)

    @field_validator("q")
    @classmethod
    def strip_query(cls, v: str) -> str:
        return v.strip()
