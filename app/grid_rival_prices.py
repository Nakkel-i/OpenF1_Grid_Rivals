
import json
import math
from pathlib import Path

import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

PRICE_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "grid_rival_prices.json"
)

SEASONS = ["2026"]

RACES = [
    "Australia",
    "China",
    "Japan",
    "Bahrain",
    "Saudi Arabia",
    "Miami",
    "Canada",
    "Monaco",
    "Barcelona-Catalunya",
    "Austria",
    "Great Britain",
    "Belgium",
    "Hungary",
    "Netherlands",
    "Italy",
    "Madrid",
    "Azerbaijan",
    "Singapore",
    "United States",
    "Mexico City",
    "São Paulo",
    "Las Vegas",
    "Qatar",
    "Abu Dhabi",
]


# ============================================================
# MANUAL DRIVER AND CONSTRUCTOR LISTS
# No API requests are made by this module.
# ============================================================

DRIVERS = [
    ("1", "Lando Norris", "McLaren"),
    ("81", "Oscar Piastri", "McLaren"),
    ("63", "George Russell", "Mercedes"),
    ("12", "Andrea Kimi Antonelli", "Mercedes"),
    ("16", "Charles Leclerc", "Ferrari"),
    ("44", "Lewis Hamilton", "Ferrari"),
    ("3", "Max Verstappen", "Red Bull"),
    ("6", "Isack Hadjar", "Red Bull"),
    ("14", "Fernando Alonso", "Aston Martin"),
    ("18", "Lance Stroll", "Aston Martin"),
    ("43", "Franco Colapinto", "Alpine"),
    ("10", "Pierre Gasly", "Alpine"),
    ("23", "Alexander Albon", "Williams"),
    ("55", "Carlos Sainz", "Williams"),
    ("41", "Arvid Lindblad", "Racing Bulls"),
    ("30", "Liam Lawson", "Racing Bulls"),
    ("31", "Esteban Ocon", "Haas"),
    ("87", "Oliver Bearman", "Haas"),
    ("27", "Nico Hulkenberg", "Audi"),
    ("5", "Gabriel Bortoleto", "Audi"),
    ("11", "Sergio Perez", "Cadillac"),
    ("77", "Valtteri Bottas", "Cadillac"),
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
    "Audi",
    "Cadillac",
]


# ============================================================
# DATA STRUCTURE
# ============================================================

def empty_race():
    return {
        "drivers": {},
        "constructors": {},
    }


def create_default_data():
    return {
        season: {
            race: empty_race()
            for race in RACES
        }
        for season in SEASONS
    }


# ============================================================
# LOAD PRICES
# ============================================================

def load_prices():

    if not PRICE_FILE.exists():
        return create_default_data()

    try:
        with PRICE_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except (OSError, json.JSONDecodeError):
        return create_default_data()

    if not isinstance(data, dict):
        return create_default_data()

    # --------------------------------------------------------
    # Migrate previous flat price format.
    # Old format:
    # {
    #     "drivers": {},
    #     "constructors": {}
    # }
    #
    # Existing prices are copied to every race.
    # --------------------------------------------------------

    if "drivers" in data or "constructors" in data:

        old_drivers = data.get("drivers", {})
        old_constructors = data.get("constructors", {})

        migrated = create_default_data()

        for race in RACES:
            migrated["2026"][race] = {
                "drivers": old_drivers.copy(),
                "constructors": old_constructors.copy(),
            }

        return migrated

    # Ensure all configured seasons and races exist.
    for season in SEASONS:

        data.setdefault(season, {})

        for race in RACES:

            data[season].setdefault(
                race,
                empty_race(),
            )

            data[season][race].setdefault("drivers", {})
            data[season][race].setdefault("constructors", {})

    return data


# ============================================================
# SAVE PRICES
# ============================================================

def save_prices(prices):

    PRICE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with PRICE_FILE.open("w", encoding="utf-8") as file:

        json.dump(
            prices,
            file,
            ensure_ascii=False,
            indent=4,
        )


