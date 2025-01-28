import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import os
from PIL import Image, UnidentifiedImageError
import pillow_heif
import io
import re
import hashlib
import time

# Enable HEIC support
pillow_heif.register_heif_opener()

# Register custom adapter for datetime objects
def adapt_datetime(dt):
    return dt.isoformat()

def convert_datetime(ts):
    return datetime.fromisoformat(ts.decode())

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)

# Load environment variables and configure Gemini API
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize SQLite database for user credentials
user_credentials_db_path = "user_credentials.db"
user_conn = sqlite3.connect(user_credentials_db_path)
user_c = user_conn.cursor()
user_c.execute('''CREATE TABLE IF NOT EXISTS users
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT UNIQUE,
                   email TEXT,
                   name TEXT,
                   password TEXT)''')
user_conn.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def convert_image_format(uploaded_file):
    try:
        image = Image.open(uploaded_file)
        buffer = io.BytesIO()
        image = image.convert("RGB")
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        return buffer, "image/jpeg"
    except UnidentifiedImageError:
        raise ValueError("Unsupported image format. Please upload PNG, JPEG, or HEIC images.")

def input_image_setup(uploaded_file):
    converted_file, mime_type = convert_image_format(uploaded_file)
    bytes_data = converted_file.getvalue()
    return bytes_data, mime_type

def extract_amount(text):
    amount_pattern = r"Total Amount: €(\d+\.\d{2})"
    match = re.search(amount_pattern, text)
    if match:
        return float(match.group(1))
    return 0.0

def extract_categorized_items(text):
    items = []
    lines = text.split('\n')
    for line in lines:
        if line.startswith('-'):
            item_pattern = r"- (.*?): €(\d+\.\d{2}) \(Category: (.*?)\)"
            match = re.match(item_pattern, line)
            if match:
                item_name = match.group(1)
                item_amount = float(match.group(2))
                item_category = match.group(3)
                items.append({
                    'item': item_name,
                    'amount': item_amount,
                    'category': item_category
                })
    return items

def process_bill_with_gemini(image_data, mime_type):
    try:
        model = genai.GenerativeModel(
            "gemini-1.5-flash",
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        )

        prompt = """
        Please analyze this bill image and extract the following information:
        1. Total amount
        2. Date of purchase
        3. Individual items and their prices
        
        Format the response as follows:
        Total Amount: €XX.XX
        Date: YYYY-MM-DD
        Items:
        - Item 1: €XX.XX (Category: grocery/utensil/clothing/miscellaneous)
        - Item 2: €XX.XX (Category: grocery/utensil/clothing/miscellaneous)
        """

        generation_config = {
            "temperature": 0.1,
            "top_p": 1,
            "top_k": 32,
            "max_output_tokens": 2048,
        }
        
        response = model.generate_content(
            [
                {"mime_type": mime_type, "data": image_data},
                prompt
            ],
            generation_config=generation_config
        )

        amount = extract_amount(response.text)
        categorized_items = extract_categorized_items(response.text)
        return response.text, amount, categorized_items

    except Exception as e:
        st.error(f"Error processing bill with Gemini: {str(e)}")
        return None, 0.0, None


def delete_item(item_id):
    c.execute("DELETE FROM bills WHERE id = ?", (item_id,))
    conn.commit()
    st.success("Item deleted successfully!")

# Initialize session state
if "authentication_status" not in st.session_state:
    st.session_state["authentication_status"] = False
if "username" not in st.session_state:
    st.session_state["username"] = None

