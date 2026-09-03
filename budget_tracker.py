#!/usr/bin/env python3

"""
Terminal-based Budget Tracker
Sudharshan S (@sudharshans2009)
LICENSE: MIT
"""


from __future__ import annotations

import os
import sys
import getpass
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterator, Optional

try:
    import mysql.connector
    from mysql.connector import Error, MySQLConnection
    from mysql.connector.cursor import MySQLCursor
except ImportError:
    print("ERROR: mysql-connector-python is not installed. Run: pip install mysql-connector-python")
    sys.exit(1)

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    DIM = "\033[2m"

def header(text: str) -> None:
    width = 56
    print(f"\n{C.CYAN}{C.BOLD}{'─' * width}")
    print(f"  {text}")
    print(f"{'─' * width}{C.RESET}")

def success(msg: str) -> None:
    print(f"{C.GREEN}  SUCCESS: {msg}{C.RESET}")

def error(msg: str) -> None:
    print(f"{C.RED}  ERROR: {msg}{C.RESET}")

def info(msg: str) -> None:
    print(f"{C.YELLOW}  INFO: {msg}{C.RESET}")

def prompt(msg: str) -> str:
    return input(f"{C.CYAN}  >  {msg}: {C.RESET}").strip()

def confirm(msg: str) -> bool:
    return prompt(f"{msg} [y/N]").lower() == "y"

def colorize(text: str, color: str) -> str:
    return f"{color}{text}{C.RESET}"

def padded(text: str, width: int, align: str = "<") -> str:
    return f"{text:{align}{width}}"

def fmt_money(amount, color: bool = True, signed: bool = False) -> str:
    amount = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    sign = ("+" if amount >= 0 else "-") if signed else ""
    plain = f"{sign}${abs(amount):,.2f}"
    return colorize(plain, C.GREEN if amount >= 0 else C.RED) if color else plain

def fmt_money_cell(amount, width: int, align: str = ">", signed: bool = False,
                    color: Optional[str] = None) -> str:
    dec = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    cell = padded(fmt_money(dec, color=False, signed=signed), width, align)
    return colorize(cell, color if color is not None else (C.GREEN if dec >= 0 else C.RED))

@dataclass
class DBConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "budget_tracker"

    def as_kwargs(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "autocommit": False,
        }

