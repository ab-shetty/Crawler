// web/static/script.js

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const form = document.getElementById('crawlForm');
    const resultsContainer = document.getElementById('results-container');
    const resultsDiv = document.getElementById('results');
    const loadingDiv = document.getElementById('loading');
    const submitBtn = document.getElementById('submitBtn');
    const resetBtn = document.getElementById('resetBtn');
    const depthRange = document.getElementById('depth');
    const depthValue = document.getElementById('depthValue');
    const maxPagesRange = document.getElementById('max_pages');
    const maxPagesValue = document.getElementById('maxPagesValue');
    const downloadJsonBtn = document.getElementById('downloadJson');
    const downloadMarkdownBtn = document.getElementById('downloadMarkdown');
    
    // Store crawl results for download
    let currentResults = null;
    let currentRequest = null;
    
    // Update depth value display when slider changes
    depthRange.addEventListener('input', function() {
        depthValue.textContent = this.value;
    });
    
    // Update max pages value display when slider changes
    maxPagesRange.addEventListener('input', function() {
        maxPagesValue.textContent = this.value;
    });
    
    // Reset form
    resetBtn.addEventListener('click', function() {
        form.reset();
        depthValue.textContent = '0';
        maxPagesValue.textContent = '20';
        resultsContainer.style.display = 'none';
        resultsDiv.innerHTML = '';
        currentResults = null;
        currentRequest = null;
    });
    
    // Handle form submission
    form.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default HTML form submission

        const url = document.getElementById('url').value;
        const instructions = document.getElementById('instructions').value;
        const depth = parseInt(depthRange.value, 10);
        const maxPages = parseInt(maxPagesRange.value, 10);
        const followExternal = document.getElementById('follow_external').checked;

        if (!url) {
            showError("URL is required");
            return;
        }

        // Show loading indicator and disable button
        loadingDiv.style.display = 'flex';
        resultsContainer.style.display = 'none';
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-sm"></span> Processing...';

        const requestBody = {
            url: url,
            instructions: instructions,
            depth: depth,
            follow_external_links: followExternal,
            max_pages: maxPages
        };
        
        // Save current request for download options
        currentRequest = {
            url: url,
            instructions: instructions,
            depth: depth,
            max_pages: maxPages
        };

        try {
            const response = await fetch('/api/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            // Hide loading, restore button
            loadingDiv.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Scraping';

            const result = await response.json();

            if (!response.ok) {
                const errorMsg = result.detail || `HTTP error! Status: ${response.status}`;
                showError(errorMsg);
                console.error('API Error:', result);
            } else {
                // Save results for download
                currentResults = result.data;
                
                // Display successful results
                displayResults(result);
                
                // Show download options
                resultsContainer.style.display = 'block';
            }

        } catch (error) {
            // Handle network errors
            loadingDiv.style.display = 'none';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Start Scraping';
            
            showError(`Network or script error: ${error.message}`);
            console.error('Fetch Error:', error);
        }
    });
    
    // Handle JSON download
    downloadJsonBtn.addEventListener('click', function() {
        if (!currentResults) {
            showError("No results to download");
            return;
        }
        
        downloadResults('json');
    });
    
    // Handle Markdown download
    downloadMarkdownBtn.addEventListener('click', function() {
        if (!currentResults) {
            showError("No results to download");
            return;
        }
        
        downloadResults('markdown');
    });
    
    // Download results function
    async function downloadResults(format) {
        try {
            // Create request with results data
            const requestBody = {
                data: currentResults,
                format: format,
                url: currentRequest?.url || 'unknown',
                instructions: currentRequest?.instructions || 'No instructions',
                depth: currentRequest?.depth || 0,
                max_pages: currentRequest?.max_pages || 20
            };
            
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Download failed: ${errorText}`);
            }
            
            // Get the file from the response
            const blob = await response.blob();
            
            // Create a download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // Get filename from content-disposition header or use default
            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'crawler_results';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1];
                }
            }
            
            // Add extension if not present
            if (!filename.includes('.')) {
                filename += format === 'json' ? '.json' : '.md';
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            
            // Cleanup
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            showError(`Download error: ${error.message}`);
            console.error('Download Error:', error);
        }
    }
    
    // Display results function
    function displayResults(result) {
        resultsDiv.innerHTML = '';
        
        if (!result.data || result.data.length === 0) {
            resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
            return;
        }
        
        // Create a summary element
        const summary = document.createElement('div');
        summary.className = 'results-summary';
        summary.innerHTML = `
            <p><strong>Pages Crawled:</strong> ${result.data.length}</p>
            <p><strong>Max Pages Setting:</strong> ${currentRequest.max_pages || 20}</p>
        `;
        resultsDiv.appendChild(summary);
        
        // Display each page's results
        result.data.forEach((page, index) => {
            const pageElement = document.createElement('div');
            pageElement.className = 'page-result';
            
            // Page header
            const pageHeader = document.createElement('div');
            pageHeader.className = 'page-header';
            pageHeader.innerHTML = `
                <h3>${page.title || 'Untitled Page'}</h3>
                <div class="page-url">${page.url}</div>
            `;
            pageElement.appendChild(pageHeader);
            
            // Page content
            const pageContent = document.createElement('div');
            pageContent.className = 'page-content';
            
            // Check for errors
            if (page.error) {
                pageContent.innerHTML = `
                    <div class="error-message">
                        Error: ${escapeHtml(page.error)}
                    </div>
                `;
            } else if (page.ai_extracted_content) {
                // Display AI-extracted content
                const aiContent = page.ai_extracted_content;
                let aiHtml = '';
                
                // Add summary if available
                if (aiContent.summary) {
                    aiHtml += `
                        <div class="ai-summary">
                            <h4>AI Summary</h4>
                            <p>${escapeHtml(aiContent.summary)}</p>
                        </div>
                    `;
                }
                
                // Add key points if available
                if (aiContent.key_points && aiContent.key_points.length > 0) {
                    aiHtml += `<h4>Key Points</h4><ul class="ai-points">`;
                    aiContent.key_points.forEach(point => {
                        aiHtml += `<li>${escapeHtml(point)}</li>`;
                    });
                    aiHtml += `</ul>`;
                }
                
                // Add extracted data if available
                if (aiContent.extracted_data && Object.keys(aiContent.extracted_data).length > 0) {
                    aiHtml += `<h4>Extracted Data</h4><dl class="ai-data">`;
                    for (const [key, value] of Object.entries(aiContent.extracted_data)) {
                        aiHtml += `
                            <dt>${escapeHtml(key)}</dt>
                            <dd>${escapeHtml(String(value))}</dd>
                        `;
                    }
                    aiHtml += `</dl>`;
                }
                
                // Add relevance info
                if (page.relevance) {
                    const relevancePercentage = Math.round(page.relevance.score * 100);
                    aiHtml += `
                        <div class="relevance-info">
                            <div class="relevance-score">
                                <div class="score-bar">
                                    <div class="score-fill" style="width: ${relevancePercentage}%"></div>
                                </div>
                                <div class="score-value">${relevancePercentage}% Relevant</div>
                            </div>
                            <div class="relevance-reason">${escapeHtml(page.relevance.reason || '')}</div>
                        </div>
                    `;
                }
                
                pageContent.innerHTML = aiHtml;
            } else if (page.paragraphs && page.paragraphs.length > 0) {
                // Display paragraphs if AI content is not available
                const paragraphsHtml = page.paragraphs
                    .map(p => `<p>${escapeHtml(p)}</p>`)
                    .join('');
                
                pageContent.innerHTML = `<div class="content-paragraphs">${paragraphsHtml}</div>`;
            } else {
                pageContent.innerHTML = `<div class="no-content">No content extracted</div>`;
            }
            
            pageElement.appendChild(pageContent);
            
            // Add links section (collapsed by default)
            if (page.links && page.links.length > 0) {
                const linksContainer = document.createElement('div');
                linksContainer.className = 'links-container';
                
                const linksToggle = document.createElement('button');
                linksToggle.className = 'links-toggle';
                linksToggle.textContent = `Show ${page.links.length} Links`;
                linksToggle.onclick = function() {
                    const linksList = this.nextElementSibling;
                    if (linksList.style.display === 'none' || !linksList.style.display) {
                        linksList.style.display = 'block';
                        this.textContent = 'Hide Links';
                    } else {
                        linksList.style.display = 'none';
                        this.textContent = `Show ${page.links.length} Links`;
                    }
                };
                
                const linksList = document.createElement('ul');
                linksList.className = 'links-list';
                linksList.style.display = 'none';
                
                page.links.forEach(link => {
                    const li = document.createElement('li');
                    li.innerHTML = `<a href="${escapeHtml(link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(link)}</a>`;
                    linksList.appendChild(li);
                });
                
                linksContainer.appendChild(linksToggle);
                linksContainer.appendChild(linksList);
                pageElement.appendChild(linksContainer);
            }
            
            resultsDiv.appendChild(pageElement);
        });
    }
    
    // Show error message
    function showError(message) {
        resultsContainer.style.display = 'block';
        resultsDiv.innerHTML = `
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <div class="error-message">${escapeHtml(message)}</div>
            </div>
        `;
    }
    
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
});