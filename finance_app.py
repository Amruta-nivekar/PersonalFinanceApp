import sqlite3
import hashlib
from datetime import datetime

# Connect to the SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('finance_app.db')
cursor = conn.cursor()

# --- 1. Create Users Table ---
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  hashed_password TEXT NOT NULL)''')
conn.commit()
print("Checked/Created 'users' table.")

# --- 2. Create Transactions Table ---
cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  type TEXT NOT NULL CHECK(type IN ('Income', 'Expense')),
                  amount REAL NOT NULL,
                  category TEXT NOT NULL,
                  description TEXT,
                  date TEXT NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
conn.commit()
print("Checked/Created 'transactions' table.")

# --- 3. Create Budgets Table ---
cursor.execute('''CREATE TABLE IF NOT EXISTS budgets (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  category TEXT NOT NULL,
                  amount REAL NOT NULL,
                  month INTEGER NOT NULL,
                  year INTEGER NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
conn.commit()
print("Checked/Created 'budgets' table.")

# --- User Registration and Login ---
def register_user():
    username = input("Enter a username: ").strip()
    password = input("Enter a password: ").strip()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)",
                       (username, hashed_password))
        conn.commit()
        print("User registered successfully!")
    except sqlite3.IntegrityError:
        print("Username already exists. Try a different one.")

