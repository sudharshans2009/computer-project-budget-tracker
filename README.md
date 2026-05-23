# 💰 Budget Tracker

A terminal-based personal finance manager backed by MySQL. Track income and expenses, organise transactions with tags, set spending budgets, and view summaries — all from your command line.

![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-blue) ![MySQL 5.7+](https://img.shields.io/badge/MySQL-5.7%2B-orange) ![License: MIT](https://img.shields.io/badge/License-MIT-green)

---

## Features

- **Add & remove** income and expense transactions
- **Tag system** — categorise transactions with custom, typed tags
- **Budget limits** — set spending ceilings per tag with live usage bars
- **Budget alerts** — warnings at 80% spend and when a budget is exceeded
- **Account summary** — total income, total expenses, and net balance
- **Per-tag summary** — breakdown of income, expense, net, and budget usage for every category

---

## Requirements

- Python 3.7+
- A running MySQL server (local or remote)
- `mysql-connector-python` package

```bash
pip install mysql-connector-python
```

> The script will attempt to auto-install `mysql-connector-python` on first run if it is missing.

---

## Getting Started

### 1. Run the script

```bash
python budget_tracker.py
```

### 2. Enter your MySQL credentials

On first launch a connection wizard prompts for host, port, user, password, and database name. Press `Enter` to accept any default.

```
MySQL Connection Setup
(Press Enter to use defaults)

  ▶  Host     [localhost]:
  ▶  Port     [3306]:
  ▶  User     [root]:
  ▶  Password: ••••••••
  ▶  Database [budget_tracker]:
```

### 3. Automatic setup

The database and both tables are created automatically if they do not exist. No manual SQL required.

---

## Main Menu Reference

| Key | Command | Description |
|-----|---------|-------------|
| `1` | Add Income | Record an income transaction with amount, description, date, and optional tag |
| `2` | Add Expense | Record an expense transaction — triggers budget warnings if relevant |
| `3` | Remove Transaction | Delete a transaction by ID after a confirmation prompt |
| `4` | List Transactions | View the 20 most recent transactions, colour-coded by type |
| `5` | Add Tag | Create a tag with type (`expense` / `income` / `both`) and optional budget |
| `6` | Remove Tag | Delete a tag; linked transactions become untagged (history preserved) |
| `7` | List Tags | Show all tags with their type and assigned budget |
| `8` | Set Tag Budget | Assign or update a spending limit for any existing tag |
| `9` | Account Summary | Total income, expenses, and net balance across all time |
| `10` | Summary by Tag | Per-tag breakdown with income, expense, net, budget, and a visual usage bar |
| `0` | Exit | Close the database connection and quit cleanly |

---

## Tag Types

When creating a tag, choose which transaction types it applies to:

| Type | Appears when adding... |
|------|------------------------|
| `expense` | Expenses only |
| `income` | Income only |
| `both` | Either type *(default)* |

**Examples:**  
`Salary` → `income` · `Rent` → `expense` · `Freelance` → `both`

---

## Budget Alerts

Budget thresholds are checked automatically every time you add an expense to a tagged category.

```
⚠  80%+ of budget used for 'Dining Out'!
   Spent ₹3,200 / Budget ₹4,000

⚠  Budget exceeded for 'Dining Out'!
   Spent ₹4,350 / Budget ₹4,000
```

---

## Database Schema

### `tags`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT | Primary key, auto-increment |
| `name` | VARCHAR(60) | Unique tag name |
| `tag_type` | ENUM | `expense`, `income`, or `both` |
| `budget` | DECIMAL(15,2) | Optional spending limit |
| `created_at` | DATETIME | Auto-set on insert |

### `transactions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INT | Primary key, auto-increment |
| `type` | ENUM | `expense` or `income` |
| `amount` | DECIMAL(15,2) | Positive value |
| `description` | VARCHAR(255) | Optional |
| `tag_id` | INT | FK → `tags.id`, `NULL` on tag deletion |
| `txn_date` | DATE | Transaction date |
| `created_at` | DATETIME | Auto-set on insert |

> Deleting a tag sets `tag_id` to `NULL` on its transactions — history is never lost.

---

## Typical Workflow

```bash
# First session
python budget_tracker.py

# 1. Create your tags
5 → Add Tag:  Salary     | type: income  | budget: —
5 → Add Tag:  Rent       | type: expense | budget: 15000
5 → Add Tag:  Groceries  | type: expense | budget: 6000
5 → Add Tag:  Dining Out | type: expense | budget: 4000

# 2. Record transactions
1 → Add Income:  ₹75,000  | Salary    | 2026-04-01
2 → Add Expense: ₹15,000  | Rent      | 2026-04-01
2 → Add Expense: ₹2,340   | Groceries

# 3. Check your position
9  → Account Summary
10 → Summary by Tag
```

---

## Troubleshooting

### Access denied
Ensure your MySQL user has `CREATE`, `INSERT`, `SELECT`, `UPDATE`, and `DELETE` privileges on the target database.

```sql
GRANT ALL PRIVILEGES ON budget_tracker.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### Can't connect to server
Verify MySQL is running:

```bash
# Linux
sudo systemctl status mysql

# macOS (Homebrew)
brew services list | grep mysql
```

Check that the host and port entered match your MySQL configuration.

### Module not found

```bash
pip install mysql-connector-python
```

---

## Project Structure

```
budget_tracker.py   # Single-file application — run this
README.md           # This file
```

---

## License

MIT