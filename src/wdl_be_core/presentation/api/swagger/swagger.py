from wdl_be_core.infrastructure.config import settings

tags_metadata = [
    {
        "name": "system",
        "description": (
            "Служебные операции API: проверка доступности приложения "
            "и состояния его основных компонентов."
        ),
    },
    {
        "name": "realms",
        "description": (
            "Управление рабочими пространствами верхнего уровня. "
            "Realm объединяет проекты, настройки доступа и участников."
        ),
    },
    {
        "name": "projects",
        "description": (
            "Управление проектами внутри Realm. "
            "Проект группирует связанные диаграммы и модели баз данных."
        ),
    },
    {
        "name": "database schema",
        "description": (
            "Физическая структура диаграммы базы данных: базы, таблицы и колонки. "
            "Операции также сохраняют свойства типов и расположение таблиц на canvas."
        ),
    },
    {
        "name": "database relationships",
        "description": (
            "Индексы, ограничения и связи между колонками таблиц. "
            "Поддерживаются составные индексы, составные внешние ключи и cardinality."
        ),
    },
    {
        "name": "canvas",
        "description": (
            "Визуальное состояние редактора: viewport, масштаб, сетка, "
            "группы таблиц и текстовые заметки."
        ),
    },
]

servers = (
    [
        {"url": "http://localhost:8000", "description": "Development environment"},
        {"url": settings.PROD_SERVER_URL, "description": "Production environment"},
    ]
    if settings.PROD_SERVER_URL
    else []
)
