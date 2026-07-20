# Contributing

<details>
<summary><strong>Подготовка окружения</strong></summary>

Репозитории должны находиться рядом:

```text
wdl/
├── wdl-be-core/
└── wdl-shared/
```

Установите зависимости:

```bash
make install
```
</details>

---

<details>
<summary><strong>Git hooks</strong></summary>
Подключите hooks из репозитория один раз после клонирования:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/*
```

`pre-commit` запускает Ruff. `commit-msg` проверяет Conventional Commits и
ограничивает заголовок коммита 70 символами.

Допустимые типы коммитов:

```text
feat, fix, docs, refactor, perf, test, build, ci, chore, revert
```

Пример:

```text
feat(api): add graph endpoint
```
</details>

## Перед pull request

```bash
make check
```

Если изменились модели SQLAlchemy, создайте и проверьте миграцию:

```bash
make migration name="describe schema change"
make migrate
```
