# Budget AI: Step-by-Step Render Deployment Guide

This comprehensive guide provides detailed instructions on deploying the Budget AI application to Render.com from your GitHub repository.

## Prerequisites

Before starting deployment, ensure you have:

1. Created a GitHub repository containing your Budget AI code
2. A Render.com account (sign up at https://render.com if you don't have one)
3. Access to the environment variables and API keys used in your application

## Step 1: Prepare Your Repository

Ensure your GitHub repository includes the following files needed for Render deployment:

1. `render.yaml` (already created)
2. `Procfile` (already created)
3. `runtime.txt` (already created)
4. `.env.sample` (already created as a reference)

## Step 2: Connect GitHub to Render

1. Log in to your Render dashboard
2. Click on "New" in the top navigation
3. Select "Blueprint"
4. In the "Connect a repository" section, click "Connect" next to GitHub
5. Authorize Render to access your GitHub account
6. Select your Budget AI repository from the list

## Step 3: Configure the Blueprint

1. Render will automatically detect the `render.yaml` file
2. Review the services it will create (web service and optional PostgreSQL database)
3. Click "Apply Blueprint" to continue

## Step 4: Configure Environment Variables

After the Blueprint is applied, you'll need to configure environment variables for your web service:

1. Navigate to the web service in your Render dashboard
2. Click on "Environment" in the left sidebar
3. Add the following environment variables:

   ```
   DATABASE_URL=postgresql://neondb_owner:npg_Hclv1yP9IEeL@ep-lively-smoke-a5b0oxbb.us-east-2.aws.neon.tech/neondb?sslmode=require
   ENVIRONMENT=production
   SECRET_KEY=your-secure-secret-key
   PLAID_CLIENT_ID=your-plaid-client-id
   PLAID_SECRET=your-plaid-secret
   PLAID_ENV=sandbox
   OPENAI_API_KEY=your-openai-api-key
   PERPLEXITY_API_KEY=your-perplexity-api-key (if used)
   ```

   Replace the placeholder values with your actual API keys and secrets.

4. Click "Save Changes"

## Step 5: Deploy the Application

1. In your web service dashboard, click on "Manual Deploy"
2. Select "Deploy latest commit" or choose a specific commit from the dropdown
3. Click "Deploy"
4. Monitor the deployment logs for any errors

## Step 6: Verify the Deployment

Once deployment is complete:

1. Click on the URL provided by Render to access your application
2. Verify that you can load the login page
3. Attempt to create an account and log in
4. Test key features to ensure they're functioning correctly

## Step 7: Set Up Custom Domain (Optional)

To use a custom domain with your Budget AI application:

1. In your web service dashboard, click on "Settings"
2. Scroll down to the "Custom Domain" section
3. Click "Add Custom Domain"
4. Enter your domain name and follow the instructions to configure DNS settings

## Step 8: Configure Continuous Deployment (Optional)

By default, Render automatically deploys when you push to the main branch of your repository. To customize this behavior:

1. In your web service dashboard, click on "Settings"
2. Scroll to the "Build & Deploy" section
3. Configure your preferred branch and auto-deploy settings

## Troubleshooting Common Issues

### Database Connection Issues

If you encounter database connection problems:
- Verify your DATABASE_URL is correctly formatted
- Ensure your Neon PostgreSQL database is online and accessible
- Check if your IP address is allowed if you've set up IP restrictions

### Build Failures

If your build fails:
- Review the build logs for specific error messages
- Ensure your dependencies are correctly specified
- Verify that your application is compatible with the Python version specified in runtime.txt

### Runtime Errors

If your application deploys but doesn't run correctly:
- Check the logs in the Render dashboard
- Verify all environment variables are correctly set
- Ensure your application is configured to listen on the port provided by Render ($PORT environment variable)

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [Neon PostgreSQL Documentation](https://neon.tech/docs/)
- [Flask on Render Guide](https://render.com/docs/deploy-flask)

For additional support, refer to the Render.com documentation or contact their support team.