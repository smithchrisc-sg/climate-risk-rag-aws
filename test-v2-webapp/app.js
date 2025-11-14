// Global variables for authentication and state
let currentToken = null;
let tokenExpiry = null;

// Global state for cursor-based pagination
let currentSearchState = {
    query: '',
    filters: {},
    pageSize: 20,
    currentPage: 1,
    totalPages: 1,
    queryId: null,
    lastCursor: null
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Check authentication state
    if (!currentToken || Date.now() > tokenExpiry) {
        showAuthModal();
    } else {
        showMainInterface();
        updateUserInfo();
    }
    
    // Set up event listeners
    setupEventListeners();
}

function setupEventListeners() {
    // Search functionality
    document.getElementById('searchButton').addEventListener('click', performNewSearch);
    document.getElementById('searchQuery').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performNewSearch();
        }
    });
    
    // Filter change handlers with mutual exclusion for location
    document.querySelectorAll('.filter-dropdown').forEach(select => {
        select.addEventListener('change', handleFilterChange);
    });
    
    // Add mutual exclusion for region vs country selection
    document.getElementById('regionFilter').addEventListener('change', function() {
        if (this.value) {
            // Clear country selection when region is selected
            const countrySelect = document.getElementById('countryFilter');
            Array.from(countrySelect.options).forEach(option => option.selected = false);
        }
    });
    
    document.getElementById('countryFilter').addEventListener('change', function() {
        const selectedCountries = Array.from(this.selectedOptions);
        if (selectedCountries.length > 0) {
            // Clear region selection when countries are selected
            document.getElementById('regionFilter').value = '';
        }
    });
    
    // Bookmark folder toggles
    document.querySelectorAll('.folder-header').forEach(header => {
        header.addEventListener('click', toggleBookmarkFolder);
    });
    
    // Sort button handlers
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.addEventListener('click', handleSortClick);
    });
    
    // Mobile menu functionality
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');
    const mobileOverlay = document.getElementById('mobileOverlay');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('open');
            mobileOverlay.classList.toggle('active');
        });
    }
    
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', function() {
            sidebar.classList.remove('open');
            mobileOverlay.classList.remove('active');
        });
    }
    
    // Close mobile menu when window is resized to desktop
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('open');
            mobileOverlay.classList.remove('active');
        }
    });
}

// Authentication Functions
async function authenticate() {
    const email = document.getElementById('authEmail').value.trim();
    const password = document.getElementById('authPassword').value.trim();
    const userPoolId = document.getElementById('userPoolId').value.trim();
    const clientId = document.getElementById('clientId').value.trim();
    const clientSecret = document.getElementById('clientSecret').value.trim();
    const authButton = document.getElementById('authButton');
    const authStatus = document.getElementById('authStatus');
    
    if (!email || !password) {
        showAuthStatus('Please enter email and password', 'error');
        return;
    }
    
    authButton.disabled = true;
    authButton.textContent = 'Signing In...';
    showAuthStatus('Authenticating with Cognito...', 'loading');
    
    try {
        // Calculate SECRET_HASH using Web Crypto API
        const message = email + clientId;
        const key = await window.crypto.subtle.importKey(
            'raw',
            new TextEncoder().encode(clientSecret),
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['sign']
        );
        const signature = await window.crypto.subtle.sign('HMAC', key, new TextEncoder().encode(message));
        const secretHash = btoa(String.fromCharCode(...new Uint8Array(signature)));
        
        // Authenticate with Cognito
        const authResponse = await fetch('https://cognito-idp.us-east-1.amazonaws.com/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
            },
            body: JSON.stringify({
                ClientId: clientId,
                AuthFlow: 'USER_PASSWORD_AUTH',
                AuthParameters: {
                    USERNAME: email,
                    PASSWORD: password,
                    SECRET_HASH: secretHash
                }
            })
        });
        
        if (!authResponse.ok) {
            const errorData = await authResponse.json();
            throw new Error(errorData.message || `Authentication failed: ${authResponse.status}`);
        }
        
        const authData = await authResponse.json();
        currentToken = authData.AuthenticationResult.IdToken;  // Use IdToken for API Gateway Cognito User Pool authorizer
        tokenExpiry = Date.now() + (authData.AuthenticationResult.ExpiresIn * 1000);
        
        showAuthStatus('Authentication successful!', 'success');
        
        // Hide modal and show main interface
        setTimeout(() => {
            hideAuthModal();
            showMainInterface();
            updateUserInfo();
        }, 1000);
        
    } catch (error) {
        console.error('Authentication error:', error);
        showAuthStatus(`Authentication failed: ${error.message}`, 'error');
        currentToken = null;
        tokenExpiry = null;
    } finally {
        authButton.disabled = false;
        authButton.textContent = 'Sign In';
    }
}

