# Versionamento (Aurum)

A versão exibida em `hermes profile update aurum` (`Currently at version X.Y.Z`) vem de **`distribution.yaml`**.

A **tag Git** (`v1.3.0`) marca o commit exato de cada release no GitHub e permite instalar ou voltar a uma versão específica.

## Regra

**Toda alteração versionada no repositório exige bump de versão** antes do merge/commit que vai para `main`.

| Tipo de mudança | Onde atualizar | Semver |
|-----------------|----------------|--------|
| Qualquer release do perfil | `distribution.yaml` → `version` | ver abaixo |
| Skill `financial-operator` alterada | `skills/financial-operator/SKILL.md` → `version` | alinhado ao distribution ou patch local |
| Skill `financial-mentor` alterada | `skills/financial-mentor/SKILL.md` → `version` | idem |
| Release publicada | `ROADMAP.md` → tabela Changelog | uma linha por versão |
| Release publicada | **tag Git** `vX.Y.Z` no commit do release | mesma versão do `distribution.yaml` |

## Semver (resumo)

- **MAJOR** (`2.0.0`): quebra compatibilidade (formato do ledger, comandos removidos, migração obrigatória).
- **MINOR** (`1.1.0`): funcionalidade nova compatível (backup, novos scripts, categorias padrão, provider).
- **PATCH** (`1.0.1`): correção de bug, typos em docs, ajuste de skill sem mudar comportamento público.

## Tags Git

### Formato

- Prefixo **`v`** + semver do `distribution.yaml` → ex.: `v1.3.0`
- Tags **anotadas** (com mensagem), não lightweight

### Quando criar

Somente **depois** do commit na `main` que já contém:

1. `distribution.yaml` com a versão nova
2. Linha no Changelog do `ROADMAP.md`
3. Versões das skills atualizadas (se aplicável)

Não crie tag em commit de WIP nem antes do push para `main`.

### Checklist de release (ordem)

1. [ ] `distribution.yaml` — `version` incrementada
2. [ ] `ROADMAP.md` — linha no Changelog
3. [ ] Skills tocadas — `version` no frontmatter
4. [ ] Commit + push para `main`
5. [ ] Tag anotada `vX.Y.Z` no commit do release
6. [ ] `git push origin vX.Y.Z`
7. [ ] `hermes profile update aurum` no VPS mostra a versão nova

### Comandos

Criar tag no commit atual (HEAD):

```bash
VERSION=1.3.0
git tag -a "v${VERSION}" -m "Aurum v${VERSION}"
git push origin "v${VERSION}"
```

Criar tag em commit específico (retroativo):

```bash
git tag -a v1.2.0 8aad716 -m "Aurum v1.2.0"
git push origin v1.2.0
```

Listar tags:

```bash
git tag -l 'v*' --sort=-v:refname
```

Ver anotação de uma tag:

```bash
git show v1.3.0
```

Checkout de uma versão (desenvolvimento / debug):

```bash
git checkout v1.3.0
```

Instalar perfil a partir de uma tag no GitHub (usuário avançado):

```bash
hermes profile install github.com/laerciocrestani/hermes-aurum@v1.3.0 --alias -y
```

> Confirme a sintaxe exata com `hermes profile install --help` na sua versão do Hermes.

Enviar **todas** as tags pendentes:

```bash
git push origin --tags
```

### Tags publicadas

| Tag | Commit | Notas |
|-----|--------|-------|
| `v1.0.0` | `5e973da` | MVP inicial |
| `v1.1.0` | `0e1c54c` | Categorias pt-BR, backup, stdin, Gemini |
| `v1.2.0` | `8aad716` | Fail-closed conta/categoria |
| `v1.2.1` | `1c0b362` | Flash Lite + Flash fallback |
| `v1.2.2` | `685773b` | `busy_input_mode: queue` no Telegram |
| `v1.3.0` | `d15947f` | Documentação e skills em pt-BR; consultas de leitura |
| `v1.3.1` | `ade9a19` | Tool `terminal` explícita; Flash primário |
| `v1.3.2` | `e2952a6` | Wrapper `aurum-run`; resolução de ledger em múltiplos caminhos |
| `v1.3.3` | `becf655` | Escrita `ledger append`; mercado → Alimentação |
| `v1.3.4` | `29739bb` | `ledger check/repair/reset`; ledger canônico no perfil |
| `v1.4.0` | *(após release)* | `hint`, `do <intent>`, skill enxuta, accounts debit/credit |
| `v1.4.1` | *(após release)* | transfer, mixed expense, add-category/account, Inter no seed |

Atualize esta tabela ao publicar uma nova tag.

## Exemplo completo de release

```yaml
# distribution.yaml
version: 1.3.0
```

```markdown
# ROADMAP.md
| v1.3.0 | 2026-06-17 | Documentação e skills em pt-BR; consultas de leitura sem preflight |
```

```bash
git add distribution.yaml ROADMAP.md skills/
git commit -m "Release Aurum v1.3.0."
git push origin main
git tag -a v1.3.0 -m "Aurum v1.3.0"
git push origin v1.3.0
```
