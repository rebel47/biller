# Biller - Your friendly Bill Management System

## Overview

The **Biller** is a Streamlit-based web application designed to help users manage and track their bills efficiently. The application allows users to upload images of their bills, extract relevant information using Google's Gemini API, and store the data in a SQLite database. Users can also manually enter bill details, view their spending history, and categorize expenses.

## Features

- **User Authentication**: Secure login and registration system with password hashing.
- **Bill Upload**: Upload images of bills (JPG, JPEG, PNG) to automatically extract details such as total amount, date, and categorized items.
- **Manual Entry**: Manually enter bill details including date, category, amount, and description.
- **Expense Tracking**: View all bills in a tabular format with options to delete entries.
- **Monthly Summary**: Display a summary of expenses grouped by month, sorted by the latest month first.
- **Categorization**: Automatically categorize items into predefined categories (grocery, utensil, clothing, miscellaneous) using Gemini API.
- **Total Amount Calculation**: Calculate and display the total amount of all bills.

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.7+
- Streamlit
- SQLite3
- Google Generative AI API
- Python-dotenv
- Pillow (PIL)
- Pandas

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/rebel47/biller.git
   cd biller
   ```

2. **Install the required Python packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   - Create a `.env` file in the root directory.
   - Add your Google API key to the `.env` file:
     ```plaintext
     GOOGLE_API_KEY=your_google_api_key_here
     ```

## Usage

1. **Run the Streamlit application**:
   ```bash
   streamlit run app.py
   ```

2. **Register a new user**:
   - Navigate to the registration section.
   - Enter your username, email, name, and password.
   - Click "Register" to create a new account.

3. **Login**:
   - Enter your username and password.
   - Click "Login" to access the application.

4. **Upload a bill**:
   - Use the file uploader to upload an image of your bill.
   - The application will automatically extract the total amount, date, and categorized items.
   - Review the extracted information and click "Save Bill" to store it in the database.

5. **Manual Entry**:
   - Enter the date, category, amount, and description manually.
   - Click "Save Manual Entry" to store the information in the database.

6. **View and Manage Bills**:
   - View all bills in a tabular format.
   - Use the checkboxes to select bills for deletion and click "Delete Selected Items" to remove them.

7. **View Monthly Summary**:
   - Check the monthly summary to see your spending history grouped by month.

## Database Schema

### User Credentials Database (`user_credentials.db`)
- **Table**: `users`
  - `id`: INTEGER (Primary Key, Auto Increment)
  - `username`: TEXT (Unique)
  - `email`: TEXT
  - `name`: TEXT
  - `password`: TEXT (Hashed)

### User Bills Database (`bills_username.db`)
- **Table**: `bills`
  - `id`: INTEGER (Primary Key, Auto Increment)
  - `date`: TEXT
  - `category`: TEXT
  - `amount`: REAL
  - `description`: TEXT


## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Streamlit](https://streamlit.io/) for the web application framework.
- [Google Generative AI](https://ai.google.dev/) for the bill extraction API.
- [SQLite](https://www.sqlite.org/) for the database management.


Thank you for using the Bill Tracker Application! We hope it helps you manage your expenses more effectively.
