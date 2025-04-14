-- SQL Server script to create the budget_ai database
-- Run this in SQL Server Management Studio before running setup_mssql.py

-- Check if database exists, drop if it does and user confirms
-- UNCOMMENT THE LINES BELOW IF YOU WANT TO DROP AN EXISTING DATABASE
-- USE master;
-- GO
-- IF DB_ID('budget_ai') IS NOT NULL
-- BEGIN
--     DROP DATABASE budget_ai;
-- END
-- GO

-- Create the database
CREATE DATABASE budget_ai;
GO

-- Use the database
USE budget_ai;
GO

-- Create a login for the application if needed
-- UNCOMMENT AND MODIFY THE LINES BELOW IF YOU WANT TO CREATE A SPECIFIC LOGIN
-- CREATE LOGIN budget_app_user WITH PASSWORD = 'YourStrongPassword123!';
-- GO

-- Create a database user and grant permissions
-- UNCOMMENT AND MODIFY THE LINES BELOW IF YOU WANT TO CREATE A SPECIFIC USER
-- CREATE USER budget_app_user FOR LOGIN budget_app_user;
-- GO
-- EXEC sp_addrolemember 'db_owner', 'budget_app_user';
-- GO

-- Note: By default, the application will use Windows Authentication
-- This means your Windows account needs permission to access the database

PRINT 'Database budget_ai created successfully!';
GO