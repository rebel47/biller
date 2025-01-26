import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
import os
from PIL import Image
import io
import re
# import json  # Commented out for now
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# Load environment variables and configure Gemini API
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Load authentication config
with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Initialize authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login widget
try:
    authenticator.login()
except Exception as e:
    st.error(e)

# Check authentication status
if st.session_state["authentication_status"]:
    # User is authenticated
    st.write(f'Welcome *{st.session_state["name"]}*')
    authenticator.logout()

    # Create a folder for user data if it doesn't exist
    user_data_folder = "user_data"
    os.makedirs(user_data_folder, exist_ok=True)

    # Initialize SQLite database for the user
    user_db_path = os.path.join(user_data_folder, f"bills_{st.session_state['username']}.db")
    conn = sqlite3.connect(user_db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bills
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  date TEXT,
                  category TEXT,
                  amount REAL,
                  description TEXT)''')
    conn.commit()

    # Function to convert image format and handle MIME type
    def convert_image_format(uploaded_file):
        try:
            image = Image.open(uploaded_file)
            buffer = io.BytesIO()
            image = image.convert("RGB")  # Ensure compatibility
            image.save(buffer, format="JPEG")
            buffer.seek(0)
            return buffer, "image/jpeg"
        except Exception as e:
            st.error(f"Error processing image: {e}")
            return None, None

    # Function to prepare image data
    def input_image_setup(uploaded_file):
        converted_file, mime_type = convert_image_format(uploaded_file)
        if converted_file:
            bytes_data = converted_file.getvalue()
            return bytes_data, mime_type
        return None, None

    # Function to extract amount from text
    def extract_amount(text):
        amount_pattern = r"Total Amount: €(\d+\.\d{2})"
        match = re.search(amount_pattern, text)
        if match:
            return float(match.group(1))
        return 0.0

    # Function to extract JSON from Gemini response (commented out for now)
    # def extract_json_from_response(response_text):
    #     try:
    #         # Find the JSON part in the response (if it exists)
    #         start_index = response_text.find('[')
    #         end_index = response_text.rfind(']') + 1
    #         json_str = response_text[start_index:end_index]
    #         return json.loads(json_str)
    #     except Exception as e:
    #         st.error(f"Error extracting JSON from response: {e}")
    #         return None

    # Function to process bill with Gemini API
    def process_bill_with_gemini(image_data, mime_type):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content([
                {"mime_type": mime_type, "data": image_data},
                "Extract the total amount, date, and items from this bill. Also, categorize each item into one of these categories: grocery, utensil, clothing, or miscellaneous. Return the results as a JSON list of dictionaries with 'item', 'category', and 'amount' keys.",
            ])
            extracted_text = response.text

            # Extract the total amount
            amount = extract_amount(extracted_text)

            # Parse categorized items from JSON string (commented out for now)
            # categorized_items = extract_json_from_response(extracted_text)
            categorized_items = None  # Placeholder for future use

            return extracted_text, amount, categorized_items
        except Exception as e:
            st.error(f"Error processing bill with Gemini: {e}")
            return None, 0.0, None

    # Function to delete an item from the database
    def delete_item(item_id):
        c.execute("DELETE FROM bills WHERE id = ?", (item_id,))
        conn.commit()
        st.success("Item deleted successfully!")

    # Streamlit App
    st.title("Bill Tracker Application")

    # Upload image
    uploaded_file = st.file_uploader("Upload a photo of your bill", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        # Prepare image data
        image_data, mime_type = input_image_setup(uploaded_file)
        if image_data and mime_type:
            # Process the bill using Gemini API
            extracted_text, amount, categorized_items = process_bill_with_gemini(image_data, mime_type)
            if extracted_text:
                # Commented out for now (debugging feature)
                # if st.checkbox("Show Extracted Text (for debugging)"):
                #     st.write("Extracted Information:", extracted_text)
                st.write("Categorized Items:", categorized_items)

                # Pre-fill the amount field
                amount = st.number_input("Enter the amount", value=amount)
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

    # Manual entry option
    st.header("Manual Entry")
    manual_date = st.date_input("Date")
    manual_category = st.selectbox("Category", ["grocery", "utensil", "clothing", "miscellaneous"])
    manual_amount = st.number_input("Amount", value=0.0)
    manual_description = st.text_input("Description")

    if st.button("Save Manual Entry"):
        c.execute("INSERT INTO bills (date, category, amount, description) VALUES (?, ?, ?, ?)",
                  (manual_date, manual_category, manual_amount, manual_description))
        conn.commit()
        st.success("Manual entry saved successfully!")

    # Display all bills with delete buttons
    st.header("All Bills")
    bills_df = pd.read_sql_query("SELECT * FROM bills", conn)

    # Add a delete button for each row
    if not bills_df.empty:
        bills_df['Delete'] = False  # Add a column for delete buttons
        edited_df = st.data_editor(
            bills_df,
            column_config={
                "Delete": st.column_config.CheckboxColumn("Delete", help="Select to delete this item", default=False)
            },
            hide_index=True,
            use_container_width=True,
        )

        # Delete selected items
        if st.button("Delete Selected Items"):
            items_to_delete = edited_df[edited_df['Delete']]['id'].tolist()
            for item_id in items_to_delete:
                delete_item(item_id)
            st.rerun()  # Refresh the page to reflect changes

    # Display total amount
    total_amount = bills_df['amount'].sum()
    st.write(f"Total Amount: {total_amount}")

    # Display previous months' data (sorted by latest month first)
    st.header("Previous Months' Data")
    if not bills_df.empty:
        bills_df['date'] = pd.to_datetime(bills_df['date'])
        bills_df['month'] = bills_df['date'].dt.to_period('M')
        monthly_summary = bills_df.groupby('month')['amount'].sum().reset_index()
        monthly_summary = monthly_summary.sort_values(by='month', ascending=False)  # Sort by latest month first
        st.write(monthly_summary)

    # Close database connection
    conn.close()

elif st.session_state["authentication_status"] is False:
    st.error("Username/password is incorrect")
elif st.session_state["authentication_status"] is None:
    st.warning("Please enter your username and password")

# Registration widget (only show if not logged in)
if not st.session_state["authentication_status"]:
    try:
        if authenticator.register_user():
            st.success("User registered successfully")
            # Save updated config file
            with open('config.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False)
    except Exception as e:
        st.error(e)