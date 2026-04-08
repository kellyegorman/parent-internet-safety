import argparse
import uuid
from sqlalchemy import create_engine, text
from passlib.context import CryptContext
 
DATABASE_URL = "mysql+pymysql://root:ZNrabNeFJKmDjnbNgxoMJPjMiStFQcwH@trolley.proxy.rlwy.net:44931/railway"
 
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
 
 
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT * FROM users"
        )).fetchall()
 
    if not rows:
        print("\n⚠️  No users in the database yet. Use --create to add one.\n")
    else:
        print(f"\n{'─'*60}")
        print(f"  {'USERID':<16} {'USERNAME':<14} {'EMAIL'}")
        print(f"{'─'*60}")
        for r in rows:
            print(f"  {r[0]:<16} {r[1]:<14} {r[2]}")
        print(f"{'─'*60}\n")
        print("Use any of these emails with the password you set when creating the account.\n")
 
 
def create_user(email: str, username: str, password: str):
    if len(password) < 8:
        print("❌ Password must be at least 8 characters.")
        return
 
    userid = str(uuid.uuid4())[:15]
    hashed = pwd_context.hash(password)
 
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO users (userid, username, email, password_hash)
                VALUES (:userid, :username, :email, :password_hash)
            """), {
                "userid": userid,
                "username": username,
                "email": email,
                "password_hash": hashed,
            })
        print(f"\n✅ User created!")
        print(f"   Email:    {email}")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"\nYou can now log in with these credentials in the extension.\n")
    except Exception as e:
        if "Duplicate" in str(e):
            print(f"❌ A user with that email or username already exists.")
        else:
            print(f"❌ Error: {e}")
 
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",     action="store_true", help="List all users")
    parser.add_argument("--create",   action="store_true", help="Create a new user")
    parser.add_argument("--email",    type=str)
    parser.add_argument("--username", type=str)
    parser.add_argument("--password", type=str)
    args = parser.parse_args()
 
    if args.list:
        list_users()
    elif args.create:
        if not all([args.email, args.username, args.password]):
            print("❌ --create requires --email, --username, and --password")
        else:
            create_user(args.email, args.username, args.password)
    else:
        # Default: just list users
        list_users()
