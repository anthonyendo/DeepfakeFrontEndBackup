"""
detectors.py

This module contains all logic related to running the deepfake detector.

It provides a single entry point that the UI calls:

    run_analysis(uploader, modality, use_mock, api_url)

Inside, it can either:
  - use a MOCK predictor (for demos / when the real API is not ready), or
  - call the REAL API endpoint defined by DEEFAKE_API_URL in Streamlit secrets.

Only these three functions would need changes probably:
  - mock_predict: fake/demo behavior
  - real_predict: how we call the backend API
  - run_analysis: glue between Streamlit uploader and the model/API
"""

import time
import random
import tempfile
from pathlib import Path

import requests
import streamlit as st


def mock_predict(file_bytes: bytes, modality: str) -> dict:
    """
    Mock / demo predictor.

    This function does NOT call any real model. It just:
      - sleeps briefly to simulate processing time
      - uses a deterministic random seed based on the file and modality
      - returns a random probability in [0.12, 0.94]
      - labels "deepfake" if prob >= 0.5, else "real"

    Args:
        file_bytes: Raw bytes of the uploaded file.
        modality: One of "image", "video", "audio".

    Returns:
        dict: {"label": "deepfake" | "real", "probability": float}
    """
    # Simulate some runtime so the spinner feels "real".
    time.sleep(0.8)

    # Build a seed from the beginning of the file + metadata
    seed = sum(bytearray(file_bytes[:64])) + len(file_bytes) + len(modality)
    random.seed(seed)

    # Generate a random probability and decide a label
    prob = round(random.uniform(0.12, 0.94), 3)
    label = "deepfake" if prob >= 0.5 else "real"

    return {"label": label, "probability": prob}


def real_predict(tmp_path: str, modality: str, api_url: str) -> dict | None:
    """
    Call the REAL deepfake detection API.

    This is where you plug in your backend.

    Expected behavior (recommended contract, can be adjusted to your backend):
      - Send a POST request to `api_url`
      - Include the uploaded file under the "file" field (multipart/form-data)
      - Include `modality` as a form field
      - Receive back JSON like:
            {
                "label": "deepfake" | "real",
                "probability": 0.87
            }

    Args:
        tmp_path: Path to the temporary file saved on disk.
        modality: "image", "video", or "audio".
        api_url: Full endpoint URL, e.g. "https://your-backend/predict".

    Returns:
        dict: Parsed JSON from the API if successful.
        None: If there's a network error, bad status code, or invalid JSON.
              In that case, a user-facing error message is shown in the UI.
    """
    # Optional: API key from Streamlit secrets (if your backend requires auth).
    # In .streamlit/secrets.toml or Streamlit Cloud "Secrets" menu, you can set:
    #   DEEFAKE_API_KEY = "your-token-here"
    headers: dict[str, str] = {}
    try:
        api_key = st.secrets.get("DEEFAKE_API_KEY")
        if api_key:
            # Example: standard Bearer token auth; adjust if your backend differs.
            headers["Authorization"] = f"Bearer {api_key}"
    except Exception:
        # If secrets are not configured with this key, just ignore.
        pass

    try:
        # Open the temporary file in binary mode and attach it as "file".
        with open(tmp_path, "rb") as f:
            files = {"file": f}
            # You can add more fields here if your backend expects them.
            data = {"modality": modality}

            # IMPORTANT:
            # - api_url is typically read from st.secrets["DEEFAKE_API_URL"]
            #   and passed in from the UI.
            # - timeout is set to 120 seconds; adjust if needed.
            resp = requests.post(
                api_url,
                files=files,
                data=data,
                headers=headers,
                timeout=120,
            )

        # Raises requests.exceptions.HTTPError for 4xx or 5xx responses.
        resp.raise_for_status()

        # Attempt to decode JSON from the response body.
        result = resp.json()
        if not isinstance(result, dict):
            # We expect a JSON OBJECT (dict), not a list / string / etc.
            raise ValueError("API did not return a JSON object")

        return result

    # Error handling: network-level or HTTP errors
    except requests.exceptions.RequestException as e:
        # This includes connection errors, timeouts, bad HTTP status codes after raise_for_status(), etc.
        st.error(
            "We couldn't reach the deepfake detection API. "
            "Please check the API URL, your internet connection, or try again later.",
            icon="⚠️",
        )
        # Show technical details for debugging (developers can see this; users can ignore).
        st.caption(f"Technical details: {e}")
        return None

    # Error handling: response format issues
    except ValueError as e:
        # This triggers if resp.json() fails or returns something unexpected (not a dict).
        st.error(
            "The deepfake detection API returned an unexpected response format.",
            icon="⚠️",
        )
        st.caption(f"Technical details: {e}")
        return None

    # Error handling: any other unexpected exceptions
    except Exception as e:
        st.error(
            "An unexpected error occurred while processing the API response.",
            icon="⚠️",
        )
        st.caption(f"Technical details: {e}")
        return None


def run_analysis(uploader, modality: str, use_mock: bool, api_url: str) -> dict | None:
    """
    High-level helper called by the UI (Home.py).

    This function is the ONLY thing the frontend calls to "run the model".
    It is responsible for:
      - validating that a file was uploaded
      - saving the file to a temporary path on disk
      - choosing between MOCK vs REAL prediction
      - returning the model's result dict back to the UI

    Args:
        uploader: The file-like object returned by st.file_uploader in the UI.
        modality: "image", "video", or "audio" (chosen in the Settings section).
        use_mock: True to use the random mock predictor; False to call real API.
        api_url: URL of the real API endpoint to call when use_mock is False.

    Returns:
        dict: Result from mock_predict or real_predict, on success.
        None: If no file is uploaded OR an error occurred (see real_predict).
    """
    # No file uploaded -> warn the user and stop.
    if not uploader:
        st.warning("Please upload a file first.", icon="⚠️")
        return None

    # Show a spinner while we process / call the API.
    with st.spinner("Analyzing… this may take a few seconds"):
        # 1) Save the uploaded file to a temporary path.
        suffix = Path(uploader.name).suffix  # keep original extension (.jpg, .mp4, etc.)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploader.getbuffer())
            tmp_path = tmp.name  # local filesystem path to pass to backend

        # 2) Choose which predictor to use based on `use_mock`.
        if use_mock:
            # Mock mode: no network call, just random result.
            result = mock_predict(uploader.getbuffer(), modality)
        else:
            # Real mode: call your actual backend API.
            result = real_predict(tmp_path, modality, api_url)

    # If the real API failed, real_predict() returns None and an error message
    # will already have been shown to the user.
    if result is None:
        return None

    # At this point, `result` should be a dict like:
    #   {"label": "deepfake" | "real", "probability": float}
    return result
