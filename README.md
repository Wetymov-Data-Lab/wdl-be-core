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
make up
```

API в Docker будет доступно по адресу `http://localhost:8001`, документация —
`http://localhost:8001/docs`. Команда `make dev` запускает API на порту `8000`.

</details>

---

<details>
<summary><strong>Project commands</strong></summary>

| Команда                         | Назначение                                      | Что выполняет                                                       |
|---------------------------------|-------------------------------------------------|---------------------------------------------------------------------|
| `make env`                      | Создать `.env` из `.env.example`                | `[ -f .env.example ] && cp -f .env.example .env \|\| echo '.env.example not found'` |
| `make install`                  | Синхронизировать зависимости всех групп         | `uv sync --all-groups`                                              |
| `make dev`                      | Запустить API с автоматической перезагрузкой    | `uv run uvicorn wdl_be_core.main:app --reload`                      |
| `make lint`                     | Проверить код с помощью Ruff                    | `uv run ruff check .`                                               |
| `make format`                   | Отформатировать код с помощью Ruff              | `uv run ruff format .`                                              |
| `make typecheck`                | Проверить типы с помощью mypy                    | `uv run mypy src`                                                   |
| `make test`                     | Запустить тесты                                 | `uv run pytest`                                                     |
| `make check`                    | Запустить все проверки                          | Последовательно запускает цели `lint`, `typecheck` и `test`         |
| `make migrate`                  | Применить все неприменённые миграции Alembic    | `uv run alembic upgrade head`                                       |
| `make migration name="message"` | Создать автогенерируемую миграцию Alembic        | `uv run alembic revision --autogenerate -m "$(name)"`               |
| `make up`                       | Запустить сервисы Docker Compose в фоне         | `docker compose up -d`                                              |
| `make build`                    | Собрать образы сервисов Docker Compose          | `docker compose build`                                              |
| `make logs`                     | Показывать логи сервисов в реальном времени     | `docker compose logs -f`                                            |
| `make stop`                     | Остановить сервисы без удаления контейнеров     | `docker compose stop`                                               |
| `make down`                     | Остановить и удалить контейнеры, сети и тома    | `docker compose down -v`                                            |

</details>

---

Правила разработки и подключение Git hooks описаны в [CONTRIBUTING.md](CONTRIBUTING.md).
