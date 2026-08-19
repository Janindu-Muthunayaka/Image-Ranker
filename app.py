import streamlit as st
import pandas as pd
import os
import random
from datetime import datetime

# --- Configuration ---
MAT_DIR, RAW_DIR = "MAT", "RAW"
USERS_CSV, LOGS_CSV, RESULTS_CSV = "users.csv", "image_logs.csv", "results.csv"
MAX_QUESTIONS = 20

# Initialize CSVs
for file, cols in [
    (USERS_CSV, ["Email", "Name", "IT_Field", "Analytics_Knowledge", "Timestamp"]),
    (LOGS_CSV, ["Email", "MAT_Image", "RAW_Image", "Timestamp"]),
    (RESULTS_CSV, ["Email", "MAT_Image", "RAW_Image", "Selected_Harder", "Timestamp"])
]:
    if not os.path.exists(file):
        pd.DataFrame(columns=cols).to_csv(file, index=False)

# --- Session State ---
if 'email' not in st.session_state:
    st.session_state.email = None
if 'q_count' not in st.session_state:
    st.session_state.q_count = 0
if 'current_pair' not in st.session_state:
    st.session_state.current_pair = None

def get_unique_pair(email):
    """Fetches images the user hasn't seen yet."""
    logs_df = pd.read_csv(LOGS_CSV)
    seen_mat = logs_df[logs_df["Email"] == email]["MAT_Image"].tolist()
    seen_raw = logs_df[logs_df["Email"] == email]["RAW_Image"].tolist()
    
    mat_imgs = [f for f in os.listdir(MAT_DIR) if f not in seen_mat and f.endswith(('.png', '.jpg'))]
    raw_imgs = [f for f in os.listdir(RAW_DIR) if f not in seen_raw and f.endswith(('.png', '.jpg'))]
    
    if not mat_imgs or not raw_imgs:
        return None
        
    pair = {"mat": random.choice(mat_imgs), "raw": random.choice(raw_imgs), "mat_left": random.choice([True, False])}
    
    # Log that these images were shown
    pd.DataFrame([{
        "Email": email, "MAT_Image": pair["mat"], "RAW_Image": pair["raw"], 
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }]).to_csv(LOGS_CSV, mode='a', header=False, index=False)
    
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
            users_df = pd.read_csv(USERS_CSV)
            if email not in users_df["Email"].values:
                pd.DataFrame([{
                    "Email": email, "Name": name, "IT_Field": it_field, 
                    "Analytics_Knowledge": knowledge, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }]).to_csv(USERS_CSV, mode='a', header=False, index=False)
            
            # Count how many questions they've already answered (in case they return)
            results_df = pd.read_csv(RESULTS_CSV)
            st.session_state.q_count = len(results_df[results_df["Email"] == email])
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
            pd.DataFrame([{
                "Email": st.session_state.email, "MAT_Image": pair["mat"], "RAW_Image": pair["raw"],
                "Selected_Harder": selection, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }]).to_csv(RESULTS_CSV, mode='a', header=False, index=False)
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
        for file in [USERS_CSV, LOGS_CSV, RESULTS_CSV]:
            if os.path.exists(file):
                with open(file, "r") as f:
                    st.download_button(f"Download {file}", f, file_name=file)