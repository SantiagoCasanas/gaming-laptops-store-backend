# Gaming Laptops Store Backend

A Django REST API backend for an e-commerce platform specializing in gaming laptops and computer hardware. This project provides a comprehensive product catalog system with support for multiple product variants, pricing, inventory management, and media handling.

## 🚀 Features

- **Product Management**: Flexible catalog system with brands, categories, and product variants
- **Inventory Control**: Track stock status (in stock, on the way, by importation, out of stock)
- **Product Variants**: Support for different conditions (new, open box, refurbished, used)
- **Media Handling**: Image upload and management for products
- **Discount System**: Apply discounts to specific product variants
- **Admin Interface**: Full Django admin panel for content management
- **API Ready**: Built with Django REST Framework for frontend integration

## 📋 Prerequisites

Before you begin, make sure you have the following installed on your computer:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **PostgreSQL** - [Download PostgreSQL](https://www.postgresql.org/download/)
- **Git** - [Download Git](https://git-scm.com/downloads/)

## 🛠️ Installation & Setup

### Step 1: Clone the Repository

Open your terminal (Command Prompt on Windows, Terminal on Mac/Linux) and run:

```bash
git clone https://github.com/your-username/gaming-laptops-store-backend.git
cd gaming-laptops-store-backend
```

### Step 2: Create a Virtual Environment

A virtual environment keeps your project dependencies separate from other Python projects.

**On Windows:**
```bash
python -m venv env
env\Scripts\activate
```

**On Mac/Linux:**
```bash
python3 -m venv env
source env/bin/activate
```

You should see `(env)` at the beginning of your terminal prompt, indicating the virtual environment is active.

### Step 3: Install Dependencies

Install all the required Python packages:

```bash
pip install -r requirements.txt
```

### Step 4: Set Up PostgreSQL Database

1. **Start PostgreSQL service** on your computer
2. **Create a new database**:
   - Open PostgreSQL command line (psql) or use a GUI tool like pgAdmin
   - Create a database named `gaming_store_db`:
   ```sql
   CREATE DATABASE gaming_store_db;
   ```

### Step 5: Configure Environment Variables

1. **Copy the environment file**:
   ```bash
   cp .env.example .env
   ```
   (If `.env.example` doesn't exist, create a new `.env` file)

2. **Edit the `.env` file** with your database credentials:
   ```
   # Django Settings
   SECRET_KEY='your-secret-key-here'
   DEBUG=True

   # Database Settings
   DB_NAME='gaming_store_db'
   DB_USER='your_postgres_username'
   DB_PASSWORD='your_postgres_password'
   DB_HOST='localhost'
   DB_PORT='5432'
   ```

   Replace the values with your actual PostgreSQL credentials.

### Step 6: Set Up the Database

Run these commands to create the database tables:

```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 7: Create an Admin User

Create a superuser account to access the admin panel:

```bash
python manage.py createsuperuser
```

Follow the prompts to enter a username, email, and password.

### Step 8: Run the Development Server

Start the Django development server:

```bash
python manage.py runserver
```

You should see output similar to:
```
System check identified no issues (0 silenced).
[Date] [Time] - Django version 5.2.6, using settings 'config.settings'
Starting development server at http://127.0.0.1:8000/
```

## 🎉 Accessing the Application

- **Admin Panel**: Visit `http://127.0.0.1:8000/admin/` and log in with your superuser credentials
- **API**: The API endpoints will be available at `http://127.0.0.1:8000/api/` (once implemented)

## 📊 Using the Admin Panel

1. Go to `http://127.0.0.1:8000/admin/`
2. Log in with your superuser credentials
3. You can manage:
   - **Brands**: Add laptop manufacturers (ASUS, MSI, etc.)
   - **Categories**: Create product categories (Laptops, Graphics Cards, etc.)
   - **Base Products**: Add product models with specifications
   - **Product Variants**: Create different versions with pricing and conditions
   - **Images**: Upload product photos
   - **Discounts**: Apply special pricing

## 🗂️ Project Structure

```
gaming-laptops-store-backend/
├── config/              # Django project configuration
├── products/            # Product management app
├── users/               # User management app
├── media/               # Uploaded files (product images)
├── env/                 # Virtual environment (created after setup)
├── manage.py            # Django management script
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
└── README.md           # This file
```

## 🔧 Development Commands

```bash
# Run the development server
python manage.py runserver

# Create new database migrations
python manage.py makemigrations

# Apply migrations to database
python manage.py migrate

# Create a superuser account
python manage.py createsuperuser

# Open Django shell for debugging
python manage.py shell

# Collect static files (for production)
python manage.py collectstatic
```

## ⚠️ Troubleshooting

### Database Connection Issues
- Make sure PostgreSQL is running
- Verify your database credentials in the `.env` file
- Ensure the database `gaming_store_db` exists

### Virtual Environment Issues
- Make sure you activated the virtual environment: `source env/bin/activate` (Mac/Linux) or `env\Scripts\activate` (Windows)
- You should see `(env)` in your terminal prompt

### Port Already in Use
- If port 8000 is busy, try: `python manage.py runserver 8001`

### Permission Errors
- On Mac/Linux, you might need to use `python3` instead of `python`
- Make sure you have write permissions in the project directory

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Need Help?

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Review the [Django documentation](https://docs.djangoproject.com/)
3. Open an issue in this repository