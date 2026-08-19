import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime

# --- Configuration ---
LOG_FILE = "data_log.csv"
MAT_DIR = "MAT"
RAW_DIR = "RAW"

# Initialize CSV with headers if it doesn't exist
if not os.path.exists(LOG_FILE):
    pd.DataFrame(columns=[
        "Timestamp", "Name", "Email", "IT_Field", 
        "Analytics_Knowledge", "MAT_Image", "RAW_Image", "Selected_Harder"
    ]).to_csv(LOG_FILE, index=False)

# --- Session State Management ---
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'current_pair' not in st.session_state:
    st.session_state.current_pair = None

def get_new_pair():
    """Fetches a random image from both folders and shuffles their positions."""
    mat_imgs = [f for f in os.listdir(MAT_DIR) if f.endswith(('.png', '.jpg'))]
    raw_imgs = [f for f in os.listdir(RAW_DIR) if f.endswith(('.png', '.jpg'))]
    
    if not mat_imgs or not raw_imgs:
        return None
        
    mat_choice = random.choice(mat_imgs)
    raw_choice = random.choice(raw_imgs)
    is_mat_left = random.choice([True, False]) # Randomize layout
    
    return {"mat": mat_choice, "raw": raw_choice, "mat_left": is_mat_left}

# --- UI: User Details Form ---
if st.session_state.user_info is None:
    st.title("Sinhala OCR Complexity Survey")
    st.write("Please provide your details to begin.")
    
    with st.form("user_details"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        it_field = st.radio("Are you in the IT field?", ["Yes", "No"])
        knowledge = st.slider("Rate your knowledge of analytics (1 = Beginner, 5 = Expert)", 1, 5)
        submitted = st.form_submit_button("Start Survey")
        
        if submitted and name and email:
            st.session_state.user_info = {
                "Name": name, "Email": email, "IT_Field": it_field, "Analytics_Knowledge": knowledge
            }
            st.session_state.current_pair = get_new_pair()
            st.rerun()

# --- UI: Image Evaluation Task ---
else:
    st.title("Image Complexity Evaluation")
    st.write("### Please select if an AI image model will have a hard time detecting the text from which image.")
    
    if st.session_state.current_pair is None:
        st.error("Missing images in the MAT or RAW folders.")
    else:
        pair = st.session_state.current_pair
        mat_path = os.path.join(MAT_DIR, pair["mat"])
        raw_path = os.path.join(RAW_DIR, pair["raw"])
        
        left_img = mat_path if pair["mat_left"] else raw_path
        right_img = raw_path if pair["mat_left"] else mat_path
        
        col1, col2 = st.columns(2)
        
        def log_selection(selection):
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Name": st.session_state.user_info["Name"],
                "Email": st.session_state.user_info["Email"],
                "IT_Field": st.session_state.user_info["IT_Field"],
                "Analytics_Knowledge": st.session_state.user_info["Analytics_Knowledge"],
                "MAT_Image": pair["mat"],
                "RAW_Image": pair["raw"],
                "Selected_Harder": selection
            }])
            new_row.to_csv(LOG_FILE, mode='a', header=False, index=False)
            st.session_state.current_pair = get_new_pair()
        
        with col1:
            st.image(left_img, caption="Image A", use_container_width=True)
            if st.button("Image A is harder"):
                log_selection("MAT" if pair["mat_left"] else "RAW")
                st.rerun()
                
        with col2:
            st.image(right_img, caption="Image B", use_container_width=True)
            if st.button("Image B is harder"):
                log_selection("RAW" if pair["mat_left"] else "MAT")
                st.rerun()

    # Admin Download Area
    st.write("---")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            st.download_button("Download Survey Data (CSV)", f, file_name="data_log.csv")