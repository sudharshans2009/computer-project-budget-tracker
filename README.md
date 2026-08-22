# Budget Tracker

A terminal-based personal finance tracker for MySQL. It lets you record income and expenses, assign tags, set category budgets, and review account totals and per-tag summaries directly from the command line.

![Python 3.7+](https://img.shields.io/badge/Python-3.7%2B-blue) ![MySQL](https://img.shields.io/badge/MySQL-Required-orange) ![MIT](https://img.shields.io/badge/License-MIT-green)

---

## Features

- Add, remove, and list income and expense entries
- Create tags with `expense`, `income`, or `both` types
- Set and update a budget for each tag
- Get warnings when spending reaches 80% or exceeds the tag budget
- Review total income, total expenses, and net balance
- View a summary by tag with usage bars and totals
- Automatically create the required MySQL tables on startup
- Read connection values from environment variables when present

---

## Requirements

- Python 3.7+
- MySQL server running locally or remotely
- `mysql-connector-python`

Install the dependency:

```bash
pip install mysql-connector-python
```

---

## Getting Started

### 1. Run the app

```bash
python budget_tracker.py
```

### 2. Provide MySQL credentials

The app prompts for host, port, user, password, and database settings. The password is collected securely using `getpass`, so it is not echoed to the terminal.

```text
MySQL Connection Setup
(Press Enter to accept defaults / env values)

  Host     [localhost]:
  Port     [3306]:
  User     [root]:
  Password:
  Database [budget_tracker]:
```

### 3. Optional environment configuration

You can also set values through environment variables instead of entering them manually:

```bash
export BUDGET_DB_HOST=localhost
export BUDGET_DB_PORT=3306
export BUDGET_DB_USER=root
export BUDGET_DB_PASSWORD=your_password
export BUDGET_DB_NAME=budget_tracker
python budget_tracker.py
```

Any missing environment values will still be prompted for interactively.

---

## Database Schema

The app creates the required tables automatically if they do not exist:

```sql
CREATE TABLE IF NOT EXISTS tags (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(60) NOT NULL UNIQUE,
    tag_type   ENUM('expense', 'income', 'both') NOT NULL DEFAULT 'both',
    budget     DECIMAL(15, 2) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    type        ENUM('expense', 'income') NOT NULL,
    amount      DECIMAL(15, 2) NOT NULL,
    description VARCHAR(255) NULL,
    tag_id      INT NULL,
    txn_date    DATE NOT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL
);
```

---

## Main Menu

```text
MAIN MENU
---------------------------------
1  Add Income
2  Add Expense
3  Remove Transaction
4  List Transactions
---------------------------------
5  Add Tag
6  Remove Tag
7  List Tags
8  Set Tag Budget
---------------------------------
9  Account Summary
10 Summary by Tag
---------------------------------
0  Exit
```

### Menu actions

| Key | Action | Description |
|-----|--------|-------------|
| `1` | Add Income | Add an income entry and optionally attach a tag |
| `2` | Add Expense | Add an expense and check budget warnings for the selected tag |
| `3` | Remove Transaction | Delete a transaction by ID after confirmation |
| `4` | List Transactions | Show recent transactions ordered by date |
| `5` | Add Tag | Create a tag with a name, type, and optional budget |
| `6` | Remove Tag | Delete a tag; existing transactions are left as untagged history |
| `7` | List Tags | Display all tags with type and budget |
| `8` | Set Tag Budget | Assign or clear a budget for an existing tag |
| `9` | Account Summary | Show total income, total expenses, and net balance |
| `10` | Summary by Tag | Show per-tag totals, net values, and budget usage |
| `0` | Exit | Close the database connection and end the script |

---

## Tag Types

Each tag can be created with one of these types:

- `expense` — available only when adding expenses
- `income` — available only when adding income
- `both` — available for both types

Examples:

- `Salary` → `income`
- `Rent` → `expense`
- `Freelance` → `both`

---

## Budget Warnings

The app checks tag budgets each time an expense is added. If spending reaches 80% of the budget, it shows a warning. If the budget is exceeded, it shows a stronger warning.

```text
⚠  80%+ of budget used for 'Dining Out'!
   Spent $3,200.00 / Budget $4,000.00

⚠  Budget exceeded for 'Dining Out'!
   Spent $4,350.00 / Budget $4,000.00
```

The tag summary view also includes a progress bar for budget usage.

---

## Typical Workflow

```bash
python budget_tracker.py
```

Then:

1. Choose `5` to add tags
2. Choose `1` to add income
3. Choose `2` to add expenses
4. Choose `9` to view the account summary
5. Choose `10` to inspect per-tag spending

Example:

```text
5 -> Add Tag: Salary     | type: income | budget: blank
5 -> Add Tag: Rent       | type: expense | budget: 1500
5 -> Add Tag: Groceries  | type: expense | budget: 600
1 -> Add Income:  $3500
2 -> Add Expense: $1200
9 -> Account Summary
10 -> Summary by Tag
```

---

## Troubleshooting

### MySQL access denied

Make sure the MySQL user has permission to create, read, update, and delete records in the target database.

```sql
GRANT ALL PRIVILEGES ON budget_tracker.* TO 'your_user'@'localhost';
FLUSH PRIVILEGES;
```

### Connection failed

Check that MySQL is running and that the host, port, user, and database values are correct.

### `mysql-connector-python` not found

```bash
pip install mysql-connector-python
```

---

## Project Structure

```text
budget_tracker.py   # Main CLI application
README.md           # Documentation
```

---

## License

This project is licensed under the MIT License.
