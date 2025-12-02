# layout.py
# This file contains all the UI components that make up the page layout.
# Each function here draws a part of the interface (settings, uploader, preview, etc.)
# Home.py calls these functions to build the page.

from pathlib import Path
import os
import streamlit as st

# Helper: Figure out which API URL to use (from secrets or fallback)
def _get_api_url() -> str:
    """
    Get the API URL used when 'Use mock API' is OFF.

    Priority order:
      1. Streamlit secrets (used locally + Streamlit Cloud)
      2. Environment variable
      3. Default local URL

    Each user can have their own secrets.toml file.
    """
    try:
        return st.secrets["DEEFAKE_API_URL"]
    except Exception:
        return os.getenv("DEEFAKE_API_URL", "http://localhost:8000/predict")

# Settings section (modality, API URL, mock toggle)
def render_settings():
    """
    Draw the Settings area at the top of the page.

    Returns:
        modality: "image" | "video" | "audio"
        use_mock: True or False
        api_url: URL used if mock is OFF
    """
    st.markdown("### Settings")

    # Two-column layout:
    # Left: input type
    # Right: API URL + mock toggle
    col1, col2 = st.columns([1, 2])

    # Column 1: Input type selection
    with col1:
        modality = st.selectbox(
            "Input type",
            ["image", "video", "audio"],
            key="modality_select",
        )

    # Column 2: API URL + mock toggle
    with col2:
        default_url = _get_api_url()

        # Keep a stable value for the toggle in session state
        if "use_mock_state" not in st.session_state:
            st.session_state.use_mock_state = True  # default is mock mode ON

        # API URL is disabled unless mock mode is OFF
        if st.session_state.use_mock_state:
            st.text_input(
                "API URL",
                value=default_url,
                disabled=True,
                key="api_url_disabled",
            )
        else:
            st.text_input(
                "API URL",
                value=default_url,
                key="api_url_input",
            )

        # Toggle for switching mock mode ON/OFF
        use_mock = st.toggle(
            "Use mock API",
            value=st.session_state.use_mock_state,
            key="use_mock_toggle",
        )

        # Keep toggle state consistent across reruns
        st.session_state.use_mock_state = use_mock

        # If mock is ON -> always use default_url
        # If mock is OFF -> use whatever user typed
        api_url = default_url if use_mock else st.session_state.get("api_url_input", default_url)

    st.divider()
    return modality, use_mock, api_url

# Title and subtitle at top of the page
def render_header():
    """Draw the main page title and a short description."""
    col_title, col_badge = st.columns([1, 0.25])
    with col_title:
        st.title("AI Deepfake Detector")
        st.caption("Upload an image, video, or audio clip to estimate its deepfake probability.")
    st.write("")

# File uploader
def render_uploader(modality: str):
    """
    Display the file uploader.

    File types allowed depend on the chosen modality.
    """
    ACCEPT = {
        "image": ["jpg", "jpeg", "png"],
        "video": ["mp4", "mov", "m4v", "avi", "mkv"],
        "audio": ["wav", "mp3", "m4a", "flac", "ogg"],
    }

    uploader = st.file_uploader(
        "Drag & drop a file or click to browse",
        type=ACCEPT[modality],
        accept_multiple_files=False,
        label_visibility="collapsed",
        help=f"Accepted: {', '.join(ACCEPT[modality])}",
    )
    return uploader

# Preview (left) + Options (right)
def render_preview_and_options(uploader, modality: str, use_mock: bool, api_url: str):
    """
    Show:
      - A preview of the uploaded file (image/video/audio)
      - A small "Options" box that repeats chosen settings
    """
    with st.container():
        preview_cols = st.columns([1, 1], vertical_alignment="top")

        # Left side: File preview
        with preview_cols[0]:
            st.markdown("#### Preview")
            box = st.container(border=True)

            if uploader:
                # Choose correct preview widget based on modality
                if modality == "image":
                    with box:
                        st.image(uploader, use_container_width=True)
                elif modality == "video":
                    with box:
                        st.video(uploader)
                elif modality == "audio":
                    with box:
                        st.audio(uploader)
            else:
                # No file yet -> show info message
                with box:
                    st.info("No file uploaded yet", icon="📂")

        # Right side: Options summary
        with preview_cols[1]:
            st.markdown("#### Options")
            opts = st.container(border=True)
            with opts:
                st.write("• **Mode:**", modality.title())
                st.write("• **API:**", "Mock" if use_mock else api_url)

# Results display
def render_results(result: dict | None, uploader, modality: str):
    """
    Show the results after the analysis is done:
      - Probability bar
      - Deepfake/Real chip
      - File name + mode
    """
    if not result:
        return  # nothing to show yet

    prob = float(result.get("probability", 0.0))
    label = result.get("label", "unknown")
    pct = f"{prob * 100:.1f}%"

    st.markdown("### Results")
    res_cols = st.columns([1, 1, 1.2])

    # Probability metric + bar
    with res_cols[0]:
        st.metric("Deepfake probability", pct)
        st.progress(min(1.0, prob))

    # Deepfake/Real chip
    with res_cols[1]:
        chip_class = "chip-fake" if label == "deepfake" else "chip-real"
        st.markdown(
            f'<span class="chip {chip_class}">{label.upper()}</span>',
            unsafe_allow_html=True,
        )
        st.caption("Decision threshold used: 0.50 (demo)")

    # File details on the right
    with res_cols[2]:
        if uploader:
            st.write("**File:**", uploader.name)
        else:
            st.write("**File:** —")
        st.write("**Mode:**", modality.title())

# History of previous analyses
def render_history():
    """
    Show a small table of recent runs.
    Stored in st.session_state.history.
    """
    history = st.session_state.get("history", [])
    if not history:
        return

    st.markdown("### Recent Analyses")
    hist_cols = st.columns([2, 1, 1, 1])
    hist_cols[0].markdown("**File**")
    hist_cols[1].markdown("**Type**")
    hist_cols[2].markdown("**Result**")
    hist_cols[3].markdown("**Prob.**")

    # Show only the last 7 analyses
    for row in reversed(history[-7:]):
        c0, c1, c2, c3 = st.columns([2, 1, 1, 1])
        c0.write(row["name"])
        c1.write(row["mode"])
        chip_class = "chip-fake" if row["label"] == "deepfake" else "chip-real"
        c2.markdown(
            f'<span class="chip {chip_class}">{row["label"]}</span>',
            unsafe_allow_html=True,
        )
        c3.write(f"{row['prob'] * 100:.1f}%")

# Footer
def render_footer():
    """Show the small note at the bottom of the page."""
    st.markdown(
        """
<div class="footer">
<b>Notes</b>: This is a demo using a mock predictor.
</div>
""",
        unsafe_allow_html=True,
    )
