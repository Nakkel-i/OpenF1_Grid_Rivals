
import json
from pathlib import Path

import streamlit as st


PRICE_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "grid_rival_prices.json"
)

# Manual 2026 grid: no OpenF1 requests.
# Driver numbers are used as stable IDs for saved prices.
DRIVERS = [
    ("1", "Lando Norris", "McLaren"),
    ("81", "Oscar Piastri", "McLaren"),
    ("63", "George Russell", "Mercedes"),
    ("12", "Andrea Kimi Antonelli", "Mercedes"),
    ("16", "Charles Leclerc", "Ferrari"),
    ("44", "Lewis Hamilton", "Ferrari"),
    ("1R", "Max Verstappen", "Red Bull"),
    ("6", "Isack Hadjar", "Red Bull"),
    ("14", "Fernando Alonso", "Aston Martin"),
    ("18", "Lance Stroll", "Aston Martin"),
    ("10", "Pierre Gasly", "Alpine"),
    ("7", "Jack Doohan", "Alpine"),
    ("23", "Alexander Albon", "Williams"),
    ("55", "Carlos Sainz", "Williams"),
    ("22", "Yuki Tsunoda", "Racing Bulls"),
    ("30", "Liam Lawson", "Racing Bulls"),
    ("31", "Esteban Ocon", "Haas"),
    ("87", "Oliver Bearman", "Haas"),
    ("27", "Nico Hulkenberg", "Kick Sauber"),
    ("5", "Gabriel Bortoleto", "Kick Sauber"),
]

CONSTRUCTORS = [
    "McLaren",
    "Mercedes",
    "Ferrari",
    "Red Bull",
    "Aston Martin",
    "Alpine",
    "Williams",
    "Racing Bulls",
    "Haas",
    "Kick Sauber",
]


def load_prices():
    if not PRICE_FILE.exists():
        return {"drivers": {}, "constructors": {}}

    try:
        with PRICE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return {
            "drivers": data.get("drivers", {}),
            "constructors": data.get("constructors", {}),
        }
    except (OSError, json.JSONDecodeError):
        return {"drivers": {}, "constructors": {}}


def parse_price(value):
    value = str(value).strip().replace(",", ".")

    if not value:
        return None

    try:
        price = float(value)
    except ValueError:
        return "invalid"

    if not (0 <= price < float("inf")):
        return "invalid"

    return price


def render_grid_rival_prices():
    st.header("Grid Rival price")
    st.caption("Edit and save driver and constructor prices.")

    saved = load_prices()

    with st.form("grid_rival_prices_manual_form"):
        st.subheader("Drivers")

        driver_values = {}

        for number, name, team in DRIVERS:
            existing = saved["drivers"].get(number, {})
            default = str(existing.get("price") or "")

            driver_values[number] = st.text_input(
                f"{name} — {team} (#{number})",
                value=default,
                placeholder="e.g. 14,5",
                key=f"manual_driver_price_{number}",
            )

        st.divider()
        st.subheader("Constructors / Teams")

        constructor_values = {}

        for team in CONSTRUCTORS:
            existing = saved["constructors"].get(team, {})
            default = str(existing.get("price") or "")

            constructor_values[team] = st.text_input(
                team,
                value=default,
                placeholder="e.g. 11,4",
                key=f"manual_constructor_price_{team}",
            )

        submitted = st.form_submit_button(
            "Save prices",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        errors = []
        new_drivers = {}
        new_constructors = {}

        for number, name, team in DRIVERS:
            raw = driver_values[number]
            price = parse_price(raw)

            if price == "invalid":
                errors.append(f"{name}: invalid price '{raw}'")
                continue

            new_drivers[number] = {
                "name": name,
                "team": team,
                "price": price,
            }

        for team, raw in constructor_values.items():
            price = parse_price(raw)

            if price == "invalid":
                errors.append(f"{team}: invalid price '{raw}'")
                continue

            new_constructors[team] = {"price": price}

        if errors:
            st.error("Fix these values before saving:")
            for error in errors:
                st.write(f"- {error}")
        else:
            try:
                PRICE_FILE.parent.mkdir(
                    parents=True, exist_ok=True
                )
                with PRICE_FILE.open("w", encoding="utf-8") as file:
                    json.dump(
                        {
                            "drivers": new_drivers,
                            "constructors": new_constructors,
                        },
                        file,
                        ensure_ascii=False,
                        indent=2,
                    )
                st.success("Prices saved successfully!")
            except OSError as exc:
                st.error(f"Could not save prices: {exc}")
