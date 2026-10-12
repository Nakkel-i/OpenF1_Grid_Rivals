
import os

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from app.database import get_cached_data, save_cached_data

load_dotenv()

BASE_URL = os.getenv(
    "BASE_API_URL",
    "https://api.openf1.org/v1/"
).rstrip("/") + "/"


def fetch_data(endpoint, params=None):
    """
    Return API data from SQLite if it exists.
    Otherwise, fetch it from OpenF1 and save it permanently.

    Cached data never expires automatically.
    """

    if params is None:
        params = {}

    # 1. Check the permanent local database.
    cached_data = get_cached_data(endpoint, params)

    if cached_data is not None:
        return pd.DataFrame(cached_data)

    # 2. Fetch data only if it is not in SQLite.
    url = f"{BASE_URL}{endpoint}"

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    # 3. Save the successful response permanently.
    save_cached_data(endpoint, params, data)

    return pd.DataFrame(data)


def fetch_meetings(year, country):
    """Fetch meetings for a year and country."""

    df = fetch_data(
        "meetings",
        {"year": year, "country_name": country}
    )

    if df.empty:
        st.warning("No meeting data found.")
        return pd.DataFrame(
            columns=["meeting_key", "label", "year"]
        )

    df = df.copy()

    df["label"] = (
        df["meeting_name"].fillna("")
        + " - "
        + df["location"].fillna("")
    )

    df = df.sort_values(
        by="meeting_key",
        ascending=False
    )

    return df[
        ["meeting_key", "label", "year"]
    ].drop_duplicates()


def fetch_sessions(meeting_key):
    """Fetch sessions for a selected Grand Prix."""

    df = fetch_data(
        "sessions",
        {"meeting_key": meeting_key}
    )

    if df.empty:
        return pd.DataFrame(
            columns=["session_key", "label"]
        )

    df = df.copy()

    df["label"] = (
        df["session_name"].fillna("")
        + " ("
        + df["date_start"].fillna("")
        + ")"
    )

    return df[
        ["session_key", "label"]
    ].drop_duplicates()


def fetch_laps(session_key):
    """Fetch lap timing data."""

    return fetch_data(
        "laps",
        {"session_key": session_key}
    )


def fetch_stints(session_key):
    """Fetch tyre stint data."""

    return fetch_data(
        "stints",
        {"session_key": session_key}
    )


def fetch_pit_stop(session_key):
    """Fetch pit stop data."""

    return fetch_data(
        "pit",
        {"session_key": session_key}
    )


def fetch_drivers(session_key):
    """Fetch driver information."""

    return fetch_data(
        "drivers",
        {"session_key": session_key}
    )
