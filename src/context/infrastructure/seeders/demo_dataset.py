"""Declarative demo ER models used by the demo seeder.

Every PostgreSQL model here must stay exportable to SQL; the seeder test checks it.
Table names are unique inside a database, so specs reference tables by name only.
"""

from dataclasses import dataclass
from typing import Any

from wdl_shared.schemas.engine.enums.database import (
    ColumnType,
    DataBaseName,
    IndexType,
    ReferentialAction,
)

UUID = ColumnType.UUID
INTEGER = ColumnType.INTEGER
SMALLINT = ColumnType.SMALLINT
BIGINT = ColumnType.BIGINT
VARCHAR = ColumnType.VARCHAR
CHAR = ColumnType.CHAR
TEXT = ColumnType.TEXT
NUMERIC = ColumnType.NUMERIC
BOOLEAN = ColumnType.BOOLEAN
DATE = ColumnType.DATE
TIMESTAMP = ColumnType.TIMESTAMP
JSONB = ColumnType.JSONB
ENUM = ColumnType.ENUM

CASCADE = ReferentialAction.CASCADE
RESTRICT = ReferentialAction.RESTRICT
SET_NULL = ReferentialAction.SET_NULL


@dataclass(frozen=True, slots=True, kw_only=True)
class ColumnSpec:
    name: str
    type: ColumnType
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    array_dimensions: int = 0
    nullable: bool = False
    primary_key: bool = False
    unique: bool = False
    auto_increment: bool = False
    unsigned: bool = False
    default: str | None = None
    check: str | None = None
    enum_values: tuple[str, ...] = ()
    notice: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexSpec:
    name: str
    columns: tuple[str, ...]
    """Column names; a leading ``-`` sorts the column descending."""
    type: IndexType = IndexType.INDEX
    method: str = "btree"
    where: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class TableSpec:
    name: str
    columns: tuple[ColumnSpec, ...]
    schema: str | None = None
    description: str | None = None
    indexes: tuple[IndexSpec, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ForeignKeySpec:
    name: str
    source: str
    """``table.column`` or ``table.column_a,column_b`` for a composite key."""
    target: str
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION


@dataclass(frozen=True, slots=True, kw_only=True)
class GroupSpec:
    name: str
    tables: tuple[str, ...]
    color: str
    """Saturated domain color; its tables use it too, the canvas tints the group fill."""
    cell: tuple[int, int]
    """Column and row of the group on the canvas grid."""
    columns: int = 1
    """How many table columns the group stacks its tables into."""


@dataclass(frozen=True, slots=True, kw_only=True)
class NoteSpec:
    text: str
    group: str
    """The note is placed under this group."""
    color: str = "#FEF08A"


@dataclass(frozen=True, slots=True, kw_only=True)
class DatabaseSpec:
    name: str
    type: DataBaseName
    notice: str
    default_schema: str | None
    tables: tuple[TableSpec, ...]
    foreign_keys: tuple[ForeignKeySpec, ...] = ()
    groups: tuple[GroupSpec, ...] = ()
    notes: tuple[NoteSpec, ...] = ()


def c(name: str, kind: ColumnType, **options: Any) -> ColumnSpec:
    if "enum_values" in options:
        options["enum_values"] = tuple(options["enum_values"])
    return ColumnSpec(name=name, type=kind, **options)


def uuid_pk(name: str = "id") -> ColumnSpec:
    return c(name, UUID, primary_key=True, default="gen_random_uuid()")


def serial_pk(name: str = "id", kind: ColumnType = INTEGER) -> ColumnSpec:
    return c(name, kind, primary_key=True, auto_increment=True)


def created_at(name: str = "created_at") -> ColumnSpec:
    return c(name, TIMESTAMP, default="now()")


def money(name: str, **options: Any) -> ColumnSpec:
    return c(name, NUMERIC, precision=12, scale=2, **options)


def ix(name: str, *columns: str, **options: Any) -> IndexSpec:
    return IndexSpec(name=name, columns=columns, **options)


def ux(name: str, *columns: str) -> IndexSpec:
    return IndexSpec(name=name, columns=columns, type=IndexType.UNIQUE)


def fk(
    name: str,
    source: str,
    target: str,
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION,
) -> ForeignKeySpec:
    return ForeignKeySpec(name=name, source=source, target=target, on_delete=on_delete)


SHOP = DatabaseSpec(
    name="shop",
    type=DataBaseName.PSQL,
    notice="Online store: customers, catalog, inventory, orders and billing",
    default_schema="public",
    tables=(
        TableSpec(
            name="users",
            description="Registered customers",
            columns=(
                uuid_pk(),
                c("email", VARCHAR, length=255, unique=True),
                c("password_hash", TEXT),
                c("full_name", VARCHAR, length=255, nullable=True),
                c("phone", VARCHAR, length=32, nullable=True),
                c(
                    "status",
                    ENUM,
                    enum_values=["active", "blocked", "deleted"],
                    default="'active'",
                ),
                c("is_verified", BOOLEAN, default="false"),
                created_at(),
                c("updated_at", TIMESTAMP, nullable=True),
            ),
            indexes=(ix("users_created_at_idx", "-created_at"),),
        ),
        TableSpec(
            name="user_addresses",
            columns=(
                uuid_pk(),
                c("user_id", UUID),
                c("kind", ENUM, enum_values=["billing", "shipping"]),
                c("country", CHAR, length=2),
                c("city", VARCHAR, length=120),
                c("line1", VARCHAR, length=255),
                c("line2", VARCHAR, length=255, nullable=True),
                c("postal_code", VARCHAR, length=20),
                c("is_default", BOOLEAN, default="false"),
            ),
            indexes=(ix("user_addresses_user_idx", "user_id"),),
        ),
        TableSpec(
            name="categories",
            schema="catalog",
            description="Category tree; parent_id points to the parent category",
            columns=(
                serial_pk(),
                c("parent_id", INTEGER, nullable=True),
                c("name", VARCHAR, length=120),
                c("slug", VARCHAR, length=120, unique=True),
                c("position", INTEGER, default="0"),
            ),
            indexes=(ix("categories_parent_idx", "parent_id"),),
        ),
        TableSpec(
            name="brands",
            schema="catalog",
            columns=(
                serial_pk(),
                c("name", VARCHAR, length=120, unique=True),
                c("country", CHAR, length=2, nullable=True),
            ),
        ),
        TableSpec(
            name="products",
            schema="catalog",
            columns=(
                uuid_pk(),
                c("category_id", INTEGER),
                c("brand_id", INTEGER, nullable=True),
                c("sku", VARCHAR, length=64, unique=True),
                c("name", VARCHAR, length=255),
                c("description", TEXT, nullable=True),
                money("price", check='"price" >= 0'),
                c("currency", CHAR, length=3, default="'USD'"),
                c("attributes", JSONB, nullable=True, notice="Free-form product attributes"),
                c("tags", TEXT, array_dimensions=1, nullable=True),
                c("is_active", BOOLEAN, default="true"),
                created_at(),
            ),
            indexes=(
                ix("products_category_idx", "category_id"),
                ix("products_name_idx", "name"),
                ix("products_attributes_idx", "attributes", method="gin"),
            ),
        ),
        TableSpec(
            name="product_images",
            schema="catalog",
            columns=(
                uuid_pk(),
                c("product_id", UUID),
                c("url", TEXT),
                c("alt", VARCHAR, length=255, nullable=True),
                c("position", INTEGER, default="0"),
            ),
            indexes=(ux("product_images_order_uq", "product_id", "position"),),
        ),
        TableSpec(
            name="reviews",
            schema="catalog",
            columns=(
                uuid_pk(),
                c("product_id", UUID),
                c("user_id", UUID),
                c("rating", SMALLINT, check='"rating" BETWEEN 1 AND 5'),
                c("title", VARCHAR, length=120, nullable=True),
                c("body", TEXT, nullable=True),
                created_at(),
            ),
            indexes=(ux("reviews_user_product_uq", "user_id", "product_id"),),
        ),
        TableSpec(
            name="warehouses",
            schema="catalog",
            columns=(
                serial_pk(),
                c("code", VARCHAR, length=16, unique=True),
                c("name", VARCHAR, length=120),
                c("city", VARCHAR, length=120),
            ),
        ),
        TableSpec(
            name="stock_levels",
            schema="catalog",
            description="Available and reserved quantity per warehouse",
            columns=(
                c("warehouse_id", INTEGER, primary_key=True),
                c("product_id", UUID, primary_key=True),
                c("quantity", INTEGER, default="0", check='"quantity" >= 0'),
                c("reserved", INTEGER, default="0", check='"reserved" >= 0'),
                c("updated_at", TIMESTAMP, default="now()"),
            ),
        ),
        TableSpec(
            name="carts",
            schema="sales",
            columns=(
                uuid_pk(),
                c("user_id", UUID, nullable=True, notice="Null for guest carts"),
                created_at(),
                c("updated_at", TIMESTAMP, nullable=True),
            ),
        ),
        TableSpec(
            name="cart_items",
            schema="sales",
            columns=(
                c("cart_id", UUID, primary_key=True),
                c("product_id", UUID, primary_key=True),
                c("quantity", INTEGER, check='"quantity" > 0'),
                created_at("added_at"),
            ),
        ),
        TableSpec(
            name="coupons",
            schema="sales",
            columns=(
                serial_pk(),
                c("code", VARCHAR, length=32, unique=True),
                c("discount_percent", SMALLINT, check='"discount_percent" BETWEEN 1 AND 100'),
                c("valid_until", TIMESTAMP, nullable=True),
                c("usage_limit", INTEGER, nullable=True),
            ),
        ),
        TableSpec(
            name="orders",
            schema="sales",
            columns=(
                uuid_pk(),
                c("user_id", UUID),
                c("shipping_address_id", UUID, nullable=True),
                c("coupon_id", INTEGER, nullable=True),
                c(
                    "status",
                    ENUM,
                    enum_values=["new", "paid", "shipped", "delivered", "cancelled"],
                    default="'new'",
                    notice="Order lifecycle state",
                ),
                money("total", check='"total" >= 0'),
                c("currency", CHAR, length=3, default="'USD'"),
                created_at("placed_at"),
                c("comment", TEXT, nullable=True),
            ),
            indexes=(
                ix("orders_user_idx", "user_id"),
                ix("orders_placed_at_idx", "-placed_at"),
                ix("orders_open_idx", "status", where="\"status\" <> 'delivered'"),
            ),
        ),
        TableSpec(
            name="order_items",
            schema="sales",
            columns=(
                c("order_id", UUID, primary_key=True),
                c("line_no", SMALLINT, primary_key=True),
                c("product_id", UUID),
                c("quantity", INTEGER, check='"quantity" > 0'),
                money("unit_price"),
            ),
            indexes=(ix("order_items_product_idx", "product_id"),),
        ),
        TableSpec(
            name="shipments",
            schema="sales",
            columns=(
                uuid_pk(),
                c("order_id", UUID),
                c("carrier", VARCHAR, length=64),
                c("tracking_number", VARCHAR, length=64, nullable=True, unique=True),
                c(
                    "status",
                    ENUM,
                    enum_values=["preparing", "in_transit", "delivered", "returned"],
                    default="'preparing'",
                ),
                c("shipped_at", TIMESTAMP, nullable=True),
                c("delivered_at", TIMESTAMP, nullable=True),
            ),
            indexes=(ix("shipments_order_idx", "order_id"),),
        ),
        TableSpec(
            name="payments",
            schema="billing",
            columns=(
                uuid_pk(),
                c("order_id", UUID),
                c("provider", ENUM, enum_values=["stripe", "paypal", "invoice"]),
                c(
                    "status",
                    ENUM,
                    enum_values=["pending", "captured", "failed", "refunded"],
                    default="'pending'",
                ),
                money("amount", check='"amount" > 0'),
                c("paid_at", TIMESTAMP, nullable=True),
                c("payload", JSONB, nullable=True, notice="Raw provider response"),
            ),
            indexes=(ix("payments_order_idx", "order_id"),),
        ),
        TableSpec(
            name="refunds",
            schema="billing",
            columns=(
                uuid_pk(),
                c("payment_id", UUID),
                money("amount", check='"amount" > 0'),
                c("reason", TEXT, nullable=True),
                created_at(),
            ),
            indexes=(ix("refunds_payment_idx", "payment_id"),),
        ),
        TableSpec(
            name="invoices",
            schema="billing",
            columns=(
                uuid_pk(),
                c("order_id", UUID, unique=True),
                c("number", VARCHAR, length=32, unique=True),
                c("issued_at", DATE),
                c("pdf_url", TEXT, nullable=True),
            ),
        ),
    ),
    foreign_keys=(
        fk("fk_user_addresses_user", "user_addresses.user_id", "users.id", CASCADE),
        fk("fk_categories_parent", "categories.parent_id", "categories.id", SET_NULL),
        fk("fk_products_category", "products.category_id", "categories.id", RESTRICT),
        fk("fk_products_brand", "products.brand_id", "brands.id", SET_NULL),
        fk("fk_product_images_product", "product_images.product_id", "products.id", CASCADE),
        fk("fk_reviews_product", "reviews.product_id", "products.id", CASCADE),
        fk("fk_reviews_user", "reviews.user_id", "users.id", CASCADE),
        fk("fk_stock_levels_warehouse", "stock_levels.warehouse_id", "warehouses.id", CASCADE),
        fk("fk_stock_levels_product", "stock_levels.product_id", "products.id", CASCADE),
        fk("fk_carts_user", "carts.user_id", "users.id", SET_NULL),
        fk("fk_cart_items_cart", "cart_items.cart_id", "carts.id", CASCADE),
        fk("fk_cart_items_product", "cart_items.product_id", "products.id", CASCADE),
        fk("fk_orders_user", "orders.user_id", "users.id", RESTRICT),
        fk("fk_orders_address", "orders.shipping_address_id", "user_addresses.id", SET_NULL),
        fk("fk_orders_coupon", "orders.coupon_id", "coupons.id", SET_NULL),
        fk("fk_order_items_order", "order_items.order_id", "orders.id", CASCADE),
        fk("fk_order_items_product", "order_items.product_id", "products.id", RESTRICT),
        fk("fk_shipments_order", "shipments.order_id", "orders.id", CASCADE),
        fk("fk_payments_order", "payments.order_id", "orders.id", CASCADE),
        fk("fk_refunds_payment", "refunds.payment_id", "payments.id", CASCADE),
        fk("fk_invoices_order", "invoices.order_id", "orders.id", RESTRICT),
    ),
    groups=(
        GroupSpec(
            name="Customers", tables=("users", "user_addresses"), color="#2563EB", cell=(0, 0)
        ),
        GroupSpec(
            name="Catalog",
            tables=("categories", "brands", "products", "product_images", "reviews"),
            color="#16A34A",
            cell=(1, 0),
            columns=2,
        ),
        GroupSpec(
            name="Inventory", tables=("warehouses", "stock_levels"), color="#0D9488", cell=(2, 0)
        ),
        GroupSpec(
            name="Sales",
            tables=("orders", "order_items", "shipments", "carts", "cart_items", "coupons"),
            color="#EA580C",
            cell=(0, 1),
            columns=2,
        ),
        GroupSpec(
            name="Billing",
            tables=("payments", "refunds", "invoices"),
            color="#DB2777",
            cell=(1, 1),
            columns=2,
        ),
    ),
    notes=(
        NoteSpec(text="Guest carts have no user; they are merged on sign-in.", group="Sales"),
        NoteSpec(text="Stock is reserved when an order is paid.", group="Inventory"),
        NoteSpec(text="Refunds never exceed the captured payment amount.", group="Billing"),
    ),
)

ANALYTICS = DatabaseSpec(
    name="analytics",
    type=DataBaseName.PSQL,
    notice="Product analytics: tracking, experiments and reporting marts",
    default_schema="analytics",
    tables=(
        TableSpec(
            name="sessions",
            columns=(
                uuid_pk(),
                c("user_id", UUID, nullable=True, notice="Shop user, if signed in"),
                c("started_at", TIMESTAMP),
                c("ended_at", TIMESTAMP, nullable=True),
                c("device", ENUM, enum_values=["desktop", "mobile", "tablet"]),
                c("country", CHAR, length=2, nullable=True),
                c("utm", JSONB, nullable=True),
            ),
            indexes=(ix("sessions_started_at_idx", "-started_at"),),
        ),
        TableSpec(
            name="events",
            columns=(
                serial_pk(kind=BIGINT),
                c("session_id", UUID),
                c("name", VARCHAR, length=120),
                c("occurred_at", TIMESTAMP),
                c("properties", JSONB, nullable=True),
            ),
            indexes=(
                ix("events_session_idx", "session_id"),
                ix("events_name_time_idx", "name", "-occurred_at"),
                ix("events_properties_idx", "properties", method="gin"),
            ),
        ),
        TableSpec(
            name="page_views",
            columns=(
                serial_pk(kind=BIGINT),
                c("session_id", UUID),
                c("path", TEXT),
                c("referrer", TEXT, nullable=True),
                c("duration_ms", INTEGER, nullable=True, check='"duration_ms" >= 0'),
                c("viewed_at", TIMESTAMP),
            ),
            indexes=(ix("page_views_session_idx", "session_id"),),
        ),
        TableSpec(
            name="experiments",
            columns=(
                serial_pk(),
                c("key", VARCHAR, length=64, unique=True),
                c("description", TEXT, nullable=True),
                c("started_at", TIMESTAMP),
                c("finished_at", TIMESTAMP, nullable=True),
            ),
        ),
        TableSpec(
            name="experiment_variants",
            columns=(
                c("experiment_id", INTEGER, primary_key=True),
                c("variant", VARCHAR, length=32, primary_key=True),
                c("weight", SMALLINT, check='"weight" > 0'),
            ),
        ),
        TableSpec(
            name="experiment_assignments",
            columns=(
                c("session_id", UUID, primary_key=True),
                c("experiment_id", INTEGER, primary_key=True),
                c("variant", VARCHAR, length=32),
                created_at("assigned_at"),
            ),
        ),
        TableSpec(
            name="daily_sales",
            description="Daily revenue per product, rebuilt nightly",
            columns=(
                c("day", DATE, primary_key=True),
                c("product_id", UUID, primary_key=True),
                c("orders", INTEGER, default="0"),
                c("revenue", NUMERIC, precision=14, scale=2, default="0"),
                c("refunds", NUMERIC, precision=14, scale=2, default="0"),
            ),
        ),
        TableSpec(
            name="funnel_steps",
            columns=(
                serial_pk(),
                c("funnel", VARCHAR, length=64),
                c("step", SMALLINT),
                c("event_name", VARCHAR, length=120),
            ),
            indexes=(ux("funnel_steps_order_uq", "funnel", "step"),),
        ),
        TableSpec(
            name="cohorts",
            columns=(
                c("cohort_month", DATE, primary_key=True),
                c("users", INTEGER),
                c("retained_30d", INTEGER),
                c("retained_90d", INTEGER),
            ),
        ),
    ),
    foreign_keys=(
        fk("fk_events_session", "events.session_id", "sessions.id", CASCADE),
        fk("fk_page_views_session", "page_views.session_id", "sessions.id", CASCADE),
        fk(
            "fk_variants_experiment",
            "experiment_variants.experiment_id",
            "experiments.id",
            CASCADE,
        ),
        fk(
            "fk_assignments_session",
            "experiment_assignments.session_id",
            "sessions.id",
            CASCADE,
        ),
        fk(
            "fk_assignments_variant",
            "experiment_assignments.experiment_id,variant",
            "experiment_variants.experiment_id,variant",
            CASCADE,
        ),
    ),
    groups=(
        GroupSpec(
            name="Tracking",
            tables=("sessions", "events", "page_views"),
            color="#7C3AED",
            cell=(0, 0),
            columns=2,
        ),
        GroupSpec(
            name="Experiments",
            tables=("experiments", "experiment_variants", "experiment_assignments"),
            color="#CA8A04",
            cell=(1, 0),
        ),
        GroupSpec(
            name="Marts",
            tables=("daily_sales", "funnel_steps", "cohorts"),
            color="#0891B2",
            cell=(2, 0),
        ),
    ),
    notes=(
        NoteSpec(
            text="Assignments reference a variant by (experiment_id, variant).",
            group="Experiments",
        ),
        NoteSpec(text="Marts are rebuilt by the nightly job.", group="Marts"),
    ),
)

CRM = DatabaseSpec(
    name="crm",
    type=DataBaseName.PSQL,
    notice="B2B sales: companies, contacts, pipelines and deals",
    default_schema="crm",
    tables=(
        TableSpec(
            name="companies",
            columns=(
                uuid_pk(),
                c("name", VARCHAR, length=255),
                c("domain", VARCHAR, length=255, nullable=True, unique=True),
                c(
                    "industry",
                    ENUM,
                    enum_values=["software", "retail", "finance", "healthcare", "other"],
                    default="'other'",
                ),
                c("employees", INTEGER, nullable=True, check='"employees" >= 0'),
                created_at(),
            ),
            indexes=(ix("companies_name_idx", "name"),),
        ),
        TableSpec(
            name="contacts",
            columns=(
                uuid_pk(),
                c("company_id", UUID, nullable=True),
                c("first_name", VARCHAR, length=120),
                c("last_name", VARCHAR, length=120),
                c("email", VARCHAR, length=255, unique=True),
                c("phone", VARCHAR, length=32, nullable=True),
                c("job_title", VARCHAR, length=120, nullable=True),
            ),
            indexes=(ix("contacts_company_idx", "company_id"),),
        ),
        TableSpec(
            name="pipelines",
            columns=(serial_pk(), c("name", VARCHAR, length=120, unique=True)),
        ),
        TableSpec(
            name="stages",
            columns=(
                serial_pk(),
                c("pipeline_id", INTEGER),
                c("name", VARCHAR, length=120),
                c("position", SMALLINT),
                c("probability", SMALLINT, check='"probability" BETWEEN 0 AND 100'),
            ),
            indexes=(ux("stages_pipeline_position_uq", "pipeline_id", "position"),),
        ),
        TableSpec(
            name="deals",
            columns=(
                uuid_pk(),
                c("company_id", UUID),
                c("contact_id", UUID, nullable=True),
                c("stage_id", INTEGER),
                c("owner_id", UUID, notice="Identity account of the sales manager"),
                c("title", VARCHAR, length=255),
                c("amount", NUMERIC, precision=14, scale=2, nullable=True),
                c("currency", CHAR, length=3, default="'USD'"),
                c("expected_close", DATE, nullable=True),
                created_at(),
            ),
            indexes=(
                ix("deals_stage_idx", "stage_id"),
                ix("deals_owner_idx", "owner_id"),
                ix("deals_company_idx", "company_id"),
            ),
        ),
        TableSpec(
            name="activities",
            columns=(
                uuid_pk(),
                c("deal_id", UUID, nullable=True),
                c("contact_id", UUID, nullable=True),
                c("kind", ENUM, enum_values=["call", "email", "meeting", "task"]),
                c("subject", VARCHAR, length=255),
                c("due_at", TIMESTAMP, nullable=True),
                c("done", BOOLEAN, default="false"),
                created_at(),
            ),
            indexes=(ix("activities_due_idx", "due_at", where='NOT "done"'),),
        ),
        TableSpec(
            name="tags",
            columns=(
                serial_pk(),
                c("name", VARCHAR, length=64, unique=True),
                c("color", CHAR, length=7, nullable=True),
            ),
        ),
        TableSpec(
            name="deal_tags",
            columns=(
                c("deal_id", UUID, primary_key=True),
                c("tag_id", INTEGER, primary_key=True),
            ),
        ),
    ),
    foreign_keys=(
        fk("fk_contacts_company", "contacts.company_id", "companies.id", SET_NULL),
        fk("fk_stages_pipeline", "stages.pipeline_id", "pipelines.id", CASCADE),
        fk("fk_deals_company", "deals.company_id", "companies.id", RESTRICT),
        fk("fk_deals_contact", "deals.contact_id", "contacts.id", SET_NULL),
        fk("fk_deals_stage", "deals.stage_id", "stages.id", RESTRICT),
        fk("fk_activities_deal", "activities.deal_id", "deals.id", CASCADE),
        fk("fk_activities_contact", "activities.contact_id", "contacts.id", CASCADE),
        fk("fk_deal_tags_deal", "deal_tags.deal_id", "deals.id", CASCADE),
        fk("fk_deal_tags_tag", "deal_tags.tag_id", "tags.id", CASCADE),
    ),
    groups=(
        GroupSpec(name="Accounts", tables=("companies", "contacts"), color="#2563EB", cell=(0, 0)),
        GroupSpec(
            name="Pipeline",
            tables=("deals", "deal_tags", "tags", "stages", "pipelines"),
            color="#DC2626",
            cell=(1, 0),
            columns=2,
        ),
        GroupSpec(name="Activity", tables=("activities",), color="#65A30D", cell=(0, 1)),
    ),
    notes=(NoteSpec(text="Deal owners are identity accounts.", group="Pipeline"),),
)

LEGACY = DatabaseSpec(
    name="legacy",
    type=DataBaseName.MYSQL,
    notice="MySQL billing system being migrated; SQL export is rejected for it",
    default_schema=None,
    tables=(
        TableSpec(
            name="customers",
            columns=(
                serial_pk(),
                c("name", VARCHAR, length=100),
                c("email", VARCHAR, length=255, unique=True),
                c("created_at", TIMESTAMP),
            ),
        ),
        TableSpec(
            name="items",
            columns=(
                serial_pk(),
                c("code", VARCHAR, length=32, unique=True),
                c("title", VARCHAR, length=255),
                c("price", NUMERIC, precision=10, scale=2),
            ),
        ),
        TableSpec(
            name="invoices",
            columns=(
                serial_pk(),
                c("customer_id", INTEGER),
                c("number", VARCHAR, length=32, unique=True),
                c("issued_at", TIMESTAMP),
                c("total", NUMERIC, precision=10, scale=2),
            ),
        ),
        TableSpec(
            name="invoice_lines",
            columns=(
                c("invoice_id", INTEGER, primary_key=True),
                c("line_no", SMALLINT, primary_key=True),
                c("item_id", INTEGER),
                c("qty", INTEGER),
                c("price", NUMERIC, precision=10, scale=2),
            ),
        ),
        TableSpec(
            name="payments_log",
            columns=(
                serial_pk(kind=BIGINT),
                c("invoice_id", INTEGER),
                c("amount", NUMERIC, precision=10, scale=2),
                c("paid_at", TIMESTAMP),
            ),
        ),
    ),
    foreign_keys=(
        fk("fk_invoices_customer", "invoices.customer_id", "customers.id", RESTRICT),
        fk("fk_invoice_lines_invoice", "invoice_lines.invoice_id", "invoices.id", CASCADE),
        fk("fk_invoice_lines_item", "invoice_lines.item_id", "items.id", RESTRICT),
        fk("fk_payments_log_invoice", "payments_log.invoice_id", "invoices.id", CASCADE),
    ),
)

DATABASES = (SHOP, ANALYTICS, CRM, LEGACY)