function showAuthStatus(message, type) {
    const authStatus = document.getElementById('authStatus');
    authStatus.textContent = message;
    authStatus.className = `auth-status ${type}`;
    authStatus.style.display = 'block';
}

function showAuthModal() {
    document.getElementById('authModal').style.display = 'flex';
    document.querySelector('.main-container').style.display = 'none';
}

function hideAuthModal() {
    document.getElementById('authModal').style.display = 'none';
}

function showMainInterface() {
    document.querySelector('.main-container').style.display = 'grid';
    hideAuthModal();
}

function updateUserInfo() {
    // Extract user info from email or use service account name
    const email = document.getElementById('authEmail').value;
    const serviceName = email.includes('gaip') ? 'GAIP Service' : 'SolveGlobal Service';
    document.getElementById('userInfo').textContent = serviceName;
}

// Search Functions
function performNewSearch() {
    // Reset search state for new searches
    currentSearchState = {
        query: '',
        filters: {},
        pageSize: 20,
        currentPage: 1,
        totalPages: 1,
        queryId: null,
        lastCursor: null
    };
    
    // Remove page parameter from URL
    const url = new URL(window.location);
    url.searchParams.delete('page');
    window.history.replaceState({}, '', url);
    
    // Perform the search
    performSearch();
}

async function performSearch(targetPage = null) {
    if (!currentToken || Date.now() > tokenExpiry) {
        showAuthModal();
        return;
    }
    
    const query = document.getElementById('searchQuery').value.trim();
    const maxResults = parseInt(document.getElementById('maxResults').value);
    const apiEndpoint = document.getElementById('apiEndpoint').value.trim();
    
    if (!query) {
        showResults('Please enter a search query', 'error');
        return;
    }
    
    // Collect filter values
    const filters = collectFilterValues();
    
    const searchButton = document.getElementById('searchButton');
    const originalText = searchButton.textContent;
    searchButton.disabled = true;
    searchButton.textContent = '🔍 Searching...';
    
    // Show appropriate loading message
    if (targetPage && currentSearchState.queryId) {
        // This is pagination within existing results
        showResults(`Loading page ${targetPage}...`, 'loading');
    } else {
        // This is a new search
        showResults('Searching...', 'loading');
    }
    
    // Show active filters visual feedback
    showActiveFilters(filters);
    
    try {
        // Determine if this is a new search or pagination
        const isNewSearch = !targetPage || 
                           query !== currentSearchState.query || 
                           JSON.stringify(filters) !== JSON.stringify(currentSearchState.filters) ||
                           maxResults !== currentSearchState.pageSize;
        
        let cursor = null;
        if (!isNewSearch && currentSearchState.queryId && targetPage) {
            // Generate cursor for pagination
            const cursorPayload = {
                query_id: currentSearchState.queryId,
                page: targetPage
            };
            cursor = btoa(JSON.stringify(cursorPayload));
        }
        
        // Build request payload with cursor-based pagination
        const requestPayload = {
            query: query,
            parameters: {
                max_results: maxResults,
                cursor: cursor
            }
        };
        
        // Add filters if any are selected
        if (Object.keys(filters).length > 0) {
            requestPayload.filters = filters;
        }
        
        console.log('Search payload:', requestPayload);
        
        const response = await fetch(`${apiEndpoint}/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentToken}`
            },
            body: JSON.stringify(requestPayload)
        });
        
        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`Search failed: ${response.status} - ${errorData}`);
        }
        
        const data = await response.json();
        
        console.log('API Response data:', data);
        console.log('Pagination from response:', data.results?.pagination);
        
        // Update search state
        currentSearchState = {
            query: query,
            filters: filters,
            pageSize: maxResults,
            currentPage: data.results?.pagination?.current_page || 1,
            totalPages: data.results?.pagination?.total_pages || 1,
            queryId: data.query_id || null,
            lastCursor: data.results?.pagination?.next_cursor || null
        };
        
        console.log('Updated currentSearchState:', currentSearchState);
        
        displaySearchResults(data, filters);
        
        // Update pagination if present
        if (data.results?.pagination) {
            updatePagination(data.results.pagination);
        }
        
        // Update URL without page parameter (cursor-based now)
        const url = new URL(window.location);
        url.searchParams.delete('page');
        window.history.replaceState({}, '', url);
        
    } catch (error) {
        console.error('Search error:', error);
        showResults(`Search failed: ${error.message}`, 'error');
    } finally {
        searchButton.disabled = false;
        searchButton.textContent = originalText;
    }
}

