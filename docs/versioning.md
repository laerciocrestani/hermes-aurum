# Versionamento (Aurum)

A versão exibida em `hermes profile update aurum` vem de **`distribution.yaml`**.

A tag Git `vX.Y.Z` marca o commit da release.

## Regra

Toda alteração versionada exige bump em `distribution.yaml` antes do merge na `main`.

| Tipo | Semver |
|------|--------|
| Quebra de formato do fluxo de caixa ou da CLI | MAJOR |
| Funcionalidade nova compatível | MINOR |
| Correção, docs, ajuste de skill | PATCH |

Alinhe `skills/cashflow/SKILL.md` → `version` e uma linha no Changelog de `ROADMAP.md`.

## Tags

```bash
VERSION=2.0.0
git tag -a "v${VERSION}" -m "Aurum v${VERSION}"
git push origin "v${VERSION}"
```

Instalar uma versão específica:

```bash
hermes profile install github.com/laerciocrestani/hermes-aurum@v2.0.0 --alias -y
```