def login_user():
    username = input("Enter your username: ").strip()
    password = input("Enter your password: ").strip()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    cursor.execute("SELECT id, hashed_password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    if result and result[1] == hashed_password:
        print("Login successful!")
        return result[0]  # Return user_id
    else:
        print("Invalid username or password.")
        return None

# --- Transactions Management ---
def add_transaction(user_id, trans_type, amount, category, description=""):
    if trans_type.lower() == "expense":
        month = datetime.now().month
        year = datetime.now().year
        
        cursor.execute('''SELECT SUM(amount) FROM transactions
                          WHERE user_id = ? AND type = 'Expense' AND category = ? 
                          AND strftime('%m', date) = ? AND strftime('%Y', date) = ?''', 
                       (user_id, category, f"{month:02}", str(year)))
        total_expenses = cursor.fetchone()[0] or 0

        cursor.execute('''SELECT amount FROM budgets 
                          WHERE user_id = ? AND category = ? AND month = ? AND year = ?''', 
                       (user_id, category, month, year))
        budget = cursor.fetchone()
        
        if budget and (total_expenses + amount > budget[0]):
            print(f"Warning: Adding this expense will exceed your budget for {category}!")
    
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT INTO transactions (user_id, type, amount, category, description, date)
                      VALUES (?, ?, ?, ?, ?, ?)''', 
                   (user_id, trans_type, amount, category, description, date))
    conn.commit()
    print("Transaction added successfully.")

def update_transaction(trans_id, user_id, new_amount=None, new_category=None, new_description=None):
    cursor.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", (trans_id, user_id))
    if not cursor.fetchone():
        print("Transaction not found or you don't have permission to modify it.")
        return
    
    if new_amount is not None:
        cursor.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amount, trans_id))
    if new_category:
        cursor.execute("UPDATE transactions SET category = ? WHERE id = ?", (new_category, trans_id))
    if new_description is not None:
        cursor.execute("UPDATE transactions SET description = ? WHERE id = ?", (new_description, trans_id))
    conn.commit()
    print("Transaction updated successfully.")

def delete_transaction(trans_id, user_id):
    cursor.execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?", (trans_id, user_id))
    if not cursor.fetchone():
        print("Transaction not found or you don't have permission to delete it.")
        return
    
    cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
    conn.commit()
    print("Transaction deleted successfully.")

def view_transactions(user_id):
    cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC", (user_id,))
    transactions = cursor.fetchall()
    if not transactions:
        print("No transactions found.")
        return
    print("\n--- Your Transactions ---")
    for trans in transactions:
        print(f"ID: {trans[0]}, Type: {trans[2]}, Amount: {trans[3]}, Category: {trans[4]}, Description: {trans[5]}, Date: {trans[6]}")

# --- Budget Management ---
def set_budget(user_id, category, amount, month, year):
    cursor.execute('''SELECT id FROM budgets 
                      WHERE user_id = ? AND category = ? AND month = ? AND year = ?''', 
                   (user_id, category, month, year))
    result = cursor.fetchone()
    
    if result:
        cursor.execute('''UPDATE budgets SET amount = ? 
                          WHERE id = ?''', (amount, result[0]))
        print("Budget updated successfully.")
    else:
        cursor.execute('''INSERT INTO budgets (user_id, category, amount, month, year) 
                          VALUES (?, ?, ?, ?, ?)''', 
                       (user_id, category, amount, month, year))
        print("Budget set successfully.")
    
    conn.commit()

def view_budgets(user_id, month, year):
    cursor.execute('''SELECT category, amount FROM budgets 
                      WHERE user_id = ? AND month = ? AND year = ?''', 
                   (user_id, month, year))
    budgets = cursor.fetchall()
    
    if not budgets:
        print("No budgets set for this month.")
        return
    
    print(f"\n--- Budgets for {year}-{month:02} ---")
    for budget in budgets:
        print(f"Category: {budget[0]}, Amount: {budget[1]}")

# --- Financial Reporting ---
def generate_monthly_report(user_id, year, month):
    cursor.execute('''SELECT type, SUM(amount) FROM transactions
                      WHERE user_id = ? AND strftime('%Y', date) = ? AND strftime('%m', date) = ?
                      GROUP BY type''', (user_id, str(year), f"{month:02}"))
    results = cursor.fetchall()
    income = 0
    expenses = 0
    for row in results:
        if row[0].lower() == 'income':
            income = row[1]
        elif row[0].lower() == 'expense':
            expenses = row[1]
    savings = income - expenses
    print(f"\n--- Financial Report for {year}-{month:02} ---")
    print(f"Total Income: {income}")
    print(f"Total Expenses: {expenses}")
    print(f"Savings: {savings}")

def generate_yearly_report(user_id, year):
    cursor.execute('''SELECT type, SUM(amount) FROM transactions
                      WHERE user_id = ? AND strftime('%Y', date) = ?
                      GROUP BY type''', (user_id, str(year)))
    results = cursor.fetchall()
    income = 0
    expenses = 0
    for row in results:
        if row[0].lower() == 'income':
            income = row[1]
        elif row[0].lower() == 'expense':
            expenses = row[1]
    savings = income - expenses
    print(f"\n--- Financial Report for {year} ---")
    print(f"Total Income: {income}")
    print(f"Total Expenses: {expenses}")
    print(f"Savings: {savings}")

# --- User Menu ---
def user_menu(user_id):
    while True:
        print("\n--- User Menu ---")
        print("1. Add Transaction")
        print("2. Update Transaction")
        print("3. Delete Transaction")
        print("4. View Transactions")
        print("5. Generate Monthly Report")
        print("6. Generate Yearly Report")
        print("7. Set Budget")
        print("8. View Budgets")
        print("9. Logout")
        choice = input("Choose an option: ").strip()

        if choice == '1':
            trans_type = input("Enter transaction type (Income/Expense): ").strip().capitalize()
            if trans_type not in ['Income', 'Expense']:
                print("Invalid transaction type. Please enter 'Income' or 'Expense'.")
                continue
            try:
                amount = float(input("Enter amount: ").strip())
            except ValueError:
                print("Invalid amount. Please enter a numeric value.")
                continue
            category = input("Enter category: ").strip()
            description = input("Enter description (optional): ").strip()
            add_transaction(user_id, trans_type, amount, category, description)
        
        elif choice == '2':
            try:
                trans_id = int(input("Enter transaction ID to update: ").strip())
            except ValueError:
                print("Invalid ID. Please enter a numeric value.")
                continue
            new_amount_input = input("Enter new amount (leave blank to skip): ").strip()
            new_amount = float(new_amount_input) if new_amount_input else None
            new_category = input("Enter new category (leave blank to skip): ").strip() or None
            new_description = input("Enter new description (leave blank to skip): ").strip() or None
            update_transaction(trans_id, user_id, new_amount, new_category, new_description)

        elif choice == '3':
            try:
                trans_id = int(input("Enter transaction ID to delete: ").strip())
            except ValueError:
                print("Invalid ID. Please enter a numeric value.")
                continue
            confirm = input(f"Are you sure you want to delete transaction ID {trans_id}? (y/n): ").strip().lower()
            if confirm == 'y':
                delete_transaction(trans_id, user_id)
            else:
                print("Deletion canceled.")

        elif choice == '4':
            view_transactions(user_id)

        elif choice == '5':
            year = input("Enter year (YYYY): ")
            month = input("Enter month (1-12): ")
            try:
                year = int(year)
                month = int(month)
                generate_monthly_report(user_id, year, month)
            except ValueError:
                print("Invalid input. Please enter numeric values for year and month.")

        elif choice == '6':
            year = input("Enter year (YYYY): ")
            try:
                year = int(year)
                generate_yearly_report(user_id, year)
            except ValueError:
                print("Invalid input. Please enter a numeric value for year.")

        elif choice == '7':
            category = input("Enter budget category: ").strip()
            try:
                amount = float(input("Enter budget amount: ").strip())
            except ValueError:
                print("Invalid amount. Please enter a numeric value.")
                continue
            try:
                month = int(input("Enter month (1-12): ").strip())
                year = int(input("Enter year (YYYY): ").strip())
            except ValueError:
                print("Invalid date. Please enter numeric values for month and year.")
                continue
            set_budget(user_id, category, amount, month, year)

        elif choice == '8':
            try:
                month = int(input("Enter month (1-12): ").strip())
                year = int(input("Enter year (YYYY): ").strip())
            except ValueError:
                print("Invalid date. Please enter numeric values for month and year.")
                continue
            view_budgets(user_id, month, year)

        elif choice == '9':
            print("Logged out successfully.")
            break

        else:
            print("Invalid choice. Please try again.")

# --- Main Menu ---
def main_menu():
    while True:
        print("\n--- Personal Finance Management ---")
        print("1. Register")
        print("2. Login")
        print("3. Exit")
        choice = input("Choose an option: ").strip()

        if choice == '1':
            register_user()
        elif choice == '2':
            user_id = login_user()
            if user_id:
                user_menu(user_id)
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

# Run the application
if __name__ == "__main__":
    main_menu()
    conn.close()
