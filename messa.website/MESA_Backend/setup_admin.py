"""Create or promote a MESA administrator account. Run: python setup_admin.py"""
import getpass
import sqlite3
from datetime import datetime, timezone
from app import DATABASE, MesaApplication, password_hash, valid_email


def main():
    MesaApplication()  # creates schema and performs safe role-column migration
    print("\nMESA Administrator Setup\n-------------------------")
    name = input("Administrator full name: ").strip()
    email = input("Administrator email: ").strip().lower()
    if len(name) < 2 or not valid_email(email):
        raise SystemExit("Please provide a valid name and email address.")
    password = getpass.getpass("Temporary administrator password (12+ characters): ")
    confirm = getpass.getpass("Confirm password: ")
    if not 12 <= len(password) <= 128 or password != confirm:
        raise SystemExit("Passwords must match and contain 12–128 characters.")
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(DATABASE) as db:
        row = db.execute("SELECT id FROM users WHERE email=? COLLATE NOCASE", (email,)).fetchone()
        if row:
            user_id = row[0]
            db.execute(
                """UPDATE users SET name=?,password_hash=?,role='super_admin',is_active=1,
                   must_change_password=1 WHERE id=?""",
                (name, password_hash(password), user_id),
            )
            print("Existing account promoted to administrator; customer history retained.")
        else:
            cursor = db.execute(
                """INSERT INTO users(name,email,password_hash,created_at,role,is_active,must_change_password)
                   VALUES(?,?,?,?, 'super_admin',1,1)""",
                (name, email, password_hash(password), now),
            )
            user_id = cursor.lastrowid
            print("Administrator account created.")
        db.execute(
            """INSERT INTO admin_audit(admin_user_id,action,target_type,target_id,details,created_at)
               VALUES(?,?,?,?,?,?)""",
            (user_id, "administrator_bootstrap", "user", str(user_id), "Administrator account set up locally.", now),
        )
    print("Sign in with the temporary password and choose a new password before using the dashboard.")

if __name__ == "__main__":
    main()
