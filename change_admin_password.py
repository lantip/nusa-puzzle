from werkzeug.security import generate_password_hash
from app import app
from models import User, db

def change_admin_password(new_password):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("No admin user found.")
            return

        admin.password = generate_password_hash(new_password)
        db.session.commit()
        print("Admin password updated successfully.")

if __name__ == '__main__':
    import getpass
    new_password = getpass.getpass("Enter new admin password: ")
    confirm = getpass.getpass("Confirm new admin password: ")

    if new_password == confirm:
        change_admin_password(new_password)
    else:
        print("Passwords do not match. Try again.")