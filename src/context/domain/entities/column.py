from dataclasses import dataclass, fields
from datetime import datetime
from uuid import UUID, uuid4

from wdl_shared.schemas.engine.enums.database import ColumnType

from context.domain.entities.base import Entity


@dataclass(frozen=True, slots=True, kw_only=True)
class ColumnAttributes:
    """Mutable attributes of a table column."""

    name: str
    type: ColumnType
    custom_type: str | None
    length: int | None
    precision: int | None
    scale: int | None
    array_dimensions: int
    nullable: bool
    primary_key: bool
    unique: bool
    auto_increment: bool
    unsigned: bool
    default: str | None
    check: str | None
    enum_values: list[str]
    sort_order: int
    notice: str | None


@dataclass(eq=False, kw_only=True)
class Column(Entity[UUID]):
    table_id: UUID
    name: str
    type: ColumnType
    custom_type: str | None
    length: int | None
    precision: int | None
    scale: int | None
    array_dimensions: int
    nullable: bool
    primary_key: bool
    unique: bool
    auto_increment: bool
    unsigned: bool
    default: str | None
    check: str | None
    enum_values: list[str]
    sort_order: int
    notice: str | None
    author_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        table_id: UUID,
        attributes: ColumnAttributes,
        author_id: UUID,
        created_at: datetime,
        column_id: UUID | None = None,
    ) -> "Column":
        return cls(
            id=column_id or uuid4(),
            table_id=table_id,
            name=attributes.name,
            type=attributes.type,
            custom_type=attributes.custom_type,
            length=attributes.length,
            precision=attributes.precision,
            scale=attributes.scale,
            array_dimensions=attributes.array_dimensions,
            nullable=attributes.nullable,
            primary_key=attributes.primary_key,
            unique=attributes.unique,
            auto_increment=attributes.auto_increment,
            unsigned=attributes.unsigned,
            default=attributes.default,
            check=attributes.check,
            enum_values=list(attributes.enum_values),
            sort_order=attributes.sort_order,
            notice=attributes.notice,
            author_id=author_id,
            created_at=created_at,
        )

    def update(self, *, attributes: ColumnAttributes, updated_at: datetime) -> None:
        for attribute in fields(attributes):
            setattr(self, attribute.name, getattr(attributes, attribute.name))
        self.enum_values = list(attributes.enum_values)
        self.updated_at = updated_at