# Login/Register Section
if not st.session_state.get("authentication_status"):
    st.title("Welcome to Biller")
    st.text("- Developed By: Mohammad Ayaz Alam")
    
    auth_option = st.radio(
        "Choose an option",
        ["Login", "Register"],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )

    if auth_option == "Login":
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            login_submitted = st.form_submit_button("Login")

            if login_submitted:
                user_c.execute("SELECT password FROM users WHERE username = ?", (username,))
                result = user_c.fetchone()

                if result and hash_password(password) == result[0]:
                    st.session_state["authentication_status"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.header("Register")
        with st.form("register_form"):
            register_username = st.text_input("Username", key="register_username")
            register_email = st.text_input("Email", key="register_email")
            register_name = st.text_input("Name", key="register_name")
            register_password = st.text_input("Password", type="password", key="register_password")
            register_confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password")
            register_submitted = st.form_submit_button("Register")

            if register_submitted:
                if register_password != register_confirm_password:
                    st.error("Passwords do not match!")
                else:
                    try:
                        hashed_password = hash_password(register_password)
                        user_c.execute("INSERT INTO users (username, email, name, password) VALUES (?, ?, ?, ?)",
                                     (register_username, register_email, register_name, hashed_password))
                        user_conn.commit()
                        st.success("Registration successful! Please login.")
                    except sqlite3.IntegrityError:
                        st.error("Username already exists")

# Main Application (After Authentication)
if st.session_state.get("authentication_status"):
    st.write(f'Welcome *{st.session_state["username"]}*')

    if st.button("Logout"):
        st.session_state["authentication_status"] = False
        st.session_state["username"] = None
        st.rerun()

    # Initialize user's database
    user_db_path = f"bills_{st.session_state['username']}.db"
    conn = sqlite3.connect(user_db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bills
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  category TEXT,
                  amount REAL,
                  description TEXT)''')
    conn.commit()

    st.title("Biller")

    # File upload with processing message
    # Upload image
    uploaded_file = st.file_uploader("Upload a photo of your bill", type=["jpg", "jpeg", "png", "heic"])
    # In the main application section, update the saving logic:
    if uploaded_file is not None:
        try:
            with st.spinner("Processing image..."):
                image_data, mime_type = input_image_setup(uploaded_file)
                extracted_text, amount, categorized_items = process_bill_with_gemini(image_data, mime_type)

            if extracted_text:
                st.success("Image processed successfully!")
                
                # Pre-fill the amount field with extracted amount
                #amount = st.number_input("Enter the amount", value=amount)
                description = st.text_input("Enter a description", value=extracted_text)

                # Save to database
                if st.button("Save Bill"):
                    date = datetime.now().strftime("%Y-%m-%d")
                    if categorized_items:
                        # Save each categorized item separately
                        for item in categorized_items:
                            c.execute("INSERT INTO bills (date, category, amount, description) VALUES (?, ?, ?, ?)",
                                    (date, item['category'], item['amount'], item['item']))
                    else:
                        # Save the entire bill as one entry
                        c.execute("INSERT INTO bills (date, category, amount, description) VALUES (?, ?, ?, ?)",
                                (date, "miscellaneous", amount, description))
                    conn.commit()
                    st.success("Bill saved successfully!")
        except Exception as e:
            st.error(f"Error: {str(e)}")

    # Manual Entry Section
    st.header("Manual Entry")
    manual_date = st.date_input("Date")
    manual_category = st.selectbox("Category ", ["grocery", "utensil", "clothing", "miscellaneous"])
    manual_amount = st.number_input("Amount ", value=0.0)
    manual_description = st.text_input("Description ")

    if st.button("Save Manual Entry"):
        c.execute("INSERT INTO bills (date, category, amount, description) VALUES (?, ?, ?, ?)",
                  (manual_date, manual_category, manual_amount, manual_description))
        conn.commit()
        st.success("Entry saved!")

    # Display Bills
    st.header("All Bills")
    bills_df = pd.read_sql_query("SELECT * FROM bills", conn)
    if not bills_df.empty:
        bills_df['Delete'] = False
        edited_df = st.data_editor(
            bills_df,
            column_config={
                "Delete": st.column_config.CheckboxColumn("Delete", help="Select to delete")
            },
            hide_index=True,
            use_container_width=True,
        )

        if st.button("Delete Selected"):
            items_to_delete = edited_df[edited_df['Delete']]['id'].tolist()
            for item_id in items_to_delete:
                delete_item(item_id)
            st.rerun()

    # Summary Section
    total_amount = bills_df['amount'].sum()
    st.write(f"Total Amount: {total_amount}")

    # Monthly Summary
    st.header("Monthly Summary")
    if not bills_df.empty:
        bills_df['date'] = pd.to_datetime(bills_df['date'])
        bills_df['month'] = bills_df['date'].dt.to_period('M')
        monthly_summary = bills_df.groupby('month')['amount'].sum().reset_index()
        monthly_summary = monthly_summary.sort_values(by='month', ascending=False)
        st.write(monthly_summary)

    conn.close()

user_conn.close()