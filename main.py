#!/usr/bin/env python3

import sys
import os
from datetime import datetime
from decimal import Decimal

try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("Installing mysql-connector-python...")
    os.system(f"{sys.executable} -m pip install mysql-connector-python")
    import mysql.connector
    from mysql.connector import Error

# ─────────────────────────────────────────────
#  ANSI Colors
# ─────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    DIM     = "\033[2m"

def header(text):
    width = 56
    print(f"\n{C.CYAN}{C.BOLD}{'─'*width}")
    print(f"  {text}")
    print(f"{'─'*width}{C.RESET}")

def success(msg): print(f"{C.GREEN}  ✔  {msg}{C.RESET}")
def error(msg):   print(f"{C.RED}  ✘  {msg}{C.RESET}")
def info(msg):    print(f"{C.YELLOW}  ℹ  {msg}{C.RESET}")
def prompt(msg):  return input(f"{C.CYAN}  ▶  {msg}: {C.RESET}").strip()

def fmt_amount(amount, color=True):
    amount = float(amount)
    s = f"₹{abs(amount):,.2f}"
    if not color:
        return s
    return f"{C.GREEN}{s}{C.RESET}" if amount >= 0 else f"{C.RED}{s}{C.RESET}"

# ─────────────────────────────────────────────
#  DB Connection
# ─────────────────────────────────────────────
def get_connection(config):
    return mysql.connector.connect(**config)

