
import itertools
from decimal import Decimal, InvalidOperation

import pandas as pd
import streamlit as st

from app.grid_rival_prices import RACES, SEASONS, load_prices


def _as_decimal(value):
    if value is None or str(value).strip() == "":
        return None

    try:
        price = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None

    if not price.is_finite() or price < 0:
        return None

    return price


def _format_price(value):
    if value is None:
        return "Not set"
    return f"{value:.1f}".replace(".", ",")


def _format_estimates(estimates):
    """Display the five driver estimates in lineup order."""
    return " / ".join(str(value) for value in estimates)

def _calculate_est_avg(estimates):
    """Calculate the average of available numeric EST values."""

    numeric_values = []

    for estimate in estimates:
        try:
            value = float(str(estimate).replace(",", "."))

            if value >= 0:
                numeric_values.append(value)

        except (ValueError, TypeError):
            continue

    if not numeric_values:
        return "NT"

    return f"{sum(numeric_values) / len(numeric_values):.1f}"

def _lineup_signature(season, race, budget, driver_choices, constructor_choices):
    return (
        season,
        race,
        str(budget),
        tuple(sorted(driver_choices.items())),
        tuple(sorted(constructor_choices.items())),
    )


def _calculate_lineups(drivers, constructors, budget):
    """Calculate all affordable combinations of 5 drivers and 1 constructor."""

    results = []

    eligible_drivers = [
        driver for driver in drivers
        if driver["included"] and driver["price"] is not None
    ]

    eligible_constructors = [
        constructor for constructor in constructors
        if constructor["included"] and constructor["price"] is not None
    ]

    if len(eligible_drivers) < 5 or not eligible_constructors:
        return results

    for driver_group in itertools.combinations(eligible_drivers, 5):

        driver_total = sum(
            (driver["price"] for driver in driver_group),
            Decimal("0"),
        )

        for constructor in eligible_constructors:

            total = driver_total + constructor["price"]

            if total <= budget:
                results.append({
                    "drivers": [
                        driver["name"] for driver in driver_group
                    ],
                    "estimates": [
                        driver["estimate"] for driver in driver_group
                    ],
                    "constructor": constructor["name"],
                    "total": total,
                    "remaining": budget - total,
                })

    # Highest-priced valid lineups first.
    results.sort(
        key=lambda item: (
            -item["total"],
            tuple(item["drivers"]),
            item["constructor"],
        )
    )

    return results


