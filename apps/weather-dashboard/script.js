// WMO Weather interpretation codes (WW)
const WMO_CODES = {
    0: { desc: 'Clear sky', icon: '☀️' },
    1: { desc: 'Mainly clear', icon: '🌤️' },
    2: { desc: 'Partly cloudy', icon: '⛅' },
    3: { desc: 'Overcast', icon: '☁️' },
    45: { desc: 'Foggy', icon: '🌫️' },
    48: { desc: 'Depositing rime fog', icon: '🌫️' },
    51: { desc: 'Light drizzle', icon: '🌦️' },
    53: { desc: 'Moderate drizzle', icon: '🌦️' },
    55: { desc: 'Dense drizzle', icon: '🌧️' },
    61: { desc: 'Slight rain', icon: '🌧️' },
    63: { desc: 'Moderate rain', icon: '🌧️' },
    65: { desc: 'Heavy rain', icon: '🌧️' },
    71: { desc: 'Slight snow', icon: '🌨️' },
    73: { desc: 'Moderate snow', icon: '🌨️' },
    75: { desc: 'Heavy snow', icon: '❄️' },
    77: { desc: 'Snow grains', icon: '🌨️' },
    80: { desc: 'Slight rain showers', icon: '🌦️' },
    81: { desc: 'Moderate rain showers', icon: '🌧️' },
    82: { desc: 'Violent rain showers', icon: '⛈️' },
    85: { desc: 'Slight snow showers', icon: '🌨️' },
    86: { desc: 'Heavy snow showers', icon: '❄️' },
    95: { desc: 'Thunderstorm', icon: '⛈️' },
    96: { desc: 'Thunderstorm with slight hail', icon: '⛈️' },
    99: { desc: 'Thunderstorm with heavy hail', icon: '⛈️' }
};

const cityInput = document.getElementById('cityInput');
const searchBtn = document.getElementById('searchBtn');
const geoBtn = document.getElementById('geoBtn');
const statusMsg = document.getElementById('statusMsg');
const weatherCard = document.getElementById('weatherCard');

const cityNameEl = document.getElementById('cityName');
const countryNameEl = document.getElementById('countryName');
const dateTimeEl = document.getElementById('dateTime');
const weatherIconEl = document.getElementById('weatherIcon');
const tempValueEl = document.getElementById('tempValue');
const weatherDescEl = document.getElementById('weatherDesc');
const windSpeedEl = document.getElementById('windSpeed');
const humidityEl = document.getElementById('humidity');
const feelsLikeEl = document.getElementById('feelsLike');
const windDirEl = document.getElementById('windDir');

function getWindDirection(deg) {
    const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
    const index = Math.round((deg % 360) / 22.5) % 16;
    return `${directions[index]} (${Math.round(deg)}°)`;
}

function showStatus(message, isError = false) {
    statusMsg.textContent = message;
    statusMsg.className = `status-msg ${isError ? 'error' : ''}`;
    statusMsg.classList.remove('hidden');
    weatherCard.classList.add('hidden');
}

function hideStatus() {
    statusMsg.classList.add('hidden');
    weatherCard.classList.remove('hidden');
}

async function fetchWeather(lat, lon, city, country) {
    try {
        showStatus('Fetching live weather conditions...');
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m&timezone=auto`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed to retrieve forecast data.');
        const data = await res.json();
        const current = data.current;

        const codeInfo = WMO_CODES[current.weather_code] || { desc: 'Unknown', icon: '🌡️' };

        cityNameEl.textContent = city;
        countryNameEl.textContent = country;
        dateTimeEl.textContent = new Date().toLocaleDateString(undefined, {
            weekday: 'long',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        weatherIconEl.textContent = codeInfo.icon;
        tempValueEl.textContent = Math.round(current.temperature_2m);
        weatherDescEl.textContent = codeInfo.desc;

        windSpeedEl.textContent = `${current.wind_speed_10m} km/h`;
        humidityEl.textContent = `${current.relative_humidity_2m}%`;
        feelsLikeEl.textContent = `${Math.round(current.apparent_temperature)}°C`;
        windDirEl.textContent = getWindDirection(current.wind_direction_10m);

        hideStatus();
    } catch (err) {
        showStatus(err.message || 'Error loading weather data.', true);
    }
}

async function searchCity(query) {
    if (!query || !query.trim()) return;
    try {
        showStatus(`Locating "${query}"...`);
        const geoUrl = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(query.trim())}&count=1&language=en&format=json`;
        const res = await fetch(geoUrl);
        if (!res.ok) throw new Error('Geocoding service unavailable.');
        const data = await res.json();

        if (!data.results || data.results.length === 0) {
            showStatus(`City "${query}" not found. Please try another search.`, true);
            return;
        }

        const place = data.results[0];
        const country = [place.admin1, place.country].filter(Boolean).join(', ');
        await fetchWeather(place.latitude, place.longitude, place.name, country);
    } catch (err) {
        showStatus(err.message || 'Failed to search city.', true);
    }
}

searchBtn.addEventListener('click', () => searchCity(cityInput.value));
cityInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') searchCity(cityInput.value);
});

geoBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
        showStatus('Geolocation is not supported by your browser.', true);
        return;
    }
    showStatus('Requesting GPS coordinates...');
    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const { latitude, longitude } = position.coords;
            await fetchWeather(latitude, longitude, 'Current Location', 'GPS');
        },
        () => {
            showStatus('Location permission denied or unavailable.', true);
        }
    );
});

// Load default city on startup
searchCity('London');
