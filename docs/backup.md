# Backup diário (Aurum)

O ledger (`data/ledger.jsonl`) é a fonte da verdade. Este backup copia os dados do perfil Aurum para arquivos datados no servidor.

## O que entra no backup

| Arquivo | Motivo |
|---------|--------|
| `data/ledger.jsonl` | Razão financeiro |
| `references/categories.json` | Categorias personalizadas |
| `config.yaml` | Config do perfil |
| `MEMORY.md`, `USER.md`, `SOUL.md` | Memória do agente (se existirem) |
| `.env` | Tokens/chaves (se existir — arquivo com permissão 0600) |

**Não versionado no Git** — só no servidor.

## Onde salva

Padrão: `~/.hermes/profiles/aurum/bkp/aurum-YYYYMMDD.tar.gz`

Override no servidor:

```bash
# em ~/.hermes/profiles/aurum/.env ou no crontab
export AURUM_BACKUP_DIR=/var/backups/aurum
export AURUM_BACKUP_KEEP_DAYS=30
```

Retenção: apaga arquivos `aurum-*.tar.gz` mais antigos que 30 dias (configurável).

## Comandos

```bash
# Criar backup de hoje
HERMES_HOME=~/.hermes/profiles/aurum \
  python3 skills/financial-operator/scripts/backup.py run

# Listar backups
HERMES_HOME=~/.hermes/profiles/aurum \
  python3 skills/financial-operator/scripts/backup.py list
```

Com alias `aurum` instalado, use `HERMES_HOME` explícito (o wrapper não executa scripts arbitrários):

```bash
HERMES_HOME=~/.hermes/profiles/aurum \
  python3 ~/.hermes/profiles/aurum/skills/financial-operator/scripts/backup.py run
```

## Cron no VPS (recomendado)

Todo dia às 03:00 (horário do servidor):

```bash
crontab -e
```

```cron
0 3 * * * HERMES_HOME=$HOME/.hermes/profiles/aurum AURUM_BACKUP_KEEP_DAYS=30 /usr/bin/python3 $HOME/.hermes/profiles/aurum/skills/financial-operator/scripts/backup.py run >> $HOME/.hermes/profiles/aurum/bkp/backup.log 2>&1
```

Crie a pasta antes:

```bash
mkdir -p ~/.hermes/profiles/aurum/bkp
```

## Restaurar

```bash
cd /tmp
tar -xzf ~/.hermes/profiles/aurum/bkp/aurum-20260616.tar.gz
# Conferir manifest.json e copiar data/ledger.jsonl de volta:
cp data/ledger.jsonl ~/.hermes/profiles/aurum/data/ledger.jsonl
```

Sempre pare o gateway antes de sobrescrever o ledger em produção.

## Backup completo do Hermes

Para snapshot de todo `~/.hermes` (todos os perfis):

```bash
hermes backup
```

Use o backup Aurum para o ledger financeiro diário; use `hermes backup` para migração ou desastre geral.