def get_db_config() -> DBConfig:
    env = os.environ
    if env.get("BUDGET_DB_HOST") or env.get("BUDGET_DB_USER"):
        info("Using DB settings from environment variables where available.")

    print(f"\n{C.CYAN}{C.BOLD}  MySQL Connection Setup{C.RESET}")
    print(f"  {C.DIM}(Press Enter to accept defaults / env values){C.RESET}\n")

    host = env.get("BUDGET_DB_HOST") or prompt("Host     [localhost]") or "localhost"
    port_str = env.get("BUDGET_DB_PORT") or prompt("Port     [3306]") or "3306"
    user = env.get("BUDGET_DB_USER") or prompt("User     [root]") or "root"
    password = env.get("BUDGET_DB_PASSWORD")
    if password is None:
        password = getpass.getpass(f"{C.CYAN}  >  Password: {C.RESET}")
    database = env.get("BUDGET_DB_NAME") or prompt("Database [budget_tracker]") or "budget_tracker"

    try:
        port = int(port_str)
    except ValueError:
        error(f"Invalid port '{port_str}', falling back to 3306.")
        port = 3306

    return DBConfig(host=host, port=port, user=user, password=password, database=database)

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS tags (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        name       VARCHAR(60) NOT NULL UNIQUE,
        tag_type   ENUM('expense', 'income', 'both') NOT NULL DEFAULT 'both',
        budget     DECIMAL(15, 2) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        type        ENUM('expense', 'income') NOT NULL,
        amount      DECIMAL(15, 2) NOT NULL,
        description VARCHAR(255) NULL,
        tag_id      INT NULL,
        txn_date    DATE NOT NULL,
        created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL
    )
    """,
]

@contextmanager
def cursor_scope(conn: MySQLConnection, dictionary: bool = False) -> Iterator[MySQLCursor]:
    cur = conn.cursor(dictionary=dictionary)
    try:
        yield cur
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()

def fetch_one(conn: MySQLConnection, query: str, params: tuple = ()) -> Optional[dict]:
    with cursor_scope(conn, dictionary=True) as cur:
        cur.execute(query, params)
        return cur.fetchone()

def fetch_all(conn: MySQLConnection, query: str, params: tuple = ()) -> list[dict]:
    with cursor_scope(conn, dictionary=True) as cur:
        cur.execute(query, params)
        return cur.fetchall()

def execute_commit(conn: MySQLConnection, query: str, params: tuple = ()) -> int:
    with cursor_scope(conn) as cur:
        cur.execute(query, params)
        last_id = cur.lastrowid
    conn.commit()
    return last_id

def ensure_schema(conn: MySQLConnection) -> None:
    with cursor_scope(conn) as cur:
        for statement in SCHEMA:
            cur.execute(statement)
    conn.commit()

def connect(config: DBConfig) -> MySQLConnection:
    return mysql.connector.connect(**config.as_kwargs())

def prompt_id(msg: str) -> Optional[int]:
    raw = prompt(msg)
    if not raw.isdigit():
        error("ID must be a number.")
        return None
    return int(raw)

def prompt_budget(msg: str) -> tuple[bool, Optional[Decimal]]:
    raw = prompt(msg)
    if not raw:
        return True, None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        error(f"'{raw}' is not a valid amount.")
        return False, None
    if value < 0:
        error("Budget cannot be negative.")
        return False, None
    return True, value

def add_tag(conn: MySQLConnection) -> None:
    header("Add Tag")
    name = prompt("Tag name")
    if not name:
        error("Tag name cannot be empty.")
        return

    tag_type = (prompt("Type  [expense / income / both]  (default: both)") or "both").lower()
    if tag_type not in ("expense", "income", "both"):
        error("Invalid type. Use expense, income, or both.")
        return

    ok, budget = prompt_budget("Budget limit (leave blank for none)")
    if not ok:
        return

    try:
        execute_commit(conn, "INSERT INTO tags (name, tag_type, budget) VALUES (%s, %s, %s)",
                        (name, tag_type, budget))
        success(f"Tag '{name}' added.")
    except mysql.connector.IntegrityError:
        error(f"Tag '{name}' already exists.")

def remove_tag(conn: MySQLConnection) -> None:
    header("Remove Tag")
    list_tags(conn, show_header=False)
    tag_id = prompt_id("Enter Tag ID to remove (transactions keep history, untagged)")
    if tag_id is None:
        return

    row = fetch_one(conn, "SELECT name FROM tags WHERE id = %s", (tag_id,))
    if not row:
        error("Tag not found.")
        return
    if not confirm(f"Delete tag '{row['name']}'? Transactions will be untagged."):
        info("Cancelled.")
        return

    execute_commit(conn, "DELETE FROM tags WHERE id = %s", (tag_id,))
    success(f"Tag '{row['name']}' removed.")

def set_tag_budget(conn: MySQLConnection) -> None:
    header("Assign / Update Tag Budget")
    list_tags(conn, show_header=False)
    tag_id = prompt_id("Enter Tag ID")
    if tag_id is None:
        return

    row = fetch_one(conn, "SELECT name, budget FROM tags WHERE id = %s", (tag_id,))
    if not row:
        error("Tag not found.")
        return

    info(f"Current budget for '{row['name']}': {fmt_money(row['budget']) if row['budget'] else 'None'}")
    ok, budget = prompt_budget("New budget amount (blank to remove)")
    if not ok:
        return

    execute_commit(conn, "UPDATE tags SET budget = %s WHERE id = %s", (budget, tag_id))
    success("Budget updated.")

def list_tags(conn: MySQLConnection, show_header: bool = True) -> None:
    if show_header:
        header("Tags")
    rows = fetch_all(conn, "SELECT * FROM tags ORDER BY name")
    if not rows:
        info("No tags yet.")
        return

    print(f"\n  {C.BOLD}{padded('ID', 5)} {padded('Name', 25)} {padded('Type', 10)} {padded('Budget', 12, '>')}{C.RESET}")
    print(f"  {'─' * 56}")
    for r in rows:
        bud = fmt_money_cell(r["budget"], 12, color=C.RESET) if r["budget"] \
            else colorize(padded("—", 12, ">"), C.DIM)
        print(f"  {padded(str(r['id']), 5)} {padded(r['name'], 25)} {padded(r['tag_type'], 10)} {bud}")

def pick_tag(conn: MySQLConnection, txn_type: str) -> Optional[int]:
    tags = fetch_all(conn, "SELECT * FROM tags WHERE tag_type = %s OR tag_type = 'both' ORDER BY name",
                      (txn_type,))
    if not tags:
        info("No tags available. Add tags first (or proceed untagged).")
        return None

    print(f"\n  {C.BOLD}{padded('ID', 5)} Tag{C.RESET}")
    for t in tags:
        print(f"  {padded(str(t['id']), 5)} {t['name']}")

    tid = prompt("Tag ID (blank for untagged)")
    if not tid:
        return None
    for t in tags:
        if str(t["id"]) == tid:
            return t["id"]
    error("Invalid tag ID. Transaction saved untagged.")
    return None

def add_transaction(conn: MySQLConnection, txn_type: str) -> None:
    header(f"Add {txn_type.capitalize()}")

    amount_str = prompt("Amount")
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        error("Enter a valid positive number.")
        return

    description = prompt("Description (optional)")

    date_str = prompt(f"Date [YYYY-MM-DD] (default: today {date.today().isoformat()})") \
        or date.today().isoformat()
    try:
        txn_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        error("Invalid date format.")
        return

    tag_id = pick_tag(conn, txn_type)

    txn_id = execute_commit(conn, """
        INSERT INTO transactions (type, amount, description, tag_id, txn_date)
        VALUES (%s, %s, %s, %s, %s)
        """, (txn_type, amount, description or None, tag_id, txn_date))
    success(f"{txn_type.capitalize()} of {fmt_money(amount)} recorded (ID #{txn_id}).")

    if tag_id:
        _check_budget_warning(conn, tag_id)

def _check_budget_warning(conn: MySQLConnection, tag_id: int) -> None:
    row = fetch_one(conn, """
        SELECT t.name, t.budget,
               COALESCE(SUM(CASE WHEN tx.type = 'expense' THEN tx.amount ELSE 0 END), 0) AS spent
        FROM tags t
        LEFT JOIN transactions tx ON tx.tag_id = t.id
        WHERE t.id = %s
        GROUP BY t.id
        """, (tag_id,))
    if not row or not row["budget"]:
        return

    spent, budget, name = row["spent"], row["budget"], row["name"]
    if spent >= budget:
        color, label = C.RED, "Budget exceeded"
    elif spent >= budget * Decimal("0.8"):
        color, label = C.YELLOW, "80%+ of budget used"
    else:
        return

    print(f"\n  {color}{C.BOLD}⚠  {label} for '{name}'! "
          f"Spent {fmt_money(spent)} / Budget {fmt_money(budget)}{C.RESET}")

def remove_transaction(conn: MySQLConnection) -> None:
    header("Remove Transaction")
    list_transactions(conn, limit=15, show_header=False)
    txn_id = prompt_id("Transaction ID to delete")
    if txn_id is None:
        return

    row = fetch_one(conn, "SELECT type, amount, description FROM transactions WHERE id = %s", (txn_id,))
    if not row:
        error("Transaction not found.")
        return
    desc = row["description"] or "no desc"
    if not confirm(f"Delete #{txn_id} [{row['type']}: {fmt_money(row['amount'])} — {desc}]?"):
        info("Cancelled.")
        return

    execute_commit(conn, "DELETE FROM transactions WHERE id = %s", (txn_id,))
    success("Transaction removed.")

def list_transactions(conn: MySQLConnection, limit: int = 20, show_header: bool = True) -> None:
    if show_header:
        header("Recent Transactions")

    rows = fetch_all(conn, """
        SELECT tx.id, tx.type, tx.amount, tx.description,
               COALESCE(t.name, '—') AS tag,
               tx.txn_date
        FROM transactions tx
        LEFT JOIN tags t ON t.id = tx.tag_id
        ORDER BY tx.txn_date DESC, tx.created_at DESC
        LIMIT %s
        """, (limit,))
    if not rows:
        info("No transactions yet.")
        return

    print(f"\n  {C.BOLD}{padded('ID', 6)} {padded('Date', 12)} {padded('Type', 9)} "
          f"{padded('Amount', 12, '>')}  {padded('Tag', 20)} Description{C.RESET}")
    print(f"  {'─' * 80}")
    for r in rows:
        amt = fmt_money_cell(r["amount"], 12, signed=True,
                              color=C.GREEN if r["type"] == "income" else C.RED)
        desc = (r["description"] or "")[:30]
        print(f"  {padded(str(r['id']), 6)} {padded(str(r['txn_date']), 12)} "
              f"{padded(r['type'], 9)} {amt}  {padded(r['tag'], 20)} {desc}")

def summary_account(conn: MySQLConnection) -> None:
    header("Account Summary")
    row = fetch_one(conn, """
        SELECT
            SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense,
            COUNT(*) AS txn_count
        FROM transactions
        """)

    inc = row["total_income"] or Decimal(0)
    exp = row["total_expense"] or Decimal(0)
    net = inc - exp

    print(f"\n  {'Total Income   :':<22} {fmt_money(inc)}")
    print(f"  {'Total Expenses :':<22} {fmt_money(-exp)}")
    print(f"  {'─' * 40}")
    print(f"  {C.BOLD}{'Net Balance    :':<22} {fmt_money(net)}{C.RESET}")
    print(f"\n  {C.DIM}Total transactions: {row['txn_count']}{C.RESET}")

def summary_by_tag(conn: MySQLConnection) -> None:
    header("Summary by Tag")
    rows = fetch_all(conn, """
        SELECT
            COALESCE(t.name, 'Untagged') AS tag,
            t.budget,
            SUM(CASE WHEN tx.type = 'income'  THEN tx.amount ELSE 0 END) AS income,
            SUM(CASE WHEN tx.type = 'expense' THEN tx.amount ELSE 0 END) AS expense,
            COUNT(*) AS txns
        FROM transactions tx
        LEFT JOIN tags t ON t.id = tx.tag_id
        GROUP BY t.id, t.name, t.budget
        ORDER BY expense DESC
        """)
    if not rows:
        info("No transactions yet.")
        return

    print(f"\n  {C.BOLD}{padded('Tag', 22)} {padded('Income', 12, '>')} {padded('Expense', 12, '>')} "
          f"{padded('Net', 12, '>')} {padded('Budget', 12, '>')}  Usage{C.RESET}")
    print(f"  {'─' * 80}")
    for r in rows:
        inc = r["income"] or Decimal(0)
        exp = r["expense"] or Decimal(0)
        net = inc - exp
        bud = r["budget"]

        usage_str = ""
        if bud and bud > 0:
            pct = float(exp / bud * 100)
            bar_filled = min(int(pct / 10), 10)
            bar = "█" * bar_filled + "░" * (10 - bar_filled)
            bar_color = C.GREEN if pct < 80 else C.YELLOW if pct < 100 else C.RED
            usage_str = f"{bar_color}{bar} {pct:.0f}%{C.RESET}"
        bud_str = padded(f"${bud:,.0f}" if bud else "—", 12, ">")

        print(f"  {padded(r['tag'], 22)} "
              f"{fmt_money_cell(inc, 12, color=C.GREEN)} "
              f"{fmt_money_cell(exp, 12, color=C.RED)} "
              f"{fmt_money_cell(abs(net), 12, color=C.GREEN if net >= 0 else C.RED)} "
              f"{bud_str}  {usage_str}")

MENU = """
 {bold}MAIN MENU{reset}
 {dim}---------------------------------{reset}
 {g}1{r}  Add Income
 {g}2{r}  Add Expense
 {g}3{r}  Remove Transaction
 {g}4{r}  List Transactions
 {dim}---------------------------------{reset}
 {g}5{r}  Add Tag
 {g}6{r}  Remove Tag
 {g}7{r}  List Tags
 {g}8{r}  Set Tag Budget
 {dim}---------------------------------{reset}
 {g}9{r}  Account Summary
 {g}10{r} Summary by Tag
 {dim}---------------------------------{reset}
 {g}0{r}  Exit
