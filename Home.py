# Home.py
# This is the main "Home" page for the app.
# When someone visits the website, this page will run.
# This file is basically in charge of 
# - building the page layout
# - collects the user input (uploaded file)
# - sends that input to 'detectors.py'
# - displaying results

import os

import streamlit as st

from styles import inject_custom_css
from layout import (
    render_settings,
    render_header,
    render_uploader,
    render_preview_and_options,
    render_results,
    render_history,
    render_footer,
)
from detectors import run_analysis


# Page setup

# Basic Streamlit config for this page.
st.set_page_config(
    page_title="AI Deepfake Detector",
    page_icon="",
    layout="wide",
    menu_items={"About": "AI Deepfake Detector"},
)

# Add custom CSS styling
inject_custom_css()


# Top of the page (title)

# Show the big page title and subtitle.
render_header()


# Settings + uploader section

# Put "Settings" and the file uploader together inside a bordered box.
with st.container(border=True):
    # Settings row:
    # - Input type (image / video / audio)
    # - API URL (for real backend)
    # - Use mock API toggle
    modality, use_mock, api_url = render_settings()

    # File uploader:
    # - Uses the chosen modality to decide what file types are allowed
    uploader = render_uploader(modality)


# Preview + options

# Show a preview of the uploaded file (image/video/audio)
# and a small "Options" box that repeats the settings.
render_preview_and_options(uploader, modality, use_mock, api_url)


# Analyze button

st.write("")  # small vertical space
go = st.button("Analyze", type="primary", use_container_width=True)


# Session state for history
# Keep a list of past analyses during this browser session.
if "history" not in st.session_state:
    st.session_state.history = []

# This will hold the result from the model (mock or real).
result = None



# When user clicks "Analyze"
if go:
    # This calls into detectors.run_analysis(), which:
    # - saves the upload to a temp file
    # - sends the uploaded file to mock_predict() or real_predict()
    result = run_analysis(uploader, modality, use_mock, api_url)

    # If we got a valid result and there was a file,
    # save it to the "Recent analyses" history.
    if result and uploader:
        prob = float(result.get("probability", 0.0))
        label = result.get("label", "unknown")
        st.session_state.history.append(
            {"name": uploader.name, "mode": modality, "label": label, "prob": prob}
        )


# Results section

# Show the probability, label chip, and basic file info.
# If `result` is None (e.g., API error), this just does nothing.
render_results(result, uploader, modality)


# Recent analyses table

# Show a small table with the last few files run through the detector.
render_history()


# Footer note

# Small note at the bottom of the page
render_footer()
