"""
Script to migrate business relationships in the database.
This script updates relationships between User and BusinessUpgradeRequest models.
"""
import os
import sys
import logging
from app import app, db
from models import User, BusinessUpgradeRequest

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_relationships():
    """Check existing relationships in the database."""
    with app.app_context():
        # Check users
        users = User.query.all()
        logger.info(f"Found {len(users)} users")
        
        # Check business upgrade requests
        requests = BusinessUpgradeRequest.query.all()
        logger.info(f"Found {len(requests)} business upgrade requests")
        
        # Check status of requests
        pending = BusinessUpgradeRequest.query.filter_by(status='pending').count()
        approved = BusinessUpgradeRequest.query.filter_by(status='approved').count()
        rejected = BusinessUpgradeRequest.query.filter_by(status='rejected').count()
        
        logger.info(f"Request status: Pending: {pending}, Approved: {approved}, Rejected: {rejected}")
        
        # Check relationships
        for req in requests:
            user = User.query.get(req.user_id)
            if user:
                logger.info(f"Request #{req.id} - User: {user.username} (ID: {user.id}), Status: {req.status}")
                if req.status == 'approved' and not user.is_business_user:
                    logger.warning(f"Inconsistency: User {user.username} has approved request but is not a business user")
            else:
                logger.error(f"Request #{req.id} - No user found with ID: {req.user_id}")
                
            if req.handled_by:
                admin = User.query.get(req.handled_by)
                if admin:
                    logger.info(f"Request #{req.id} - Handled by: {admin.username} (ID: {admin.id})")
                else:
                    logger.error(f"Request #{req.id} - No admin found with ID: {req.handled_by}")
        
        return {
            'users': len(users),
            'requests': len(requests),
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        }

def update_relationships():
    """Update relationships between users and business upgrade requests."""
    with app.app_context():
        try:
            # Update users with approved requests to be business users
            approved_requests = BusinessUpgradeRequest.query.filter_by(status='approved').all()
            logger.info(f"Found {len(approved_requests)} approved requests")
            
            updated_count = 0
            for req in approved_requests:
                user = User.query.get(req.user_id)
                if user and not user.is_business_user:
                    user.is_business_user = True
                    updated_count += 1
                    logger.info(f"Updated user {user.username} to business user based on approved request")
            
            # Commit changes
            if updated_count > 0:
                db.session.commit()
                logger.info(f"Updated {updated_count} users to business users")
            else:
                logger.info("No users needed updating")
                
            return {'updated_users': updated_count}
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating relationships: {str(e)}")
            return {'error': str(e)}

def main():
    """Main function to run the migration."""
    logger.info("Starting business relationships migration")
    
    # Check existing relationships
    status = check_relationships()
    logger.info(f"Relationship check completed: {status}")
    
    # Update relationships if needed
    if status['approved'] > 0:
        result = update_relationships()
        logger.info(f"Relationship update completed: {result}")
    else:
        logger.info("No approved requests found, skipping update")
    
    logger.info("Business relationships migration completed")
    return True

if __name__ == "__main__":
    main()