"""

def main() -> None:
    print(f"\n{C.CYAN}{C.BOLD}")
    print("  BUDGET TRACKER")
    print(C.RESET)

    config = get_db_config()

    print(f"\n{C.DIM}  Connecting to MySQL...{C.RESET}")
    try:
        conn = connect(config)
        success(f"Connected to '{config.database}' on {config.host}:{config.port}")
    except Error as e:
        error(f"Could not connect: {e}")
        sys.exit(1)

    try:
        ensure_schema(conn)
    except Error as e:
        error(f"Could not initialize schema: {e}")
        conn.close()
        sys.exit(1)

    actions = {
        "1": lambda: add_transaction(conn, "income"),
        "2": lambda: add_transaction(conn, "expense"),
        "3": lambda: remove_transaction(conn),
        "4": lambda: list_transactions(conn),
        "5": lambda: add_tag(conn),
        "6": lambda: remove_tag(conn),
        "7": lambda: list_tags(conn),
        "8": lambda: set_tag_budget(conn),
        "9": lambda: summary_account(conn),
        "10": lambda: summary_by_tag(conn),
    }

    try:
        while True:
            print(MENU.format(bold=C.BOLD, reset=C.RESET, dim=C.DIM, g=C.GREEN, r=C.RESET))
            choice = prompt("Choose an option")
            if choice == "0":
                print(f"\n{C.CYAN}Goodbye!{C.RESET}\n")
                break
            elif choice in actions:
                try:
                    actions[choice]()
                except Error as e:
                    error(f"Database error: {e}")
                except KeyboardInterrupt:
                    print("\n")
                    info("Action cancelled.")
            else:
                error("Invalid option. Try again.")
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{C.CYAN}Exiting... Goodbye!{C.RESET}\n")
        sys.exit(0)
