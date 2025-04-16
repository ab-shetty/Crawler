// web/static/script.js

const form = document.getElementById('crawlForm');
const resultsDiv = document.getElementById('results');
const loadingDiv = document.getElementById('loading');
const submitBtn = document.getElementById('submitBtn');

form.addEventListener('submit', async (event) => {
    event.preventDefault(); // Prevent default HTML form submission

    const url = document.getElementById('url').value;
    const instructions = document.getElementById('instructions').value;
    const depth = parseInt(document.getElementById('depth').value, 10); // Get depth as integer

    if (!url) {
        resultsDiv.innerHTML = '<pre>Error: URL is required.</pre>';
        return;
    }

    // Show loading indicator and disable button
    loadingDiv.style.display = 'block';
    resultsDiv.innerHTML = ''; // Clear previous results
    submitBtn.disabled = true;
    submitBtn.textContent = 'Scraping...';

    const requestBody = {
        url: url,
        instructions: instructions,
        depth: depth // Include depth in the request
    };

    try {
        const response = await fetch('/api/scrape', { // Call your FastAPI endpoint
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json' // Expect JSON response
            },
            body: JSON.stringify(requestBody)
        });

        loadingDiv.style.display = 'none'; // Hide loading indicator
        submitBtn.disabled = false;       // Re-enable button
        submitBtn.textContent = 'Start Scraping';

        const result = await response.json(); // Parse the JSON response body

        if (!response.ok) {
            // Handle HTTP errors (like 4xx, 5xx)
            const errorMsg = result.detail || `HTTP error! Status: ${response.status}`;
            resultsDiv.innerHTML = `<pre>Error: ${escapeHtml(errorMsg)}</pre>`;
            console.error('API Error:', result);
        } else {
            // Display successful results
            // The 'data' field should contain the list of dictionaries
            const formattedResult = JSON.stringify(result, null, 2); // Pretty print JSON
            resultsDiv.innerHTML = `<pre>${escapeHtml(formattedResult)}</pre>`;
            console.log('API Success:', result);
        }

    } catch (error) {
        // Handle network errors or issues with fetch itself
        loadingDiv.style.display = 'none';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Start Scraping';
        resultsDiv.innerHTML = `<pre>Network or script error: ${escapeHtml(error.message)}</pre>`;
        console.error('Fetch Error:', error);
    }
});

// Basic HTML escaping function to prevent XSS
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}
