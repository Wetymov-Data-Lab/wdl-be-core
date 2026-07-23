from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from wdl_shared.schemas.engine.enums.database import (
    ColumnType,
    DataBaseName,
    IndexType,
    ReferentialAction,
    RelationshipCardinality,
    SortOrder,
)

from wdl_be_core.infrastructure.database.base import Base
from wdl_be_core.infrastructure.database.models.mixins import AuditMixin, CanvasPositionMixin


class Databases(AuditMixin, Base):
    """Database diagram model."""

    __tablename__ = "databases"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_databases_project_id_name"),
    )

    __model_permissions__ = [
        ("create", "Разрешает создание объекта Database"),
        ("read", "Разрешает просмотр объекта Database"),
        ("update", "Разрешает редактирование объекта Database"),
        ("delete", "Разрешает удаление объекта Database"),
    ]

    id:             Mapped[UUID]         = mapped_column(Uuid, primary_key=True)
    name:           Mapped[str]          = mapped_column(String(255), nullable=False)
    project_id:     Mapped[UUID]         = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type:           Mapped[DataBaseName] = mapped_column(String(50), nullable=False)
    notice:         Mapped[str | None]   = mapped_column(String(255), nullable=True)
    default_schema: Mapped[str | None]   = mapped_column(String(255), nullable=True)
    charset:        Mapped[str | None]   = mapped_column(String(64), nullable=True)
    collation:      Mapped[str | None]   = mapped_column(
        "collation_name",
        String(128),
        nullable=True,
    )


