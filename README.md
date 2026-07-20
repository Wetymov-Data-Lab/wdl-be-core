# @wdl/wdl-be-core

Core API системы визуализации связей баз данных.

<details>
<summary><strong>Requirements</strong></summary>

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker и Docker Compose
- соседний каталог `../wdl-shared` для локальной разработки

</details>

---

<details>
<summary><strong>Installation</strong></summary>

```bash
make env
make install
make docker-up
```

API в Docker будет доступно по адресу `http://localhost:8001`, документация —
`http://localhost:8001/docs`. Команда `make dev` запускает API на порту `8000`.

По умолчанию при старте приложения SQLAlchemy создаёт отсутствующие таблицы
напрямую, без запуска Alembic (`DATABASE_CREATE_TABLES=True`). Этот режим не
изменяет и не удаляет уже существующие колонки. Когда проект перейдёт на
миграции, установите `DATABASE_CREATE_TABLES=False` и применяйте `make migrate`.

При локальной установке `uv` подключает `../wdl-shared` в editable-режиме.
Изменения библиотеки становятся доступны приложению без повторной установки.
При production-сборке локальный source override отключается, и `wdl-shared`
устанавливается из ветки `main` GitHub-репозитория. Перед production-сборкой
актуальная версия `wdl-shared` должна быть опубликована в этой ветке.

</details>

---

<details>
<summary><strong>Project commands</strong></summary>

| Команда                          | Назначение                                     |
|----------------------------------|------------------------------------------------|
| `make install`                   | Установить зависимости для разработки          |
| `make dev`                       | Запустить API с автоматической перезагрузкой   |
| `make lint`                      | Проверить код Ruff                             |
| `make format`                    | Отформатировать код Ruff                       |
| `make typecheck`                 | Выполнить строгую проверку mypy                |
| `make test`                      | Запустить тесты                                |
| `make check`                     | Запустить lint, typecheck и test               |
| `make migrate`                   | Применить миграции Alembic                     |
| `make migration name="message"`  | Создать миграцию Alembic                       |
| `make docker-up`                 | Собрать и запустить API с PostgreSQL           |
| `make docker-down`               | Остановить контейнеры                          |

</details>

---

Описание слоёв и размещения кода находится в [ARCHITECTURE.md](ARCHITECTURE.md).
Правила разработки и подключение Git hooks описаны в [CONTRIBUTING.md](CONTRIBUTING.md).