function collectFilterValues() {
    const filters = {};
    
    // Solution Category
    const solutionCategory = document.getElementById('solutionCategoryFilter').value;
    if (solutionCategory) {
        filters.solution_category = [solutionCategory];
    }
    
    // Solution Type
    const solutionType = document.getElementById('solutionTypeFilter').value;
    if (solutionType) {
        filters.solution_type = [solutionType];
    }
    
    // Location: Region OR Countries (mutually exclusive)
    const region = document.getElementById('regionFilter').value;
    const countrySelect = document.getElementById('countryFilter');
    const selectedCountries = Array.from(countrySelect.selectedOptions).map(option => option.value);
    
    if (region) {
        // Use regional filter
        filters.region = [region];
    } else if (selectedCountries.length > 0) {
        // Use country list filter
        filters.countries = selectedCountries;
    }
    
    return filters;
}

function showActiveFilters(filters) {
    // Create or update active filters display
    let activeFiltersDiv = document.getElementById('activeFilters');
    if (!activeFiltersDiv) {
        activeFiltersDiv = document.createElement('div');
        activeFiltersDiv.id = 'activeFilters';
        activeFiltersDiv.className = 'active-filters';
        document.querySelector('.search-section').appendChild(activeFiltersDiv);
    }
    
    if (Object.keys(filters).length === 0) {
        activeFiltersDiv.innerHTML = '';
        return;
    }
    
    let html = '<div class="active-filters-header">Active Filters:</div>';
    
    Object.entries(filters).forEach(([key, values]) => {
        const displayName = getFilterDisplayName(key);
        const valueList = Array.isArray(values) ? values.join(', ') : values;
        html += `<span class="filter-tag">
            ${displayName}: ${valueList}
            <button class="remove-filter" onclick="clearFilter('${key}')">&times;</button>
        </span>`;
    });
    
    html += `<button class="clear-all-filters" onclick="clearAllFilters()">Clear All</button>`;
    
    activeFiltersDiv.innerHTML = html;
}

function getFilterDisplayName(key) {
    const displayNames = {
        'solution_category': 'Category',
        'solution_type': 'Solution Type',
        'region': 'Region',
        'countries': 'Countries'
    };
    return displayNames[key] || key;
}

function clearFilter(filterKey) {
    // Clear the specific filter and re-run search
    const filterMap = {
        'solution_category': 'solutionCategoryFilter',
        'solution_type': 'solutionTypeFilter',
        'region': 'regionFilter',
        'countries': 'countryFilter'
    };
    
    const elementId = filterMap[filterKey];
    if (elementId) {
        const element = document.getElementById(elementId);
        if (element.multiple) {
            // Clear all selections for multi-select
            Array.from(element.options).forEach(option => option.selected = false);
        } else {
            element.value = '';
        }
        
        // Re-run search
        performSearch();
    }
}

function clearAllFilters() {
    // Clear all filter dropdowns
    document.getElementById('solutionCategoryFilter').value = '';
    document.getElementById('solutionTypeFilter').value = '';
    document.getElementById('regionFilter').value = '';
    
    // Clear multi-select countries
    const countrySelect = document.getElementById('countryFilter');
    Array.from(countrySelect.options).forEach(option => option.selected = false);
    
    // Re-run search
    performSearch();
}

