# Versionamento (Aurum)

A versão exibida em `hermes profile update aurum` (`Currently at version X.Y.Z`) vem de **`distribution.yaml`**.

## Regra

**Toda alteração versionada no repositório exige bump de versão** antes do merge/commit que vai para `main`.

| Tipo de mudança | Onde atualizar | Semver |
|-----------------|----------------|--------|
| Qualquer release do perfil | `distribution.yaml` → `version` | ver abaixo |
| Skill `financial-operator` alterada | `skills/financial-operator/SKILL.md` → `version` | alinhado ao distribution ou patch local |
| Skill `financial-mentor` alterada | `skills/financial-mentor/SKILL.md` → `version` | idem |
| Release publicada | `ROADMAP.md` → tabela Changelog | uma linha por versão |

## Semver (resumo)

- **MAJOR** (`2.0.0`): quebra compatibilidade (formato do ledger, comandos removidos, migração obrigatória).
- **MINOR** (`1.1.0`): funcionalidade nova compatível (backup, novos scripts, categorias padrão, provider).
- **PATCH** (`1.0.1`): correção de bug, typos em docs, ajuste de skill sem mudar comportamento público.

## Checklist antes de push

1. [ ] `distribution.yaml` — `version` incrementada
2. [ ] `ROADMAP.md` — linha no Changelog
3. [ ] Skills tocadas — `version` no frontmatter
4. [ ] `hermes profile update aurum` no VPS mostra a versão nova

## Exemplo

```yaml
# distribution.yaml
version: 1.1.0
```

```markdown
# ROADMAP.md
| v1.1.0 | 2026-06-16 | Categorias pt-BR, backup diário, ledger append via stdin, Gemini |
```
