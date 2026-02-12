"""
detectors.py

This file contains the mock_predict function and the real_predict function.

This file basically serves as the "bridge" between:
    - The user interface (what users see in the browser)
    - The backend deepfake detection system (the AI model server)

The UI (Home.py) calls one function in this file:

    run_analysis(uploader, modality, use_mock, api_url)

This file decides:

    If we are in MOCK mode:
        then generate a fake/random result (for demo purposes)

    If we are in REAL mode:
        then send the uploaded file to a backend API
        -> wait for a response
        -> return the result to the UI
"""

import time
import random
import tempfile
from pathlib import Path

import requests
import streamlit as st

# mock_predict() is not necessary to understand, it will be removed eventually
def mock_predict(file_bytes: bytes, modality: str) -> dict:
    """
    Mock / demo predictor.
    
    NOT NECESSARY to know what this does at all, it's just temporary for demo purposes.

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
    # Simulate some runtime for the spinner
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
    This function sends the uploaded file to the backend server.

    This function is basically saying:
        "Hey backend, here is a file. Please analyze it and see if it's a deepfake."

    It works like this:
        1. Open the saved file (the user input)
        2. Send it to the backend using an HTTP POST request
        3. Wait for a response
        4. Return the result
        
    Basically in order to connect the API to this function you just need to create the secrets.toml
    file (instructions in README), and paste the API url into that file.
    
    It's important to note that using the secrets.toml file to connect the back end via API will only work locally.
    This is just for testing purposes to see if the API connection actually works.
    Once we confirm it works there is an option in Streamlit to apply it globally to the website, so that anyone
    who visits our website will be able have full functionality of the detector. But for now we're going to use
    secrets.toml for testing purposes. 

    Parameters:
        tmp_path:
            The location of the file saved on disk (temporary file) (the user input).

        modality:
            "image", "video", or "audio"

        api_url:
            The full URL of the backend endpoint (not sure where we are hosting the model, could do AWS, Render,
            Fly.io, etc.)
            Example: https://my-backend.com/predict
            Example: s3://my-bucket/deepfake-registry/v1

    Returns:
        - A dictionary if successful
        - None if something failed
    """
    # ------------------------------------
    # In .streamlit/secrets.toml you can set:
    #   DEEFAKE_API_KEY = "your-token-here"
    # See line 101
    headers: dict[str, str] = {}
    try:
        api_key = st.secrets.get("DEEFAKE_API_KEY") # This is retrieving the API url from the secrets.toml file
        if api_key:
            # This just sends a Bearer token in headers just in case the backend requires authentication
            headers["Authorization"] = f"Bearer {api_key}"
    except Exception:
        # If secrets are not detected, then just ignore.
        pass

    # ------------------------------------
    # Sending HTTP request to backend
    try:
        # Open the temporary file in binary mode(rb) and attach it as "file".
        # Use binary mode because images, audio, video are binary, not text
        with open(tmp_path, "rb") as f:
            # ------------------------------------
            # Prepare file for upload
            # Building a dictionary (key-value pair)
            # The form field name = "file"
            # The file content = f
            files = {"file": f}
            
            # Also adding another form field called modality ("image", "audio", "video")
            data = {"modality": modality}

            # send POST request to backend (POST is an HTTP request that "sends data")
            resp = requests.post(
                api_url, # URL of backend
                files=files, # uploaded file (user input)
                data=data, # the modality
                headers=headers, # metadata about the POST request (in this case the authorization Bearer token) (may not be used)
                timeout=120, # wait up to 2 minutes, if exceeds 2 mins, then the request fails
            )
            
            # So the backend receives:
            # - the file
            # - the modality type
            # This allows the backend to decide which processing pipeline to run
            
    # ------------------------------------
        # Error response just in case
        resp.raise_for_status()

        # Converts backend response into python dictionary
        result = resp.json()
        
        # Makes sure that the response is really a dictionary
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
    This is the one function that Home.py calls.

    This function:
        1. Checks that a file was uploaded
        2. Saves the file temporarily
        3. Decides whether to use mock or real API
        4. Returns the result

    Parameters:
        uploader:
            The file uploaded via Streamlit file uploader.

        modality:
            "image", "video", or "audio"

        use_mock:
            True  -> Use mock_predict()
            False -> Use real_predict()

        api_url:
            Backend URL (used only if use_mock is False)

    Returns:
        Dictionary with result OR None
    """
    # ------------------------------------
    # If the user did not upload a file
    if not uploader:
        st.warning("Please upload a file first.", icon="⚠️")
        return None

    # ------------------------------------
    # Show a loading spinner while we process / call the API.
    with st.spinner("Analyzing… this may take a few seconds"):
        # 1) Save the uploaded file to a temporary location
        suffix = Path(uploader.name).suffix  # keep original extension (.jpg, .mp4, etc.)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp: # Create a temporary file on disk
            tmp.write(uploader.getbuffer()) # Write uploaded file contents into it
            tmp_path = tmp.name  # Save file path

        # 2) Choose which predictor to use based on `use_mock`.
        if use_mock:
            # Fake random result
            result = mock_predict(uploader.getbuffer(), modality)
        else:
            # Call actual back end API
            result = real_predict(tmp_path, modality, api_url)

    # ------------------------------------
    # If the real API failed, real_predict() returns None and an error message
    # will already have been shown to the user.
    if result is None:
        return None

    # ------------------------------------
    # At this point, `result` should be a dict like:
    #   {"label": "deepfake" | "real", "probability": float}
    return result