function displaySearchResults(data, appliedFilters = {}) {
    const container = document.getElementById('resultsContainer');
    
    console.log('Search results data:', data); // Debug log
    
    if (!data.results || !data.results.solutions || data.results.solutions.length === 0) {
        let message = 'No solutions found for your search query';
        if (Object.keys(appliedFilters).length > 0) {
            message += ' with the selected filters';
        }
        showResults(message, 'no-results');
        return;
    }
    
    // Log first result to see structure
    console.log('First result structure:', data.results.solutions[0]);
    
    let html = '';
    
    // Add results summary with total count
    const totalResults = data.results.pagination ? data.results.pagination.total_results : data.results.solutions.length;
    const currentPage = data.results.pagination ? data.results.pagination.current_page : 1;
    const pageSize = data.results.pagination ? data.results.pagination.page_size : data.results.solutions.length;
    
    html += `<div class="results-summary">
        Found ${totalResults} solutions${Object.keys(appliedFilters).length > 0 ? ' matching your filters' : ''}
    </div>`;
    
    // If filters are applied, show as single group. Otherwise, group by content.
    if (Object.keys(appliedFilters).length > 0) {
        // Calculate result range for display
        const startResult = ((currentPage - 1) * pageSize) + 1;
        const endResult = Math.min(startResult + data.results.solutions.length - 1, totalResults);
        
        // Show filtered results as single group
        html += `<div class="risk-type-section">
            <h3 class="risk-type-header">Results ${startResult} - ${endResult}</h3>`;
        
        data.results.solutions.forEach((result, index) => {
            // Calculate result number based on page and position
            const resultNumber = ((currentPage - 1) * pageSize) + index + 1;
            console.log(`Creating card ${index} with result number ${resultNumber}`); // Debug
            html += createSolutionCard(result, index, resultNumber);
        });
        
        html += '</div>';
    } else {
        // Calculate result range for unfiltered searches
        const startResult = ((currentPage - 1) * pageSize) + 1;
        const endResult = Math.min(startResult + data.results.solutions.length - 1, totalResults);
        
        // Show all results as single group (no content-based grouping)
        html += `<div class="risk-type-section">
            <h3 class="risk-type-header">Results ${startResult} - ${endResult}</h3>`;
        
        data.results.solutions.forEach((result, index) => {
            const resultNumber = ((currentPage - 1) * pageSize) + index + 1;
            html += createSolutionCard(result, index, resultNumber);
        });
        
        html += '</div>';
    }
    
    container.innerHTML = html;
    
    // Add interactivity to cards
    addCardInteractivity();
    
    // Show pagination if needed
    if (data.results.solutions.length >= 10) {
        document.getElementById('pagination').style.display = 'flex';
    }
}

function groupResultsByContent(results) {
    // Simple grouping by content keywords for demo purposes
    const groups = {
        'Search Results': [] // Default group for all results
    };
    
    results.forEach(result => {
        // Handle different possible content fields - use summary_description from API v2
        const content = (result.summary_description || result.content || result.text || result.description || '').toLowerCase();
        
        if (content.includes('pandemic') || content.includes('health') || content.includes('disease')) {
            if (!groups['Pandemic Solutions']) groups['Pandemic Solutions'] = [];
            groups['Pandemic Solutions'].push(result);
        } else if (content.includes('cyber') || content.includes('security') || content.includes('breach')) {
            if (!groups['Cyber Security']) groups['Cyber Security'] = [];
            groups['Cyber Security'].push(result);
        } else if (content.includes('natural') || content.includes('disaster') || content.includes('catastrophe')) {
            if (!groups['Natural Catastrophe']) groups['Natural Catastrophe'] = [];
            groups['Natural Catastrophe'].push(result);
        } else {
            groups['Search Results'].push(result);
        }
    });
    
    // Remove empty groups
    Object.keys(groups).forEach(key => {
        if (groups[key].length === 0) {
            delete groups[key];
        }
    });
    
    return groups;
}

