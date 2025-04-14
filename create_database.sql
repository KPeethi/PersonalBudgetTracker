-- Create Budget AI database
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'budget_ai')
BEGIN
    CREATE DATABASE budget_ai;
END
GO

USE budget_ai;
GO

-- Create users table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'users')
BEGIN
    CREATE TABLE users (
        id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(64) NOT NULL UNIQUE,
        email NVARCHAR(120) NOT NULL UNIQUE,
        password_hash NVARCHAR(256) NOT NULL,
        created_at DATETIME DEFAULT GETDATE(),
        is_admin BIT DEFAULT 0,
        is_business_user BIT DEFAULT 0,
        last_login DATETIME NULL,
        is_active BIT DEFAULT 1,
        is_suspended BIT DEFAULT 0,
        suspension_reason NVARCHAR(255) NULL
    );
END
GO

-- Create expenses table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'expenses')
BEGIN
    CREATE TABLE expenses (
        id INT IDENTITY(1,1) PRIMARY KEY,
        date DATE NOT NULL DEFAULT GETDATE(),
        description NVARCHAR(255) NOT NULL,
        category NVARCHAR(100) NOT NULL,
        amount FLOAT NOT NULL,
        user_id INT NULL REFERENCES users(id),
        created_at DATETIME DEFAULT GETDATE(),
        payment_method NVARCHAR(50) NULL,
        merchant NVARCHAR(100) NULL,
        excel_import_id INT NULL
    );
END
GO

-- Create budgets table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'budgets')
BEGIN
    CREATE TABLE budgets (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id),
        total_budget FLOAT DEFAULT 3000.0,
        food FLOAT DEFAULT 500.0,
        transportation FLOAT DEFAULT 300.0,
        entertainment FLOAT DEFAULT 200.0,
        bills FLOAT DEFAULT 800.0,
        shopping FLOAT DEFAULT 400.0,
        other FLOAT DEFAULT 800.0,
        month INT DEFAULT DATEPART(month, GETDATE()),
        year INT DEFAULT DATEPART(year, GETDATE()),
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Create business_upgrade_requests table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'business_upgrade_requests')
BEGIN
    CREATE TABLE business_upgrade_requests (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id),
        status NVARCHAR(20) DEFAULT 'pending',
        company_name NVARCHAR(100) NOT NULL,
        industry NVARCHAR(100) NULL,
        business_email NVARCHAR(120) NULL,
        phone_number NVARCHAR(20) NULL,
        reason NVARCHAR(MAX) NULL,
        admin_notes NVARCHAR(MAX) NULL,
        handled_by INT NULL REFERENCES users(id),
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Create excel_imports table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'excel_imports')
BEGIN
    CREATE TABLE excel_imports (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id),
        filename NVARCHAR(255) NOT NULL,
        file_path NVARCHAR(512) NOT NULL,
        file_size INT NOT NULL,
        num_rows INT NULL,
        records_imported INT NULL,
        status NVARCHAR(20) DEFAULT 'pending',
        error_message NVARCHAR(MAX) NULL,
        description NVARCHAR(MAX) NULL,
        upload_date DATETIME DEFAULT GETDATE(),
        completed_at DATETIME NULL,
        created_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Create user_preferences table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'user_preferences')
BEGIN
    CREATE TABLE user_preferences (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id),
        theme NVARCHAR(20) DEFAULT 'light',
        email_notifications BIT DEFAULT 1,
        push_notifications BIT DEFAULT 1,
        weekly_reports BIT DEFAULT 1,
        monthly_reports BIT DEFAULT 1,
        alerts_enabled BIT DEFAULT 1,
        alert_large_transactions BIT DEFAULT 1,
        alert_low_balance BIT DEFAULT 1,
        alert_upcoming_bills BIT DEFAULT 1,
        alert_saving_goal_progress BIT DEFAULT 1,
        alert_budget_exceeded BIT DEFAULT 1,
        large_transaction_threshold FLOAT DEFAULT 100.0,
        other_settings NVARCHAR(MAX) DEFAULT '{}',
        created_at DATETIME DEFAULT GETDATE(),
        updated_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Create notifications table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'notifications')
BEGIN
    CREATE TABLE notifications (
        id INT IDENTITY(1,1) PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id),
        title NVARCHAR(100) NOT NULL,
        message NVARCHAR(MAX) NOT NULL,
        notification_type NVARCHAR(50) DEFAULT 'info',
        is_read BIT DEFAULT 0,
        related_id INT NULL,
        related_type NVARCHAR(50) NULL,
        created_at DATETIME DEFAULT GETDATE()
    );
END
GO

-- Create receipts table if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'receipts')
BEGIN
    CREATE TABLE receipts (
        id INT IDENTITY(1,1) PRIMARY KEY,
        expense_id INT NULL REFERENCES expenses(id),
        user_id INT NOT NULL REFERENCES users(id),
        filename NVARCHAR(255) NOT NULL,
        file_path NVARCHAR(512) NOT NULL,
        file_size INT NOT NULL,
        file_type NVARCHAR(100) NOT NULL,
        upload_date DATETIME DEFAULT GETDATE(),
        description NVARCHAR(255) NULL
    );
END
GO

PRINT 'Budget AI database setup completed';