class Tables(AuditMixin, CanvasPositionMixin, Base):
    """Database table and its canvas placement."""

    __tablename__ = "tables"
    __table_args__ = (
        UniqueConstraint(
            "database_id",
            "schema_name",
            "name",
            name="uq_tables_database_schema_name",
        ),
        CheckConstraint(
            "color IS NULL OR color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_tables_color",
        ),
        CheckConstraint("width IS NULL OR width > 0", name="ck_tables_width"),
        CheckConstraint("sort_order >= 0", name="ck_tables_sort_order"),
    )

    __model_permissions__ = [
        ("create", "Разрешает создание объекта Table"),
        ("read", "Разрешает просмотр объекта Table"),
        ("update", "Разрешает редактирование объекта Table"),
        ("delete", "Разрешает удаление объекта Table"),
    ]

    id:           Mapped[UUID]       = mapped_column(Uuid, primary_key=True)
    name:         Mapped[str]        = mapped_column(String(255), nullable=False)
    database_id:  Mapped[UUID]       = mapped_column(
        Uuid,
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schema_name:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    description:  Mapped[str | None] = mapped_column(String(255), nullable=True)
    notice:       Mapped[str | None] = mapped_column(String(255), nullable=True)
    color:        Mapped[str | None] = mapped_column(String(7), nullable=True)
    width:      Mapped[float | None] = mapped_column(Float, nullable=True)
    is_collapsed: Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    sort_order:   Mapped[int]        = mapped_column(Integer, nullable=False, default=0)


class Columns(AuditMixin, Base):
    """Column definition shown inside a database table."""

    __tablename__ = "columns"
    __table_args__ = (
        UniqueConstraint("table_id", "name", name="uq_columns_table_id_name"),
        CheckConstraint("length IS NULL OR length > 0", name="ck_columns_length"),
        CheckConstraint("precision IS NULL OR precision > 0", name="ck_columns_precision"),
        CheckConstraint("scale IS NULL OR scale >= 0", name="ck_columns_scale"),
        CheckConstraint(
            "precision IS NULL OR scale IS NULL OR scale <= precision",
            name="ck_columns_scale_precision",
        ),
        CheckConstraint(
            "array_dimensions >= 0 AND array_dimensions <= 8",
            name="ck_columns_array_dimensions",
        ),
        CheckConstraint("sort_order >= 0", name="ck_columns_sort_order"),
    )

    __model_permissions__ = [
        ("create", "Разрешает создание объекта Column"),
        ("read", "Разрешает просмотр объекта Column"),
        ("update", "Разрешает редактирование объекта Column"),
        ("delete", "Разрешает удаление объекта Column"),
    ]

    id:               Mapped[UUID]       = mapped_column(Uuid, primary_key=True)
    name:             Mapped[str]        = mapped_column(String(255), nullable=False)
    table_id:         Mapped[UUID]       = mapped_column(
        Uuid,
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type:             Mapped[ColumnType] = mapped_column(String(50), nullable=False)
    custom_type:      Mapped[str | None] = mapped_column(String(255), nullable=True)
    length:           Mapped[int | None] = mapped_column(Integer, nullable=True)
    precision:        Mapped[int | None] = mapped_column(Integer, nullable=True)
    scale:            Mapped[int | None] = mapped_column(Integer, nullable=True)
    array_dimensions: Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    nullable:         Mapped[bool]       = mapped_column(Boolean, nullable=False, default=True)
    primary_key:      Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    unique:           Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    auto_increment:   Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    unsigned:         Mapped[bool]       = mapped_column(Boolean, nullable=False, default=False)
    default:          Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    check:            Mapped[str | None] = mapped_column(String(4_000), nullable=True)
    enum_values:      Mapped[list[str]]  = mapped_column(JSON, nullable=False, default=list)
    sort_order:       Mapped[int]        = mapped_column(Integer, nullable=False, default=0)
    notice:           Mapped[str | None] = mapped_column(String(255), nullable=True)


class DiagramIndexes(AuditMixin, Base):
    """Named or anonymous table index."""

    __tablename__ = "diagram_indexes"
    __table_args__ = (
        UniqueConstraint("table_id", "name", name="uq_diagram_indexes_table_id_name"),
    )

    id:       Mapped[UUID]       = mapped_column(Uuid, primary_key=True)
    table_id: Mapped[UUID]       = mapped_column(
        Uuid,
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name:     Mapped[str | None] = mapped_column(String(255), nullable=True)
    type:     Mapped[IndexType]  = mapped_column(
        String(32),
        nullable=False,
        default=IndexType.INDEX,
    )
    method:   Mapped[str | None] = mapped_column(String(64), nullable=True)
    where:    Mapped[str | None] = mapped_column(String(4_000), nullable=True)


class DiagramIndexColumns(Base):
    """Ordered column membership of a diagram index."""

    __tablename__ = "diagram_index_columns"
    __table_args__ = (
        UniqueConstraint("index_id", "column_id", name="uq_index_columns_index_column"),
        UniqueConstraint("index_id", "position", name="uq_index_columns_index_position"),
        CheckConstraint("position >= 0", name="ck_index_columns_position"),
    )

    id:         Mapped[UUID]      = mapped_column(Uuid, primary_key=True)
    index_id:   Mapped[UUID]      = mapped_column(
        Uuid,
        ForeignKey("diagram_indexes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_id:  Mapped[UUID]      = mapped_column(
        Uuid,
        ForeignKey("columns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[SortOrder] = mapped_column(
        String(8),
        nullable=False,
        default=SortOrder.ASC,
    )
    position:   Mapped[int]       = mapped_column(Integer, nullable=False)


class Relationships(AuditMixin, Base):
    """Foreign-key relationship and its visual representation."""

    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint("database_id", "name", name="uq_relationships_database_id_name"),
    )

    id:                 Mapped[UUID]                    = mapped_column(Uuid, primary_key=True)
    database_id:        Mapped[UUID]                    = mapped_column(
        Uuid,
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name:               Mapped[str | None]              = mapped_column(String(255), nullable=True)
    source_table_id:    Mapped[UUID]                    = mapped_column(
        Uuid,
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_table_id:    Mapped[UUID]                    = mapped_column(
        Uuid,
        ForeignKey("tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_cardinality: Mapped[RelationshipCardinality] = mapped_column(
        String(32),
        nullable=False,
        default=RelationshipCardinality.ZERO_OR_MANY,
    )
    target_cardinality: Mapped[RelationshipCardinality] = mapped_column(
        String(32),
        nullable=False,
        default=RelationshipCardinality.EXACTLY_ONE,
    )
    on_delete:          Mapped[ReferentialAction]       = mapped_column(
        String(32),
        nullable=False,
        default=ReferentialAction.NO_ACTION,
    )
    on_update:          Mapped[ReferentialAction]       = mapped_column(
        String(32),
        nullable=False,
        default=ReferentialAction.NO_ACTION,
    )
    waypoints:          Mapped[list[dict[str, float]]]  = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )


class RelationshipColumns(Base):
    """Source/target column mapping of a relationship."""

    __tablename__ = "relationship_columns"
    __table_args__ = (
        UniqueConstraint(
            "relationship_id",
            "source_column_id",
            "target_column_id",
            name="uq_relationship_columns_mapping",
        ),
    )

    id:               Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    relationship_id:  Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("relationships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_column_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("columns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_column_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("columns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