function createSolutionCard(result, index, resultNumber = null) {
    console.log(`createSolutionCard called with resultNumber: ${resultNumber}`); // Debug
    
    // Use the correct field names from API v2 response
    const content = result.summary_description || result.content || result.text || result.description || 'No content available';
    const documentId = result.document_id || result.doc_id || result.id || `result-${index}`;
    const chunkId = result.chunk_id || result.id || `chunk-${index}`;
    const score = result.relevance_score || result.score || 0;
    
    // Use the solution_name from API response instead of extracting
    const solutionName = result.solution_name || result.title || extractSolutionName(content) || `Solution ${index + 1}`;
    const fullDescription = content; // Use full assembled description from S3 chunks
    const shortDescription = content.substring(0, 200) + (content.length > 200 ? '...' : '');
    const relevanceScore = Math.round(score * 100);
    
    // Use API response fields for metadata
    const riskType = (result.risk_types_addressed && result.risk_types_addressed[0]) || extractRiskType(content);
    const country = (result.country_regions_covered && result.country_regions_covered[0]) || extractCountry(content) || 'Multiple Countries';
    const region = 'ASEAN'; // Default for demo
    
    return `
        <div class="solution-card" data-result-id="${chunkId}">
            <div class="solution-header">
                <div class="solution-title-section">
                    ${resultNumber ? `<div class="result-number">#${resultNumber}</div>` : '<div class="result-number">NO_NUM</div>'}
                    <h3 class="solution-name">${solutionName}</h3>
                    <div class="solution-meta">
                        <span class="meta-item"><span class="meta-label">Risk Type:</span> ${riskType}</span>
                        <span class="meta-item"><span class="meta-label">Document ID:</span> ${documentId}</span>
                    </div>
                </div>
                <div class="solution-actions">
                    <button class="action-btn bookmark-btn" onclick="toggleBookmark(this)">📌 Bookmark</button>
                    <button class="action-btn export-btn" onclick="exportSolution('${documentId}')">📄 Export PDF</button>
                </div>
            </div>
            
            <div class="solution-summary">
                <div class="location-info">
                    <span class="location-item"><span class="meta-label">Region:</span> ${region}</span>
                    <span class="location-item"><span class="meta-label">Country:</span> ${country}</span>
                    <span class="location-item"><span class="meta-label">Solution Type:</span> ${(result.solution_types && result.solution_types[0]) || 'Prevention'}</span>
                    <span class="relevance-score">${relevanceScore}%</span>
                </div>
                <div class="solution-preview">
                    <p>${shortDescription}</p>
                </div>
            </div>
            
            <div class="solution-details" style="display: none;">
                <div class="solution-description">
                    <h4>Full Solution Description:</h4>
                    <p>${fullDescription}</p>
                </div>
                
                <div class="solution-categories">
                    <div class="category-section">
                        <h4>Risk Types Addressed:</h4>
                        <ul>
                            ${(result.risk_types_addressed || []).map(risk => `<li>${risk}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="category-section">
                        <h4>Solution Types:</h4>
                        <ul>
                            ${(result.solution_types || []).map(type => `<li>${type}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                
                <div style="margin-top: 16px; text-align: right;">
                    <a href="#" class="text-primary" style="font-size: 14px;">Click here for more details ▶</a>
                </div>
            </div>
            
            <button class="expand-btn" onclick="toggleSolutionDetails(this)">▼</button>
        </div>
    `;
}

// Utility functions for extracting information from content
function extractSolutionName(content) {
    if (!content) return null;
    
    // Try to extract a meaningful title from the content
    const sentences = content.split('.').filter(s => s.trim().length > 10);
    if (sentences.length > 0) {
        let title = sentences[0].trim();
        if (title.length > 80) {
            title = title.substring(0, 77) + '...';
        }
        return title;
    }
    return null;
}

function extractRiskType(content) {
    if (!content) return 'General Risk';
    
    const lowerContent = content.toLowerCase();
    if (lowerContent.includes('pandemic') || lowerContent.includes('health') || lowerContent.includes('disease')) {
        return 'Pandemic';
    } else if (lowerContent.includes('cyber') || lowerContent.includes('security')) {
        return 'Cyber Security';
    } else if (lowerContent.includes('natural') || lowerContent.includes('disaster') || lowerContent.includes('catastrophe')) {
        return 'Natural Catastrophe';
    } else if (lowerContent.includes('mortality') || lowerContent.includes('death')) {
        return 'Mortality';
    } else if (lowerContent.includes('retirement') || lowerContent.includes('pension')) {
        return 'Retirement';
    }
    return 'General Risk';
}

function extractCountry(content) {
    if (!content) return null;
    
    const countries = ['Singapore', 'Thailand', 'Malaysia', 'Indonesia', 'Philippines', 'Vietnam', 'Cambodia', 'Laos', 'Myanmar', 'Brunei', 'China', 'Japan', 'South Korea', 'Australia', 'New Zealand'];
    const lowerContent = content.toLowerCase();
    
    for (const country of countries) {
        if (lowerContent.includes(country.toLowerCase())) {
            return country;
        }
    }
    return null;
}

// Interactive Functions
function addCardInteractivity() {
    // Expand/collapse functionality is handled by onclick in HTML
    // Add any additional interactivity here
}

function toggleSolutionDetails(button) {
    const card = button.closest('.solution-card');
    const details = card.querySelector('.solution-details');
    
    if (details.style.display === 'none') {
        details.style.display = 'block';
        button.textContent = '▲';
        button.style.bottom = '16px'; // Adjust position when expanded
    } else {
        details.style.display = 'none';
        button.textContent = '▼';
        button.style.bottom = '16px';
    }
}

function toggleBookmark(button) {
    if (button.classList.contains('bookmarked')) {
        button.classList.remove('bookmarked');
        button.textContent = '📌 Bookmark';
    } else {
        button.classList.add('bookmarked');
        button.textContent = '📌 Bookmarked';
    }
}

function exportSolution(documentId) {
    // Placeholder for export functionality
    alert(`Export functionality for document ${documentId} would be implemented here`);
}

// Filter and Sort Functions
function handleFilterChange(event) {
    const filter = event.target;
    const filterType = filter.id;
    const value = filter.value;
    
    // Visual feedback
    filter.style.borderColor = 'var(--light-blue)';
    setTimeout(() => {
        filter.style.borderColor = '';
    }, 1000);
    
    // Auto-search if there's a query and user is authenticated
    const query = document.getElementById('searchQuery').value.trim();
    if (query && currentToken && Date.now() < tokenExpiry) {
        // Reset to page 1 when filters change
        const url = new URL(window.location);
        url.searchParams.delete('page');
        window.history.replaceState({}, '', url);
        
        // Debounce the search to avoid too many API calls
        clearTimeout(window.filterSearchTimeout);
        window.filterSearchTimeout = setTimeout(() => {
            performNewSearch();
        }, 500);
    }
    
    console.log(`Filter changed: ${filterType} = ${value}`);
}

function updatePagination(pagination) {
    const paginationDiv = document.getElementById('pagination');
    const pageNumbersDiv = document.getElementById('pageNumbers');
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    
    if (pagination.total_pages <= 1) {
        paginationDiv.style.display = 'none';
        return;
    }
    
    // Show pagination
    paginationDiv.style.display = 'flex';
    
    // Remove disabled attribute and any title attributes that might cause tooltips
    prevBtn.removeAttribute('disabled');
    prevBtn.removeAttribute('title');
    nextBtn.removeAttribute('disabled');
    nextBtn.removeAttribute('title');
    
    // Override the changePage function to work with our pagination
    window.changePage = function(direction) {
        console.log('changePage called with direction:', direction);
        console.log('currentSearchState:', currentSearchState);
        console.log('pagination:', pagination);
        
        const newPage = currentSearchState.currentPage + direction;
        console.log('newPage calculated:', newPage);
        
        // Simplified bounds checking
        if (direction === -1 && currentSearchState.currentPage <= 1) {
            console.log('Already on first page, ignoring previous');
            return;
        }
        if (direction === 1 && currentSearchState.currentPage >= currentSearchState.totalPages) {
            console.log('Already on last page, ignoring next');
            return;
        }
        
        console.log('Calling performSearch with newPage:', newPage);
        performSearch(newPage);
    };
    
    // Visual feedback using CSS classes and styles (no tooltips)
    if (!pagination.has_previous) {
        prevBtn.classList.add('pagination-disabled');
        prevBtn.style.opacity = '0.5';
        prevBtn.style.cursor = 'default';
        prevBtn.style.pointerEvents = 'auto';
    } else {
        prevBtn.classList.remove('pagination-disabled');
        prevBtn.style.opacity = '1';
        prevBtn.style.cursor = 'pointer';
        prevBtn.style.pointerEvents = 'auto';
    }
    
    if (!pagination.has_next) {
        nextBtn.classList.add('pagination-disabled');
        nextBtn.style.opacity = '0.5';
        nextBtn.style.cursor = 'default';
        nextBtn.style.pointerEvents = 'auto';
    } else {
        nextBtn.classList.remove('pagination-disabled');
        nextBtn.style.opacity = '1';
        nextBtn.style.cursor = 'pointer';
        nextBtn.style.pointerEvents = 'auto';
    }
    
    // Generate page numbers
    pageNumbersDiv.innerHTML = '';
    const currentPage = pagination.current_page;
    const totalPages = pagination.total_pages;
    
    // Show page numbers (max 7: 1 ... 3 4 [5] 6 7 ... 10)
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);
    
    // Add first page if not in range
    if (startPage > 1) {
        addPageButton(1, currentPage);
        if (startPage > 2) {
            pageNumbersDiv.appendChild(createEllipsis());
        }
    }
    
    // Add page range
    for (let i = startPage; i <= endPage; i++) {
        addPageButton(i, currentPage);
    }
    
    // Add last page if not in range
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            pageNumbersDiv.appendChild(createEllipsis());
        }
        addPageButton(totalPages, currentPage);
    }
}

function addPageButton(pageNum, currentPage) {
    const pageNumbersDiv = document.getElementById('pageNumbers');
    const btn = document.createElement('button');
    btn.className = `page-btn ${pageNum === currentPage ? 'active' : ''}`;
    btn.textContent = pageNum;
    btn.onclick = () => goToPage(pageNum);
    pageNumbersDiv.appendChild(btn);
}

function createEllipsis() {
    const span = document.createElement('span');
    span.className = 'page-ellipsis';
    span.textContent = '...';
    return span;
}

function changePage(direction) {
    console.log('changePage called with direction:', direction);
    console.log('currentSearchState:', currentSearchState);
    
    const newPage = currentSearchState.currentPage + direction;
    console.log('newPage calculated:', newPage);
    console.log('totalPages:', currentSearchState.totalPages);
    
    if (newPage >= 1 && newPage <= currentSearchState.totalPages) {
        console.log('Calling performSearch with newPage:', newPage);
        performSearch(newPage);
    } else {
        console.log('Page out of bounds, not performing search');
    }
}

function goToPage(page) {
    if (page >= 1 && page <= currentSearchState.totalPages) {
        performSearch(page);
    }
}

function handleSortClick(event) {
    const button = event.target;
    
    // Remove active class from all sort buttons
    document.querySelectorAll('.sort-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Add active class to clicked button
    button.classList.add('active');
    
    // In a real implementation, this would sort the results
    console.log(`Sort by: ${button.textContent}`);
}

function toggleBookmarkFolder(event) {
    const header = event.currentTarget;
    const folder = header.closest('.bookmark-folder');
    const content = folder.querySelector('.folder-content');
    const toggle = header.querySelector('.folder-toggle');
    
    if (content) {
        if (content.style.display === 'none' || !content.style.display) {
            content.style.display = 'block';
            toggle.textContent = '▲';
        } else {
            content.style.display = 'none';
            toggle.textContent = '▼';
        }
    }
}

// Utility Functions
function showResults(message, type) {
    const container = document.getElementById('resultsContainer');
    const className = type === 'error' ? 'no-results' : 'loading-message';
    container.innerHTML = `<div class="${className}">${message}</div>`;
}

// Make authenticate function globally available
window.authenticate = authenticate;
