from context.infrastructure.repositories.column_contract import ColumnUnitOfWork
from context.infrastructure.repositories.database_contract import DatabaseUnitOfWork
from context.infrastructure.repositories.index_contract import IndexUnitOfWork
from context.infrastructure.repositories.relationship_contract import RelationshipUnitOfWork
from context.infrastructure.repositories.table_contract import TableUnitOfWork


class SqlExportUnitOfWork(
    DatabaseUnitOfWork,
    TableUnitOfWork,
    ColumnUnitOfWork,
    IndexUnitOfWork,
    RelationshipUnitOfWork,
):
    """Repositories needed to read a whole ER model of one database."""
