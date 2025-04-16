# Deploying Budget AI on Render.com

This guide explains how to deploy the Budget AI application on Render.com.

## Prerequisites

1. A Render.com account
2. A PostgreSQL database (you can create one on Render or use your Google Cloud PostgreSQL instance)
3. Your GitHub repository with the Budget AI code

## Deployment Steps

### 1. Set Up PostgreSQL Database

You have two options for the database:

#### Option A: Use Your Existing Google Cloud SQL Database

If you want to use your existing Google Cloud SQL PostgreSQL database:
- Make sure your database has public access enabled (shown in your screenshots)
- Note your database connection details:
  - Host: 34.60.72.203 (from your screenshots)
  - Port: 5432
  - Database Name: your database name
  - Username: your username
  - Password: your password

#### Option B: Create a New PostgreSQL Database on Render

Alternatively, you can create a new PostgreSQL database on Render:
1. In your Render dashboard, go to "New" > "PostgreSQL"
2. Configure the database settings (name, region, plan)
3. Create the database and note the connection details provided

### 2. Deploy the Web Service

1. Log in to your Render.com account
2. Click on "New" > "Blueprint" (to use the render.yaml configuration)
3. Connect your GitHub repository containing the Budget AI code
4. Render will detect the render.yaml file and configure the services
5. Configure the environment variables:
   - `DATABASE_URL`: Your PostgreSQL connection string (format: `postgres://username:password@host:5432/database_name`)
   - `ENVIRONMENT`: Set to `production`
   - `PLAID_CLIENT_ID`: Your Plaid client ID
   - `PLAID_SECRET`: Your Plaid secret
   - `PLAID_ENV`: Your Plaid environment (sandbox, development, or production)
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `PERPLEXITY_API_KEY`: Your Perplexity API key (if used)
6. Click "Apply" to start the deployment

### 3. Initial Setup After Deployment

Once deployed, you need to perform initial setup:
1. Access your app at the provided Render URL
2. Create an admin account using the application's interface
3. Import any necessary data

## Verify Deployment

After deployment, verify that:
1. The application is accessible through the Render URL
2. You can log in and create an account
3. The database connection is working properly
4. All features are functioning as expected

## Troubleshooting

If you encounter issues:
1. Check the Render logs for error messages
2. Verify your environment variables are correctly set
3. Ensure your database connection string is correct
4. Check that all required services (Plaid, OpenAI, etc.) are properly configured

## Additional Resources

- [Render Web Services Documentation](https://render.com/docs/web-services)
- [Render PostgreSQL Documentation](https://render.com/docs/databases)
- [Render Environment Variables](https://render.com/docs/environment-variables)