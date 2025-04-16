# Budget AI: Post-Deployment Operations Guide

This guide covers common operations and maintenance tasks for your Budget AI application after it has been successfully deployed to Render.com.

## Monitoring Your Application

### Viewing Logs

To monitor your application's performance and troubleshoot issues:

1. Log in to your Render dashboard
2. Navigate to your Budget AI web service
3. Click on "Logs" in the left sidebar
4. You can filter logs by:
   - Info: General application information
   - Error: Application errors
   - System: Render system events
   - Build: Deployment build logs

### Checking Service Status

To check the status of your application:

1. Go to your Render dashboard
2. Look at the status indicator next to your Budget AI service
3. Green indicates the service is running properly
4. Red indicates there's an issue with the service

### Setting Up Alerts (Render Teams Plan)

If you upgrade to Render's Teams plan, you can set up monitoring alerts:

1. Navigate to your Budget AI service
2. Click on "Monitoring" in the left sidebar
3. Configure alerts for metrics like CPU usage, memory usage, and response time

## Managing Your Application

### Restarting the Application

If you need to restart your application:

1. Go to your web service in the Render dashboard
2. Click the "Actions" dropdown in the top right
3. Select "Restart Service"

### Updating Environment Variables

To add or modify environment variables:

1. Navigate to your web service
2. Click on "Environment" in the left sidebar
3. Add, edit, or remove environment variables as needed
4. Click "Save Changes"
5. Your service will automatically restart with the new configuration

### Scaling Your Application

If you need to scale your application due to increased traffic:

1. Go to your web service
2. Click on "Settings" in the left sidebar
3. Scroll to the "Instance Type" section
4. Select a more powerful instance type based on your needs
5. Click "Save Changes"

## Database Management

### Connecting to Your Neon PostgreSQL Database

To connect directly to your Neon PostgreSQL database:

1. Visit the Neon dashboard at https://console.neon.tech/
2. Select your project
3. Click on "SQL Editor" to run queries directly in the browser
4. Alternatively, connect using a tool like pgAdmin with the connection details:
   - Host: ep-lively-smoke-a5b0oxbb.us-east-2.aws.neon.tech
   - Database: neondb
   - User: neondb_owner
   - Password: npg_Hclv1yP9IEeL
   - SSL Mode: require

### Database Backups

Neon PostgreSQL provides automated backups:

1. Visit your Neon dashboard
2. Navigate to your project
3. Go to the "Backups" section
4. Here you can view available backups and restore if needed

## Deployment Management

### Deploying Updates

When you make changes to your application:

1. Push the changes to your GitHub repository
2. Render will automatically detect changes and deploy the new version
3. Monitor the deployment logs to ensure it completes successfully

### Rollback to Previous Version

If you need to roll back to a previous version:

1. Go to your web service in the Render dashboard
2. Click on "Deploys" in the left sidebar
3. Find the previous working deployment
4. Click the three dots menu next to it
5. Select "Rollback to this deploy"

### Suspending Your Service

If you need to temporarily suspend your service:

1. Go to your web service
2. Click on "Settings"
3. Scroll down to the "Suspend Service" section
4. Click "Suspend Service"
5. To resume, click "Resume Service" when you're ready

## Security Management

### Rotating API Keys

It's good practice to periodically rotate your API keys:

1. Generate new keys for services like Plaid, OpenAI, etc.
2. Update the environment variables in your Render dashboard
3. Verify the application works with the new keys
4. Revoke the old API keys

### Rotating Your Application Secret Key

To rotate your application's SECRET_KEY:

1. Go to your web service's Environment settings
2. Generate a new secure random key
3. Update the SECRET_KEY variable
4. Save changes (this will log out all users as the session cookies will be invalidated)

## Troubleshooting Common Issues

### Application Crashes

If your application crashes after deployment:

1. Check the logs for error messages
2. Verify your environment variables are correct
3. Ensure your database connection is working
4. Check for any recent code changes that might have introduced bugs

### Database Connection Issues

If your application can't connect to the database:

1. Verify your DATABASE_URL is correct
2. Check if your Neon PostgreSQL instance is running
3. Ensure there are no network restrictions preventing connections
4. Check if you've reached connection limits

### Memory or CPU Usage Issues

If your application is slow or using excessive resources:

1. Check the logs for performance bottlenecks
2. Consider optimizing database queries
3. Implement caching if appropriate
4. Scale your instance type if needed

## Getting Help

If you need further assistance:

1. Render Documentation: https://render.com/docs
2. Neon PostgreSQL Documentation: https://neon.tech/docs/
3. Render Support: https://render.com/support
4. Flask Documentation: https://flask.palletsprojects.com/