# ============================================================
# PRICE VALIDATION
# ============================================================

def parse_price(value):

    if value is None:
        return None

    value = str(value).strip().replace(",", ".")

    if not value:
        return None

    try:
        price = float(value)

    except ValueError:
        return "invalid"

    if not math.isfinite(price) or price < 0:
        return "invalid"

    return price


# ============================================================
# FIND LATEST EVENT WITH SAVED PRICES
# ============================================================

def get_latest_priced_race(prices, season):
    """
    Search the race calendar backwards.

    Returns the latest race that contains at least one
    valid driver or constructor price.

    Returns None if no race has any valid prices.
    """

    season_prices = prices.get(season, {})

    for race in reversed(RACES):

        race_data = season_prices.get(race, {})

        driver_prices = race_data.get("drivers", {})
        constructor_prices = race_data.get("constructors", {})

        has_valid_price = False

        # Check driver prices.
        for entry in driver_prices.values():

            if not isinstance(entry, dict):
                continue

            price = parse_price(entry.get("price"))

            if isinstance(price, (int, float)):
                has_valid_price = True
                break

        # Check constructor prices if no driver price was found.
        if not has_valid_price:

            for entry in constructor_prices.values():

                if not isinstance(entry, dict):
                    continue

                price = parse_price(entry.get("price"))

                if isinstance(price, (int, float)):
                    has_valid_price = True
                    break

        if has_valid_price:
            return race

    return None


# ============================================================
# SORT DRIVERS AND CONSTRUCTORS BY LATEST EVENT PRICES
# ============================================================

def sort_by_latest_price(items, price_data, get_identifier):
    """
    Sort items by their price in the latest priced event.

    Valid prices:
        Highest first.

    Missing prices:
        Remain at the bottom in their original default order.
    """

    indexed_items = list(enumerate(items))

    def sort_key(indexed_item):

        original_index, item = indexed_item

        identifier = get_identifier(item)

        entry = price_data.get(identifier, {})

        if not isinstance(entry, dict):
            return (1, 0, original_index)

        price = parse_price(entry.get("price"))

        if isinstance(price, (int, float)):
            return (0, -price, original_index)

        # No price: retain original order after priced entries.
        return (1, 0, original_index)

    sorted_items = sorted(
        indexed_items,
        key=sort_key,
    )

    return [
        item
        for original_index, item in sorted_items
    ]


# ============================================================
# RENDER PRICE PAGE
# ============================================================

