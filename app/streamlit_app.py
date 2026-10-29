"""Dashboard entry point: uv run --group app streamlit run app/streamlit_app.py"""

import streamlit as st

st.set_page_config(
    page_title="Metro housing affordability", page_icon="🏠", layout="wide"
)
st.navigation(
    [
        st.Page("views/overview.py", title="Overview", icon=":material/leaderboard:"),
        st.Page(
            "views/metro.py", title="Metro detail", icon=":material/location_city:"
        ),
        st.Page("views/migration.py", title="Migration", icon=":material/moving:"),
        st.Page("views/forecasts.py", title="Forecasts", icon=":material/trending_up:"),
    ],
    position="top",
).run()