def render_grid_rival_lineup():

    st.header("Grid Rival lineup")

    st.caption(
        "Find every affordable lineup containing exactly 5 drivers "
        "and 1 constructor."
    )

    prices = load_prices()

    # ========================================================
    # SELECTORS
    # ========================================================

    top_col1, top_col2, top_col3 = st.columns([1, 1, 1.2])

    with top_col1:
        selected_season = st.selectbox(
            "Season",
            SEASONS,
            key="lineup_season",
        )

    with top_col2:
        selected_race = st.selectbox(
            "Race",
            RACES,
            key="lineup_race",
        )

    with top_col3:
        budget_text = st.text_input(
            "Budget",
            value="100,0",
            placeholder="e.g. 104,5",
            key="lineup_budget_text",
        )

    budget = _as_decimal(budget_text)

    race_data = (
        prices.get(selected_season, {})
        .get(selected_race, {})
    )

    race_drivers = race_data.get("drivers", {})
    race_constructors = race_data.get("constructors", {})

    if not isinstance(race_drivers, dict):
        race_drivers = {}

    if not isinstance(race_constructors, dict):
        race_constructors = {}

    # ========================================================
    # GET EXISTING ESTIMATES FROM GRID RIVALS
    # ========================================================

    # These values are populated by grid_rivals.py.
    # They are not recalculated here.
    race_estimates = st.session_state.get(
        "grid_rivals_estimates",
        {},
    )

    if not isinstance(race_estimates, dict):
        race_estimates = {}

    st.divider()

    driver_choices = {}
    constructor_choices = {}

    driver_records = []
    constructor_records = []

    # ========================================================
    # DRIVERS
    # EST IS NOT DISPLAYED IN THIS LIST.
    # ========================================================

    st.subheader("Drivers")

    st.caption(
        "Choose Include or Exclude for each driver."
    )

    header_cols = st.columns([4.5, 1.4, 2.2])

    header_cols[0].markdown("**Driver**")
    header_cols[1].markdown("**Price**")
    header_cols[2].markdown("**Selection**")

    if not race_drivers:
        st.warning(
            "No driver prices were found for this race. "
            "Add prices in the Grid Rival price tab first."
        )

    for driver_key, details in race_drivers.items():

        details = details if isinstance(details, dict) else {}

        driver_key = str(driver_key)

        name = str(
            details.get("name") or f"Driver {driver_key}"
        )

        team = str(details.get("team") or "")

        price = _as_decimal(details.get("price"))

        # Retrieve the existing estimate from Grid Rivals.
        estimate = race_estimates.get(driver_key, "NT")

        if estimate is None or str(estimate).strip() == "":
            estimate = "NT"
        else:
            estimate = str(estimate)

        row = st.columns([4.5, 1.4, 2.2])

        driver_label = (
            f"{name} — {team}" if team else name
        )

        row[0].write(driver_label)
        row[1].write(_format_price(price))

        choice_key = (
            f"lineup_driver_{selected_season}_"
            f"{selected_race}_{driver_key}"
        )

        choice = row[2].radio(
            "Selection",
            options=["Include", "Exclude"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key=choice_key,
        )

        driver_choices[driver_key] = choice

        driver_records.append({
            "key": driver_key,
            "name": name,
            "team": team,
            "price": price,
            "estimate": estimate,
            "included": choice == "Include",
        })

    # ========================================================
    # CONSTRUCTORS
    # ========================================================

    st.divider()

    st.subheader("Constructors / Teams")

    header_cols = st.columns([4.5, 1.4, 2.2])

    header_cols[0].markdown("**Constructor**")
    header_cols[1].markdown("**Price**")
    header_cols[2].markdown("**Selection**")

    if not race_constructors:
        st.warning(
            "No constructor prices were found for this race. "
            "Add prices in the Grid Rival price tab first."
        )

    for constructor_name, details in race_constructors.items():

        details = details if isinstance(details, dict) else {}

        price = _as_decimal(details.get("price"))

        row = st.columns([4.5, 1.4, 2.2])

        row[0].write(str(constructor_name))
        row[1].write(_format_price(price))

        choice_key = (
            f"lineup_constructor_{selected_season}_"
            f"{selected_race}_{constructor_name}"
        )

        choice = row[2].radio(
            "Selection",
            options=["Include", "Exclude"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key=choice_key,
        )

        constructor_choices[str(constructor_name)] = choice

        constructor_records.append({
            "name": str(constructor_name),
            "price": price,
            "included": choice == "Include",
        })

    # ========================================================
    # BUDGET AND CALCULATION
    # ========================================================

    st.divider()

    if budget is None:
        st.error("Enter a valid budget, for example 104,5.")
    else:
        st.write(f"**Budget:** {_format_price(budget)}")

    if st.button(
        "Calculate lineups",
        type="primary",
        use_container_width=True,
        disabled=budget is None,
    ):

        if budget is not None:

            result_rows = _calculate_lineups(
                driver_records,
                constructor_records,
                budget,
            )

            signature = _lineup_signature(
                selected_season,
                selected_race,
                budget,
                driver_choices,
                constructor_choices,
            )

            st.session_state["lineup_calculation"] = {
                "signature": signature,
                "results": result_rows,
            }

    # ========================================================
    # DISPLAY CALCULATED RESULTS
    # ========================================================

    saved_calculation = st.session_state.get(
        "lineup_calculation"
    )

    current_signature = (
        _lineup_signature(
            selected_season,
            selected_race,
            budget,
            driver_choices,
            constructor_choices,
        )
        if budget is not None
        else None
    )

    if (
        saved_calculation
        and saved_calculation.get("signature") == current_signature
    ):

        results = saved_calculation["results"]

        st.divider()
        st.subheader("Possible lineups")

        if not results:

            st.warning(
                "No valid lineups found. Check the budget, available prices, "
                "and Include / Exclude selections."
            )

        else:

            st.success(
                f"Found {len(results):,} valid lineups."
            )

            display_rows = []

            for index, result in enumerate(results, start=1):

                display_rows.append({
                    "Rank": index,
                    "Drivers": ", ".join(result["drivers"]),
                    "EST": _format_estimates(result["estimates"]),
                    "EST AVG": _calculate_est_avg(result["estimates"]),
                    "Constructor": result["constructor"],
                    "Total price": _format_price(result["total"]),
                    "Budget remaining": _format_price(result["remaining"]),
                })

            results_df = pd.DataFrame(display_rows)

            # Sort EST AVG numerically instead of alphabetically.
            results_df["_EST_SORT"] = pd.to_numeric(
            results_df["EST AVG"].astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
            )

            results_df = results_df.sort_values(
            by="_EST_SORT",
            ascending=True,
            na_position="last"
            )           .drop(columns=["_EST_SORT"])

            results_df = results_df.reset_index(drop=True)

            # Update rank numbers after sorting.
            results_df["Rank"] = range(1, len(results_df) + 1)

            st.dataframe(
                results_df,
                use_container_width=True,
                hide_index=True,
                height=650,
            )

            csv_data = results_df.to_csv(
                index=False
            ).encode("utf-8-sig")

            st.download_button(
                "Download all lineups as CSV",
                data=csv_data,
                file_name=(
                    f"grid_rival_lineups_"
                    f"{selected_race}_{selected_season}.csv"
                ),
                mime="text/csv",
                use_container_width=True,
            )

    elif saved_calculation:

        st.info(
            "Your budget or selections have changed since the last calculation. "
            "Press Calculate lineups again to update the results."
        )

    # ========================================================
    # MISSING PRICE INFORMATION
    # ========================================================

    missing_driver_prices = sum(
        1 for driver in driver_records
        if driver["price"] is None
    )

    missing_constructor_prices = sum(
        1 for constructor in constructor_records
        if constructor["price"] is None
    )

    if missing_driver_prices or missing_constructor_prices:

        st.caption(
            f"Not included in calculations until priced: "
            f"{missing_driver_prices} driver(s), "
            f"{missing_constructor_prices} constructor(s)."
        )
