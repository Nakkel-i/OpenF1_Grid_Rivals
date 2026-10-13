
import requests
import pandas as pd
import streamlit as st

from app.data_loader import fetch_data


@st.cache_data(ttl=1800)
def get_2026_meetings():
    return fetch_data("meetings", {"year": 2026})


@st.cache_data(ttl=1800)
def get_meeting_sessions(meeting_key):
    return fetch_data("sessions", {"meeting_key": int(meeting_key)})


@st.cache_data(ttl=1800)
def get_session_drivers(session_key):
    return fetch_data("drivers", {"session_key": int(session_key)})


@st.cache_data(ttl=1800)
def get_session_results(session_key):
    return fetch_data(
        "session_result",
        {"session_key": int(session_key)}
    )


def render_grid_rivals():
    st.header("🏁 Grid Rivals")
    st.caption("2026 season — practice standings and race results")

    # Get only the 2026 races.
    try:
        meetings = get_2026_meetings()
    except requests.RequestException as exc:
        response = getattr(exc, "response", None)

        if response is not None and response.status_code == 401:
            st.warning(
                "OpenF1 requires authentication right now. "
                "Please try again later or configure an API token."
            )
        else:
            st.error(f"Could not load 2026 races: {exc}")
        return

    if meetings.empty:
        st.info("No 2026 races are available from the API.")
        return

    # Create race labels.
    meetings = meetings.copy()

    meetings["label"] = (
        meetings["meeting_name"].fillna("Unknown Grand Prix").astype(str)
        + " — "
        + meetings["location"].fillna("").astype(str)
    )

    if "date_start" in meetings.columns:
        meetings = meetings.sort_values("date_start")
    else:
        meetings = meetings.sort_values("meeting_key")

    meetings = meetings.drop_duplicates("meeting_key")

    meeting_keys = meetings["meeting_key"].tolist()
    labels = meetings["label"].tolist()

    selected_key = st.selectbox(
        "Select race",
        meeting_keys,
        format_func=lambda key: labels[meeting_keys.index(key)],
        key="grid_rivals_race"
    )

    # Load sessions for the selected race.
    try:
        sessions = get_meeting_sessions(selected_key)
    except requests.RequestException as exc:
        st.error(f"Could not load race sessions: {exc}")
        return

    if sessions.empty:
        st.info("Session information is not available yet.")
        return

    # Map OpenF1 session names to the requested columns.
    practice_names = {
        "practice 1": "FP1",
        "fp1": "FP1",
        "practice 2": "FP2",
        "fp2": "FP2",
        "practice 3": "FP3",
        "fp3": "FP3",
    }

    sessions = sessions.copy()

    sessions["session_name_clean"] = (
        sessions["session_name"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    sessions["practice"] = (
        sessions["session_name_clean"].map(practice_names)
    )

    practice_sessions = sessions[
        sessions["practice"].notna()
    ].drop_duplicates("practice")

    session_keys = dict(
        zip(
            practice_sessions["practice"],
            practice_sessions["session_key"]
        )
    )

    # Find the Grand Prix race session.
    race_sessions = sessions[
        sessions["session_name_clean"] == "race"
    ]

    race_session_key = (
        race_sessions.iloc[0]["session_key"]
        if not race_sessions.empty
        else None
    )

    # Get driver information from an available session.
    try:
        driver_df = pd.DataFrame()

        available_sessions = (
            sessions.sort_values("date_start")
            if "date_start" in sessions.columns
            else sessions
        )

        for session_key in available_sessions["session_key"]:
            driver_df = get_session_drivers(int(session_key))

            if not driver_df.empty:
                break

    except requests.RequestException as exc:
        st.error(f"Could not load driver information: {exc}")
        return

    if driver_df.empty:
        st.info(
            "Driver information is not available yet. "
            "Try again after the event data has been published."
        )
        return

    driver_df = driver_df.copy()
    driver_df["driver_number"] = (
        driver_df["driver_number"].astype(str)
    )

    # Prefer full names, then acronyms.
    if "full_name" in driver_df.columns:
        driver_df["Driver"] = driver_df["full_name"]

        if "name_acronym" in driver_df.columns:
            driver_df["Driver"] = driver_df["Driver"].fillna(
                driver_df["name_acronym"]
            )

    elif "name_acronym" in driver_df.columns:
        driver_df["Driver"] = driver_df["name_acronym"]

    else:
        driver_df["Driver"] = driver_df["driver_number"]

    result = driver_df[
        ["driver_number", "Driver"]
    ].drop_duplicates("driver_number").copy()

    # Load final positions for FP1, FP2 and FP3.
    for practice in ("FP1", "FP2", "FP3"):
        result[practice] = "NT"

        session_key = session_keys.get(practice)

        if session_key is None:
            continue

        try:
            standings = get_session_results(int(session_key))
        except requests.RequestException as exc:
            st.warning(
                f"{practice} results could not be loaded: {exc}"
            )
            continue

        if standings.empty or "position" not in standings.columns:
            continue

        standings = standings[
            ["driver_number", "position"]
        ].dropna(subset=["position"]).copy()

        standings["driver_number"] = (
            standings["driver_number"].astype(str)
        )

        positions = (
            standings.drop_duplicates("driver_number")
            .set_index("driver_number")["position"]
        )

        result[practice] = (
            result["driver_number"]
            .map(positions)
            .map(
                lambda position: (
                    str(int(position))
                    if pd.notna(position)
                    else "NT"
                )
            )
        )

    # Load official race finishing positions.
    result["RACE"] = "NT"

    if race_session_key is not None:
        try:
            race_standings = get_session_results(
                int(race_session_key)
            )

            if (
                not race_standings.empty
                and "position" in race_standings.columns
            ):
                race_standings = race_standings[
                    ["driver_number", "position"]
                ].dropna(subset=["position"]).copy()

                race_standings["driver_number"] = (
                    race_standings["driver_number"].astype(str)
                )

                race_positions = (
                    race_standings
                    .drop_duplicates("driver_number")
                    .set_index("driver_number")["position"]
                )

                result["RACE"] = (
                    result["driver_number"]
                    .map(race_positions)
                    .map(
                        lambda position: (
                            str(int(position))
                            if pd.notna(position)
                            else "NT"
                        )
                    )
                )

        except requests.RequestException as exc:
            st.warning(
                f"Race results could not be loaded: {exc}"
            )

    # Calculate average position across FP1, FP2 and FP3.
    # Ignore "NT" entries and round to one decimal place.
    def calculate_average(row):
        positions = pd.to_numeric(
            row[["FP1", "FP2", "FP3"]],
            errors="coerce"
        ).dropna()

        if positions.empty:
            return "NT"

        return f"{positions.mean():.1f}"

    result["AVG"] = result.apply(calculate_average, axis=1)

    # Calculate estimated finishing position using weighted practice results.
    # FP1 = 20%, FP2 = 30%, FP3 = 50%.
    def calculate_estimate(row):
        weights = {
            "FP1": 0.2,
            "FP2": 0.3,
            "FP3": 0.5,
        }

        weighted_total = 0.0
        total_weight = 0.0

        for session, weight in weights.items():
            position = pd.to_numeric(
                pd.Series([row[session]]),
                errors="coerce"
            ).iloc[0]

            if pd.notna(position):
                weighted_total += position * weight
                total_weight += weight

        if total_weight == 0:
            return "NT"

        # Normalize weights if a practice session is missing.
        estimate = weighted_total / total_weight

        return f"{estimate:.1f}"

    result["EST"] = result.apply(calculate_estimate, axis=1)

    # Sort drivers by estimated finishing position.
    # Drivers without estimates are placed last.
    result["_sort_est"] = pd.to_numeric(
        result["EST"],
        errors="coerce"
    )

    result = (
        result.sort_values("_sort_est", na_position="last")
        .drop(columns="_sort_est")
        .reset_index(drop=True)
    )

    # Display the table once.
    st.subheader(labels[meeting_keys.index(selected_key)])

    st.dataframe(
        result[
            ["Driver", "FP1", "FP2", "FP3", "AVG", "EST", "RACE"]
        ],
        hide_index=True,
        use_container_width=True
    )