def setup_database(config):
    """Create DB and tables if they don't exist."""
    base = {k: v for k, v in config.items() if k != "database"}
    conn = mysql.connector.connect(**base)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{config['database']}` CHARACTER SET utf8mb4")
    conn.commit()
    cur.close()
    conn.close()

    conn = get_connection(config)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(60) UNIQUE NOT NULL,
            tag_type    ENUM('expense','income','both') DEFAULT 'both',
            budget      DECIMAL(15,2) DEFAULT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            type         ENUM('expense','income') NOT NULL,
            amount       DECIMAL(15,2) NOT NULL,
            description  VARCHAR(255),
            tag_id       INT,
            txn_date     DATE NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE SET NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()

# ─────────────────────────────────────────────
#  Tag Management
# ─────────────────────────────────────────────
def add_tag(conn):
    header("Add Tag")
    name = prompt("Tag name")
    if not name:
        error("Tag name cannot be empty.")
        return
    tag_type = prompt("Type  [expense / income / both]  (default: both)").lower() or "both"
    if tag_type not in ("expense", "income", "both"):
        error("Invalid type. Use expense, income, or both.")
        return
    budget_str = prompt("Budget limit (leave blank for none)")
    budget = None
    if budget_str:
        try:
            budget = Decimal(budget_str)
        except Exception:
            error("Invalid budget amount.")
            return
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO tags (name, tag_type, budget) VALUES (%s, %s, %s)",
                    (name, tag_type, budget))
        conn.commit()
        success(f"Tag '{name}' added.")
    except mysql.connector.IntegrityError:
        error(f"Tag '{name}' already exists.")
    finally:
        cur.close()

def remove_tag(conn):
    header("Remove Tag")
    list_tags(conn, show_header=False)
    tag_id = prompt("Enter Tag ID to remove (transactions keep history)")
    cur = conn.cursor()
    cur.execute("SELECT name FROM tags WHERE id = %s", (tag_id,))
    row = cur.fetchone()
    if not row:
        error("Tag not found.")
        cur.close()
        return
    confirm = prompt(f"Delete tag '{row[0]}'? Transactions will be untagged. [y/N]").lower()
    if confirm == "y":
        cur.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
        conn.commit()
        success(f"Tag '{row[0]}' removed.")
    else:
        info("Cancelled.")
    cur.close()

def set_tag_budget(conn):
    header("Assign / Update Tag Budget")
    list_tags(conn, show_header=False)
    tag_id = prompt("Enter Tag ID")
    cur = conn.cursor()
    cur.execute("SELECT name, budget FROM tags WHERE id = %s", (tag_id,))
    row = cur.fetchone()
    if not row:
        error("Tag not found.")
        cur.close()
        return
    info(f"Current budget for '{row[0]}': {fmt_amount(row[1]) if row[1] else 'None'}")
    budget_str = prompt("New budget amount (blank to remove)")
    budget = None
    if budget_str:
        try:
            budget = Decimal(budget_str)
        except Exception:
            error("Invalid amount.")
            cur.close()
            return
    cur.execute("UPDATE tags SET budget = %s WHERE id = %s", (budget, tag_id))
    conn.commit()
    success("Budget updated.")
    cur.close()

def list_tags(conn, show_header=True):
    if show_header:
        header("Tags")
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM tags ORDER BY name")
    rows = cur.fetchall()
    cur.close()
    if not rows:
        info("No tags yet.")
        return
    print(f"\n  {C.BOLD}{'ID':<5} {'Name':<25} {'Type':<10} {'Budget':>12}{C.RESET}")
    print(f"  {'─'*54}")
    for r in rows:
        bud = fmt_amount(r['budget']) if r['budget'] else f"{C.DIM}  —{C.RESET}"
        print(f"  {r['id']:<5} {r['name']:<25} {r['tag_type']:<10} {bud:>12}")

# ─────────────────────────────────────────────
#  Transaction Management
# ─────────────────────────────────────────────
def pick_tag(conn, txn_type):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM tags WHERE tag_type = %s OR tag_type = 'both' ORDER BY name",
                (txn_type,))
    tags = cur.fetchall()
    cur.close()
    if not tags:
        info("No tags available. Add tags first (or proceed untagged).")
        return None
    print(f"\n  {C.BOLD}{'ID':<5} {'Tag':<25}{C.RESET}")
    for t in tags:
        print(f"  {t['id']:<5} {t['name']}")
    tid = prompt("Tag ID (blank for untagged)")
    if not tid:
        return None
    for t in tags:
        if str(t['id']) == tid:
            return t['id']
    error("Invalid tag ID. Transaction saved untagged.")
    return None

def add_transaction(conn, txn_type):
    header(f"Add {txn_type.capitalize()}")
    amount_str = prompt("Amount")
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError
    except Exception:
        error("Enter a valid positive number.")
        return
    description = prompt("Description (optional)")
    date_str = prompt(f"Date [YYYY-MM-DD] (default: today {datetime.today().strftime('%Y-%m-%d')})")
    if not date_str:
        date_str = datetime.today().strftime("%Y-%m-%d")
    try:
        txn_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        error("Invalid date format.")
        return
    tag_id = pick_tag(conn, txn_type)

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO transactions (type, amount, description, tag_id, txn_date)
        VALUES (%s, %s, %s, %s, %s)
    """, (txn_type, amount, description or None, tag_id, txn_date))
    conn.commit()
    txn_id = cur.lastrowid
    cur.close()
    success(f"{txn_type.capitalize()} of {fmt_amount(amount)} recorded (ID #{txn_id}).")

    # Budget warning
    if tag_id:
        _check_budget_warning(conn, tag_id)

def _check_budget_warning(conn, tag_id):
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT t.name, t.budget,
               COALESCE(SUM(CASE WHEN tx.type='expense' THEN tx.amount ELSE 0 END), 0) AS spent
        FROM tags t
        LEFT JOIN transactions tx ON tx.tag_id = t.id
        WHERE t.id = %s
        GROUP BY t.id
    """, (tag_id,))
    row = cur.fetchone()
    cur.close()
    if row and row['budget'] and row['spent'] >= row['budget']:
        print(f"\n  {C.RED}{C.BOLD}⚠  Budget exceeded for '{row['name']}'! "
              f"Spent {fmt_amount(row['spent'])} / Budget {fmt_amount(row['budget'])}{C.RESET}")
    elif row and row['budget'] and row['spent'] >= row['budget'] * Decimal("0.8"):
        print(f"\n  {C.YELLOW}{C.BOLD}⚠  80%+ of budget used for '{row['name']}'! "
              f"Spent {fmt_amount(row['spent'])} / Budget {fmt_amount(row['budget'])}{C.RESET}")

def remove_transaction(conn):
    header("Remove Transaction")
    list_transactions(conn, limit=15, show_header=False)
    txn_id = prompt("Transaction ID to delete")
    cur = conn.cursor()
    cur.execute("SELECT type, amount, description FROM transactions WHERE id = %s", (txn_id,))
    row = cur.fetchone()
    if not row:
        error("Transaction not found.")
        cur.close()
        return
    confirm = prompt(f"Delete #{txn_id} [{row[0]}: {fmt_amount(row[1])} — {row[2] or 'no desc'}]? [y/N]").lower()
    if confirm == "y":
        cur.execute("DELETE FROM transactions WHERE id = %s", (txn_id,))
        conn.commit()
        success("Transaction removed.")
    else:
        info("Cancelled.")
    cur.close()

def list_transactions(conn, limit=20, show_header=True):
    if show_header:
        header("Recent Transactions")
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT tx.id, tx.type, tx.amount, tx.description,
               COALESCE(t.name,'—') AS tag,
               tx.txn_date
        FROM transactions tx
        LEFT JOIN tags t ON t.id = tx.tag_id
        ORDER BY tx.txn_date DESC, tx.created_at DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    if not rows:
        info("No transactions yet.")
        return
    print(f"\n  {C.BOLD}{'ID':<6} {'Date':<12} {'Type':<9} {'Amount':>12}  {'Tag':<20} {'Description'}{C.RESET}")
    print(f"  {'─'*80}")
    for r in rows:
        color = C.GREEN if r['type'] == 'income' else C.RED
        sign  = "+" if r['type'] == 'income' else "-"
        amt   = f"{color}{sign}₹{r['amount']:,.2f}{C.RESET}"
        desc  = (r['description'] or '')[:30]
        print(f"  {r['id']:<6} {str(r['txn_date']):<12} {r['type']:<9} {amt:>20}  {r['tag']:<20} {desc}")

# ─────────────────────────────────────────────
#  Summary & Reports
# ─────────────────────────────────────────────
def summary_account(conn):
    header("Account Summary")
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT
            SUM(CASE WHEN type='income'  THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS total_expense,
            COUNT(*) AS txn_count
        FROM transactions
    """)
    row = cur.fetchone()
    cur.close()

    inc  = row['total_income']  or Decimal(0)
    exp  = row['total_expense'] or Decimal(0)
    net  = inc - exp
    nc   = C.GREEN if net >= 0 else C.RED

    print(f"\n  {'Total Income   :':<22} {C.GREEN}₹{inc:>14,.2f}{C.RESET}")
    print(f"  {'Total Expenses :':<22} {C.RED}₹{exp:>14,.2f}{C.RESET}")
    print(f"  {'─'*40}")
    print(f"  {C.BOLD}{'Net Balance    :':<22} {nc}₹{net:>14,.2f}{C.RESET}")
    print(f"\n  {C.DIM}Total transactions: {row['txn_count']}{C.RESET}")

def summary_by_tag(conn):
    header("Summary by Tag")
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT
            COALESCE(t.name,'Untagged') AS tag,
            t.budget,
            SUM(CASE WHEN tx.type='income'  THEN tx.amount ELSE 0 END) AS income,
            SUM(CASE WHEN tx.type='expense' THEN tx.amount ELSE 0 END) AS expense,
            COUNT(*) AS txns
        FROM transactions tx
        LEFT JOIN tags t ON t.id = tx.tag_id
        GROUP BY t.id, t.name, t.budget
        ORDER BY expense DESC
    """)
    rows = cur.fetchall()
    cur.close()

    if not rows:
        info("No transactions yet.")
        return

    print(f"\n  {C.BOLD}{'Tag':<22} {'Income':>12} {'Expense':>12} {'Net':>12} {'Budget':>12} {'Usage':<10}{C.RESET}")
    print(f"  {'─'*80}")
    for r in rows:
        inc  = r['income']  or Decimal(0)
        exp  = r['expense'] or Decimal(0)
        net  = inc - exp
        nc   = C.GREEN if net >= 0 else C.RED
        bud  = r['budget']

        usage_str = ""
        if bud and bud > 0:
            pct = float(exp / bud * 100)
            bar_filled = int(pct / 10)
            bar = "█" * min(bar_filled, 10) + "░" * max(0, 10 - bar_filled)
            bar_color = C.GREEN if pct < 80 else C.YELLOW if pct < 100 else C.RED
            usage_str = f"{bar_color}{bar} {pct:.0f}%{C.RESET}"
        bud_str = f"₹{bud:,.0f}" if bud else "—"

        print(f"  {r['tag']:<22} {C.GREEN}₹{inc:>10,.2f}{C.RESET} "
              f"{C.RED}₹{exp:>10,.2f}{C.RESET} "
              f"{nc}₹{abs(net):>10,.2f}{C.RESET} "
              f"{bud_str:>12}  {usage_str}")

# ─────────────────────────────────────────────
#  DB Config Wizard
# ─────────────────────────────────────────────
def get_db_config():
    print(f"\n{C.CYAN}{C.BOLD}  MySQL Connection Setup{C.RESET}")
    print(f"  {C.DIM}(Press Enter to use defaults){C.RESET}\n")
    host     = prompt("Host     [localhost]") or "localhost"
    port_str = prompt("Port     [3306]") or "3306"
    user     = prompt("User     [root]") or "root"
    password = prompt("Password")
    db       = prompt("Database [budget_tracker]") or "budget_tracker"
    return {
        "host":     host,
        "port":     int(port_str),
        "user":     user,
        "password": password,
        "database": db,
    }

# ─────────────────────────────────────────────
#  Main Menu
# ─────────────────────────────────────────────
MENU = """
  {bold}MAIN MENU{reset}
  {dim}─────────────────────────────────{reset}
  {g}1{r}  Add Income
  {g}2{r}  Add Expense
  {g}3{r}  Remove Transaction
  {g}4{r}  List Transactions
  {dim}─────────────────────────────────{reset}
  {g}5{r}  Add Tag
  {g}6{r}  Remove Tag
  {g}7{r}  List Tags
  {g}8{r}  Set Tag Budget
  {dim}─────────────────────────────────{reset}
  {g}9{r}  Account Summary
  {g}10{r} Summary by Tag
  {dim}─────────────────────────────────{reset}
  {g}0{r}  Exit
"""

def main():
    print(f"\n{C.CYAN}{C.BOLD}")
    print("  ╔══════════════════════════════════════╗")
    print("  ║        💰  BUDGET TRACKER  💰        ║")
    print("  ╚══════════════════════════════════════╝")
    print(C.RESET)

    config = get_db_config()

    print(f"\n{C.DIM}  Connecting to MySQL...{C.RESET}")
    try:
        setup_database(config)
        conn = get_connection(config)
        success(f"Connected to '{config['database']}' on {config['host']}:{config['port']}")
    except Error as e:
        error(f"Could not connect: {e}")
        sys.exit(1)

    actions = {
        "1":  lambda: add_transaction(conn, "income"),
        "2":  lambda: add_transaction(conn, "expense"),
        "3":  lambda: remove_transaction(conn),
        "4":  lambda: list_transactions(conn),
        "5":  lambda: add_tag(conn),
        "6":  lambda: remove_tag(conn),
        "7":  lambda: list_tags(conn),
        "8":  lambda: set_tag_budget(conn),
        "9":  lambda: summary_account(conn),
        "10": lambda: summary_by_tag(conn),
    }

    while True:
        print(MENU.format(
            bold=C.BOLD, reset=C.RESET, dim=C.DIM,
            g=C.GREEN, r=C.RESET
        ))
        choice = prompt("Choose an option").strip()
        if choice == "0":
            print(f"\n{C.CYAN}  Goodbye! 👋{C.RESET}\n")
            conn.close()
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

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{C.CYAN}  Exiting... Goodbye!{C.RESET}\n")
        sys.exit(0)