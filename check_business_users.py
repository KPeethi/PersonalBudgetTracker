"""
Script to check business users in the expense tracker database.
"""
from main import app, db
from models import User, BusinessUpgradeRequest

def check_business_users():
    """Check business users in the system"""
    with app.app_context():
        # Check business users
        business_users = User.query.filter_by(is_business_user=True).all()
        print(f"Found {len(business_users)} business users:")
        for user in business_users:
            print(f"User: {user.username}, Email: {user.email}")
            
        # Check business upgrade requests
        requests = BusinessUpgradeRequest.query.all()
        print(f"\nFound {len(requests)} business upgrade requests:")
        for req in requests:
            if req.user:
                print(f"User: {req.user.username}, Status: {req.status}")
            else:
                print(f"Request ID: {req.id}, Status: {req.status} (No user associated)")

if __name__ == "__main__":
    check_business_users()