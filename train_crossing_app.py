import streamlit as st
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import folium
from streamlit_folium import st_folium
import openrouteservice
from gtts import gTTS
import tempfile
import os

# Set page title
st.title("Riverside Train Crossing Navigator")

# Define key railroad crossing points in Riverside, California (exact crossing locations)
train_crossings = {
    "Mission Inn Ave & Vine St": (33.982802, -117.374213),
    "3rd St & Vine St": (33.983955, -117.374504),
    "Kansas Ave & Spruce St": (33.987775, -117.369103),
    "Chicago Ave & Marlborough Ave": (33.972620, -117.345799),
    "Howard Ave & Center St": (33.960915, -117.344325),
    "Central Ave & 9th St": (33.952437, -117.386746),
    "University Ave & California Ave": (33.979278, -117.337070),
    "Riverwalk Parkway & Pierce St": (33.986728, -117.328611),
    "Riverside Ave & La Cadena Dr": (33.993241, -117.437265),
    "Civic Center Dr & 14th St": (33.986057, -117.375654)
}

st.markdown("### Step 1: Enter Start and End Addresses")
with st.expander("Instructions"):
    st.markdown("- Enter the **Start** and **End** addresses below.")
    st.markdown("- The app will geocode the addresses and calculate the route.")
    st.markdown("- Known train crossings are shown in red.")

# Initialize session state
if "points" not in st.session_state:
    st.session_state.points = []
if "route_geojson" not in st.session_state:
    st.session_state.route_geojson = None
if "directions" not in st.session_state:
    st.session_state.directions = []  # Store turn-by-turn directions
if "route_segments" not in st.session_state:  # Initialize route_segments
    st.session_state.route_segments = []
if "current_step" not in st.session_state:
    st.session_state.current_step = 0  # Keep track of current navigation step
if "route_calculated" not in st.session_state:
    st.session_state.route_calculated = False  # Flag to track if the route has been calculated

# Geocoding function using Geopy with increased timeout and better error handling
def geocode_address(address):
    geolocator = Nominatim(user_agent="train-crossing-navigator")
    try:
        location = geolocator.geocode(address, timeout=10)  # Timeout set to 10 seconds
        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    except GeocoderTimedOut:
        st.error("Geocoding service timed out. Please try again.")
        return None
    except GeocoderUnavailable:
        st.error("Geocoding service is unavailable. Please try again later.")
        return None

# User inputs for addresses
start_address = st.text_input("Start Address")
end_address = st.text_input("End Address")

# Travel mode selection
travel_mode = st.selectbox("Travel Mode", ["Walking", "Driving", "Biking"])
mode_map = {
    "Walking": "foot-walking",
    "Driving": "driving-car",
    "Biking": "cycling-regular"
}

# Route calculation with selected travel mode
def calculate_route(start_coords, end_coords, travel_mode):
    coords = [(start_coords[1], start_coords[0]), (end_coords[1], end_coords[0])]  # lng, lat
    try:
        route = client.directions(
            coordinates=coords,
            profile=travel_mode,
            format='geojson',
            radiuses=[1000, 1000]  # Increase the search radius to 1000 meters
        )
        st.session_state.route_geojson = route
        directions, segments = [], []
        for step in route['features'][0]['properties']['segments'][0]['steps']:
            directions.append(step['instruction'])
            segments.append(step.get('geometry', {}).get('coordinates', []))
        st.session_state.directions = directions
        st.session_state.route_segments = segments
        st.session_state.current_step = 0
        st.session_state.route_calculated = True  # Set flag to True after route calculation
    except Exception as e:
        st.error(f"Error retrieving route: {e}")

# OpenRouteService API
ORS_API_KEY = "5b3ce3597851110001cf62481eb9f4d398e9490f8399878029429326"
client = openrouteservice.Client(key=ORS_API_KEY)

# Geocode and store coordinates only once when both addresses are input
if start_address and end_address and not st.session_state.route_calculated:
    start_coords = geocode_address(start_address)
    end_coords = geocode_address(end_address)

    if start_coords and end_coords:
        st.session_state.points = [start_coords, end_coords]
        st.session_state.route_geojson = None  # Clear previous route to force rerouting
        st.session_state.directions = []  # Reset directions
        st.session_state.route_segments = []  # Reset route segments
        st.session_state.current_step = 0  # Reset step
        if st.button("Calculate Route"):
            calculate_route(start_coords, end_coords, mode_map[travel_mode])
    else:
        st.error("Could not geocode one or both addresses. Please try again.")

# Function to play audio instruction
def play_audio_instruction(text):
    tts = gTTS(text=text, lang='en')
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tts.save(tmpfile.name)
        tmpfile.close()
        st.audio(tmpfile.name, format="audio/mp3")
        os.remove(tmpfile.name)  # Delete the file after playing

# Ensure the current step is within bounds
if st.session_state.directions:
    current_step = st.session_state.current_step
    total_steps = len(st.session_state.directions)

    # If current_step exceeds total steps, reset to last step
    if current_step >= total_steps:
        st.session_state.current_step = total_steps - 1
        current_step = total_steps - 1

    # Show current navigation step
    st.write(f"### Step {current_step + 1}: {st.session_state.directions[current_step]}")

    # Play audio for the current step
    play_audio_instruction(st.session_state.directions[current_step])

    # Navigation buttons to progress through steps
    col1, col2 = st.columns([1, 1])
    with col1:
        if current_step > 0:
            if st.button("Previous Step"):
                st.session_state.current_step -= 1  # Indented properly to be inside the if statement

    with col2:
        if current_step < total_steps - 1:
            if st.button("Next Step"):
                st.session_state.current_step += 1  # Indented properly to be inside the if statement

# Show route map if available
if st.session_state.route_geojson:
    start, end = st.session_state.points
    result_map = folium.Map(location=start, zoom_start=14)
    folium.Marker(start, tooltip="Start", icon=folium.Icon(color="green")).add_to(result_map)
    folium.Marker(end, tooltip="End", icon=folium.Icon(color="blue")).add_to(result_map)

    for name, loc in train_crossings.items():
        folium.Marker(loc, popup=name, icon=folium.Icon(color='red')).add_to(result_map)

    folium.GeoJson(st.session_state.route_geojson, name="Route").add_to(result_map)

    st.markdown("### Step 2: Route Result")
    st_folium(result_map, height=400, width=700)




