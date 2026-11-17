
import streamlit as st

# STEP 1: Configure the web page
st.set_page_config(
    page_title="IT Helpdesk System",
    page_icon="🛠️",
    layout="wide"
)

# STEP 2: Display application title
st.title("IT Helpdesk Ticket Management System")

st.write(
    "Welcome to the IT Helpdesk Management System."
)

# STEP 3: Show application status
st.info("Week 3 - Streamlit Web Interface")

# STEP 4: Test user interaction
if st.button("Test Interface"):
    st.success("Streamlit is working successfully!")
