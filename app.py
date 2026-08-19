import streamlit as st
import pandas as pd
import os
import random
import requests
from datetime import datetime

# --- Configuration ---
MAT_DIR, RAW_DIR = "MAT", "RAW"
MAX_QUESTIONS = 20

# ⚠️ REPLACE THIS WITH YOUR DEPLOYED GOOGLE APPS SCRIPT WEB APP URL ⚠️
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxhDQRUbSqm__le5o0c4UawSPU1bVRZvICpxOtUTmLPLTah1UEB9Hk58QNyklWInpJC/exec" 

# --- Backend Connectivity ---
def fetch_sheet_data(sheet_name):
    """Fetches data from the Google Sheet via the Web App."""
    if WEB_APP_URL == "PASTE_YOUR_WEB_APP_URL_HERE":
        return pd.DataFrame()
    try:
        response = requests.get(f"{WEB_APP_URL}?sheet={sheet_name}")
        data = response.json()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def append_to_sheet(sheet_name, row_data):
    """Appends a row to the Google Sheet via the Web App."""
    if WEB_APP_URL == "PASTE_YOUR_WEB_APP_URL_HERE":
        st.warning("Please configure your WEB_APP_URL to save data!")
        return
    try:
        payload = {"sheetName": sheet_name, "rowData": row_data}
        requests.post(WEB_APP_URL, json=payload)
    except Exception as e:
        st.error(f"Error saving data: {e}")

# --- Session State ---
if 'email' not in st.session_state:
    st.session_state.email = None
if 'q_count' not in st.session_state:
    st.session_state.q_count = 0
if 'current_pair' not in st.session_state:
    st.session_state.current_pair = None

def get_unique_pair(email):
    """Fetches images the user hasn't seen yet."""
    logs_df = fetch_sheet_data("image_logs")
    
    if logs_df.empty or "Email" not in logs_df.columns:
        seen_mat, seen_raw = [], []
    else:
        seen_mat = logs_df[logs_df["Email"] == email]["MAT_Image"].tolist()
        seen_raw = logs_df[logs_df["Email"] == email]["RAW_Image"].tolist()
        
    mat_imgs = [f for f in os.listdir(MAT_DIR) if f not in seen_mat and f.endswith(('.png', '.jpg'))]
    raw_imgs = [f for f in os.listdir(RAW_DIR) if f not in seen_raw and f.endswith(('.png', '.jpg'))]
    
    if not mat_imgs or not raw_imgs:
        return None
        
    pair = {"mat": random.choice(mat_imgs), "raw": random.choice(raw_imgs), "mat_left": random.choice([True, False])}
    
    # Log that these images were shown
    append_to_sheet("image_logs", {
        "Email": email, "MAT_Image": pair["mat"], "RAW_Image": pair["raw"], 
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return pair

# --- UI: User Login ---
if st.session_state.email is None:
    st.title("Sinhala OCR Complexity Survey")
    with st.form("user_details"):
        name = st.text_input("Name")
        email = st.text_input("Email (Used to track your unique images)")
        it_field = st.radio("Are you in the IT field?", ["Yes", "No"])
        knowledge = st.slider("Rate your analytics knowledge (1 = Beginner, 5 = Expert)", 1, 5)
        
        if st.form_submit_button("Start Survey") and email:
            # Check if user already exists, if not, save them
            users_df = fetch_sheet_data("users")
            if users_df.empty or "Email" not in users_df.columns or email not in users_df["Email"].values:
                append_to_sheet("users", {
                    "Email": email, "Name": name, "IT_Field": it_field, 
                    "Analytics_Knowledge": knowledge, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # Count how many questions they've already answered (in case they return)
            results_df = fetch_sheet_data("results")
            if not results_df.empty and "Email" in results_df.columns:
                st.session_state.q_count = len(results_df[results_df["Email"] == email])
            else:
                st.session_state.q_count = 0
                
            st.session_state.email = email
            st.session_state.current_pair = get_unique_pair(email)
            st.rerun()

# --- UI: Survey Interface ---
elif st.session_state.q_count >= MAX_QUESTIONS:
    st.success(f"Thank you! You have completed all {MAX_QUESTIONS} questions.")
else:
    st.title(f"Evaluation: Question {st.session_state.q_count + 1} / {MAX_QUESTIONS}")
    st.write("### Which image makes it harder for an AI model to detect the text?")
    
    pair = st.session_state.current_pair
    if not pair:
        st.error("No more unique images available!")
    else:
        left_img = os.path.join(MAT_DIR if pair["mat_left"] else RAW_DIR, pair["mat"] if pair["mat_left"] else pair["raw"])
        right_img = os.path.join(RAW_DIR if pair["mat_left"] else MAT_DIR, pair["raw"] if pair["mat_left"] else pair["mat"])
        
        col1, col2 = st.columns(2)
        def save_result(selection):
            append_to_sheet("results", {
                "Email": st.session_state.email, "MAT_Image": pair["mat"], "RAW_Image": pair["raw"],
                "Selected_Harder": selection, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            st.session_state.q_count += 1
            st.session_state.current_pair = get_unique_pair(st.session_state.email) if st.session_state.q_count < MAX_QUESTIONS else None
        
        with col1:
            st.image(left_img, use_container_width=True)
            if st.button("Image A is harder", key="btn_a"):
                save_result("MAT" if pair["mat_left"] else "RAW")
                st.rerun()
                
        with col2:
            st.image(right_img, use_container_width=True)
            if st.button("Image B is harder", key="btn_b"):
                save_result("RAW" if pair["mat_left"] else "MAT")
                st.rerun()

# --- Hidden Admin Portal ---
st.write("") # Spacer
with st.expander("🛠️"): # Obscure emoji for admin access
    ad_user = st.text_input("User", key="ad_u")
    ad_pass = st.text_input("Pass", type="password", key="ad_p")
    
    if ad_user == "admin" and ad_pass == "admin":
        st.success("Admin unlocked.")
        st.markdown("[Open Google Sheet Data](https://docs.google.com/spreadsheets/d/1jwvK2PwaTHL226HZna471dhS79GYNYvzC1GxquGaiZ4/edit?usp=sharing)")