def render_grid_rival_prices():

    st.header("Grid Rival price")

    st.caption(
        "Manage driver and constructor prices for each race."
    )

    prices = load_prices()

    # --------------------------------------------------------
    # SEASON SELECTOR
    # --------------------------------------------------------

    selected_season = st.selectbox(
        "Season",
        SEASONS,
        key="grid_price_season",
    )

    prices.setdefault(selected_season, {})

    # --------------------------------------------------------
    # FIND LATEST EVENT WITH PRICES
    # --------------------------------------------------------

    latest_priced_race = get_latest_priced_race(
        prices,
        selected_season,
    )

    if latest_priced_race is not None:

        latest_prices = prices[selected_season][latest_priced_race]

        # Sort drivers using latest event prices.
        sorted_drivers = sort_by_latest_price(
            DRIVERS,
            latest_prices.get("drivers", {}),
            lambda driver: driver[0],
        )

        # Sort constructors using latest event prices.
        sorted_constructors = sort_by_latest_price(
            CONSTRUCTORS,
            latest_prices.get("constructors", {}),
            lambda team: team,
        )

        st.caption(
            f"List sorted by prices from the latest event with saved prices: "
            f"{latest_priced_race}."
        )

    else:

        # No saved prices in any event.
        # Use original default listing.
        sorted_drivers = DRIVERS
        sorted_constructors = CONSTRUCTORS

        st.caption(
            "No saved event prices found. Showing the default listing."
        )

    # --------------------------------------------------------
    # RACE SELECTOR
    # --------------------------------------------------------

    selected_race = st.selectbox(
        "Race",
        RACES,
        key="grid_price_race",
    )

    prices[selected_season].setdefault(
        selected_race,
        empty_race(),
    )

    race_prices = prices[selected_season][selected_race]

    st.divider()

    st.subheader(
        f"{selected_race} — {selected_season}"
    )

    # --------------------------------------------------------
    # PRICE INPUT FORM
    # --------------------------------------------------------

    with st.form(
        key=f"price_form_{selected_season}_{selected_race}"
    ):

        # ----------------------------------------------------
        # DRIVERS
        # ----------------------------------------------------

        st.subheader("Drivers")

        driver_values = {}

        for number, name, team in sorted_drivers:

            existing = race_prices["drivers"].get(
                number,
                {},
            )

            old_price = existing.get("price")

            default_value = (
                str(old_price).replace(".", ",")
                if old_price is not None
                else ""
            )

            driver_values[number] = st.text_input(
                f"{name} — {team} (#{number})",
                value=default_value,
                placeholder="e.g. 14,5",
                key=(
                    f"price_driver_"
                    f"{selected_season}_"
                    f"{selected_race}_"
                    f"{number}"
                ),
            )

        st.divider()

        # ----------------------------------------------------
        # CONSTRUCTORS
        # ----------------------------------------------------

        st.subheader("Constructors / Teams")

        constructor_values = {}

        for team in sorted_constructors:

            existing = race_prices["constructors"].get(
                team,
                {},
            )

            old_price = existing.get("price")

            default_value = (
                str(old_price).replace(".", ",")
                if old_price is not None
                else ""
            )

            constructor_values[team] = st.text_input(
                team,
                value=default_value,
                placeholder="e.g. 11,4",
                key=(
                    f"price_team_"
                    f"{selected_season}_"
                    f"{selected_race}_"
                    f"{team}"
                ),
            )

        st.divider()

        # ----------------------------------------------------
        # SAVE BUTTON
        # ----------------------------------------------------

        submitted = st.form_submit_button(
            "Save prices",
            type="primary",
            use_container_width=True,
        )

    # ========================================================
    # SAVE AND VALIDATE
    # ========================================================

    if submitted:

        errors = []

        new_drivers = {}
        new_constructors = {}

        # ----------------------------------------------------
        # VALIDATE DRIVERS
        # ----------------------------------------------------

        for number, name, team in DRIVERS:

            raw_value = driver_values[number]

            price = parse_price(raw_value)

            if price == "invalid":

                errors.append(
                    f"{name}: invalid price '{raw_value}'"
                )

                continue

            new_drivers[number] = {
                "name": name,
                "team": team,
                "price": price,
            }

        # ----------------------------------------------------
        # VALIDATE CONSTRUCTORS
        # ----------------------------------------------------

        for team in CONSTRUCTORS:

            raw_value = constructor_values[team]

            price = parse_price(raw_value)

            if price == "invalid":

                errors.append(
                    f"{team}: invalid price '{raw_value}'"
                )

                continue

            new_constructors[team] = {
                "price": price,
            }

        # ----------------------------------------------------
        # SHOW ERRORS
        # ----------------------------------------------------

        if errors:

            st.error(
                "Please correct the following prices:"
            )

            for error in errors:
                st.write(f"- {error}")

        # ----------------------------------------------------
        # SAVE SUCCESSFULLY
        # ----------------------------------------------------

        else:

            prices[selected_season][selected_race] = {
                "drivers": new_drivers,
                "constructors": new_constructors,
            }

            try:

                save_prices(prices)

                st.success(
                    f"Prices saved for "
                    f"{selected_race} {selected_season}!"
                )

            except OSError as exc:

                st.error(
                    f"Could not save prices: {exc}"
                )

    # ========================================================
    # INFORMATION
    # ========================================================

    st.divider()

    st.caption(
        "Prices are stored locally in "
        "data/grid_rival_prices.json. "
        "Each race has its own independent prices. "
        "The list is sorted using the latest event with saved prices. "
        "No OpenF1 API requests are made by this page."
    )
