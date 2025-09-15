// BMA Social Campaign Manager JavaScript

// API Base URL - will use current domain in production
const API_BASE = window.location.origin;

let currentCampaignId = null;

// Load statistics on page load
document.addEventListener('DOMContentLoaded', function() {
    loadStatistics();
    loadRecentCampaigns();
});

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/api/campaigns/statistics`);
        const stats = await response.json();

        // Update stats display
        document.getElementById('total-customers').textContent =
            stats.customer_statistics?.total_customers || 0;
        document.getElementById('total-zones').textContent =
            stats.customer_statistics?.total_zones || 0;
        document.getElementById('expiring-30').textContent =
            stats.customer_statistics?.expiring_30_days || 0;
        document.getElementById('active-campaigns').textContent =
            stats.active_campaigns || 0;
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Create quick campaign with natural language
async function createQuickCampaign() {
    const humanRequest = document.getElementById('human-request').value;

    if (!humanRequest.trim()) {
        alert('Please describe what campaign you want to create');
        return;
    }

    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/api/campaigns/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                human_request: humanRequest
            })
        });

        const result = await response.json();
        console.log('Campaign API response:', result);  // Debug log

        if (response.ok && result.success) {
            const campaign = result.campaign;  // Extract campaign from result
            currentCampaignId = campaign.id;

            // Check if campaign has target customers
            if (campaign.statistics && campaign.statistics.total_customers === 0) {
                showLoading(false);
                alert('No customers found matching your criteria. Try "all hotels" or "Hilton" or check the customer database.');
                resetForm();
                return;
            }
            showCampaignPreview(campaign);
            showLoading(false);
        } else {
            showLoading(false);
            alert('Error creating campaign: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        showLoading(false);
        alert('Error creating campaign: ' + error.message);
    }
}

// Create advanced campaign with filters
async function createAdvancedCampaign() {
    const campaignType = document.getElementById('campaign-type').value;
    const filterBrand = document.getElementById('filter-brand').value;
    const filterBusiness = document.getElementById('filter-business').value;
    const filterExpiry = document.getElementById('filter-expiry').value;
    const context = document.getElementById('campaign-context').value;

    // Build filters object
    const filters = {};
    if (filterBrand) filters.brand = filterBrand;
    if (filterBusiness) filters.business_type = filterBusiness;
    if (filterExpiry) filters.contract_expiry = { days: parseInt(filterExpiry) };

    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/api/campaigns/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: campaignType,
                filters: filters,
                context: context || undefined
            })
        });

        const result = await response.json();

        if (response.ok && result.success) {
            const campaign = result.campaign;  // Extract campaign from result
            currentCampaignId = campaign.id;
            showCampaignPreview(campaign);
            showLoading(false);
        } else {
            showLoading(false);
            alert('Error creating campaign: ' + (campaign.error || 'Unknown error'));
        }
    } catch (error) {
        showLoading(false);
        alert('Error creating campaign: ' + error.message);
    }
}

// Show campaign preview
async function showCampaignPreview(campaign) {
    // Hide creation forms
    document.querySelectorAll('.card').forEach(card => {
        if (!card.id) card.style.display = 'none';
    });

    // Get preview data
    const response = await fetch(`${API_BASE}/api/campaigns/${campaign.id}/preview`);
    const preview = await response.json();
    console.log('Campaign preview:', preview);  // Debug log

    // Store campaign data for editing
    window.currentCampaignData = preview;

    // Build preview HTML with editable messages
    let previewHTML = `
        <div class="campaign-summary">
            <h3>Campaign: ${preview.plan?.campaign_name || 'Campaign'}</h3>
            <p><strong>Type:</strong> ${preview.type}</p>
            <p><strong>Goal:</strong> ${preview.plan?.campaign_goal || 'N/A'}</p>
            <p><strong>Target Audience:</strong> ${preview.total_customers} customers (${preview.statistics?.total_zones || 0} zones)</p>
        </div>

        <h4 style="margin-top: 20px;">📝 Edit Messages Before Sending:</h4>
        <p class="help-text">Review and edit the messages below. Your changes will be applied to all customers.</p>
    `;

    // Add editable message templates
    if (preview.sample_messages && preview.sample_messages.length > 0) {
        const sample = preview.sample_messages[0];
        previewHTML += `
            <div class="edit-section">
                <h5>WhatsApp/Line Message:</h5>
                <textarea id="edit-whatsapp" class="message-editor">${sample.whatsapp}</textarea>

                <h5 style="margin-top: 15px;">Email Subject:</h5>
                <input type="text" id="edit-email-subject" value="${sample.email_subject}" />

                <h5 style="margin-top: 15px;">Email Body:</h5>
                <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;">
                    <strong>Preview:</strong>
                    <div style="margin-top: 8px; padding: 10px; background: white; border-radius: 3px;">
                        ${sample.email_body || sample.whatsapp || 'Email body content'}
                    </div>
                </div>
                <textarea id="edit-email-body" class="message-editor">${sample.email_body || sample.whatsapp || 'Email body content'}</textarea>
            </div>

            <h4 style="margin-top: 20px;">👥 This will be sent to:</h4>
        `;

        // Show all target customers with contact selection
        preview.sample_messages.forEach((sample, customerIndex) => {
            // Build contact checkboxes HTML directly
            let contactCheckboxes = '';
            const contacts = sample.contacts || [sample.contact];

            if (Array.isArray(contacts)) {
                contacts.forEach((contact, idx) => {
                    // Parse contact string if it's in format "Name (Role)"
                    let name = contact;
                    let role = '';
                    if (typeof contact === 'string' && contact.includes('(')) {
                        const match = contact.match(/(.+)\s*\((.+)\)/);
                        if (match) {
                            name = match[1].trim();
                            role = match[2].trim();
                        }
                    }
                    contactCheckboxes += `
                        <label style="display: block; margin: 5px 0; cursor: pointer;">
                            <input type="checkbox" checked
                                   data-customer="${customerIndex}"
                                   data-contact="${idx}"
                                   style="margin-right: 8px;">
                            ${name} ${role ? `(${role})` : ''}
                        </label>
                    `;
                });
            }

            previewHTML += `
                <div class="preview-item">
                    <h4>${sample.customer}</h4>
                    <p><strong>Brand:</strong> ${sample.brand || 'Independent'}</p>
                    <p><strong>Zones:</strong> ${sample.zones.join(', ')}</p>
                    <p><strong>📧 Selected Recipients:</strong></p>
                    <div style="margin-left: 20px; margin-bottom: 10px;">
                        ${contactCheckboxes || '<p>No contacts available</p>'}
                    </div>
                    <p><strong>Channels:</strong> ${sample.channels && sample.channels.length > 0 ? sample.channels.join(', ') : 'No channels'}</p>
                </div>
            `;
        });
    } else {
        previewHTML += '<p>No customers found matching your criteria.</p>';
    }

    // Show estimated sends
    previewHTML += `
        <div style="margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 8px;">
            <h4>📊 Campaign Summary:</h4>
            <p>Total Customers: ${preview.total_customers || 0}</p>
            <p>WhatsApp Messages: ${preview.estimated_sends?.whatsapp || 0}</p>
            <p>Email Messages: ${preview.estimated_sends?.email || 0}</p>
            <p>Line Messages: ${preview.estimated_sends?.line || 0}</p>
        </div>
    `;

    document.getElementById('preview-content').innerHTML = previewHTML;
    document.getElementById('campaign-preview').style.display = 'block';
}

// Populate contact checkboxes for each customer
function populateContactCheckboxes(preview) {
    if (!preview.sample_messages) return;

    preview.sample_messages.forEach((sample, customerIndex) => {
        const container = document.getElementById(`contacts-${customerIndex}`);
        if (!container) return;

        // For now, use the contacts information from the sample
        // In future, we'd get all available contacts from the backend
        const selectedContacts = sample.contacts || [sample.contact];

        let checkboxHTML = '';

        if (Array.isArray(selectedContacts)) {
            selectedContacts.forEach((contact, contactIndex) => {
                // Parse contact string if it's in format "Name (Role)"
                let contactName = contact;
                let contactRole = '';
                if (contact.includes('(') && contact.includes(')')) {
                    const parts = contact.match(/(.+)\s*\((.+)\)/);
                    if (parts) {
                        contactName = parts[1].trim();
                        contactRole = parts[2].trim();
                    }
                }

                checkboxHTML += `
                    <label class="contact-checkbox">
                        <input type="checkbox"
                               checked
                               data-customer="${customerIndex}"
                               data-contact="${contactIndex}"
                               data-contact-name="${contactName}"
                               data-contact-role="${contactRole}">
                        <span class="contact-info">
                            <strong>${contactName}</strong>
                            ${contactRole ? `<br><small>${contactRole}</small>` : ''}
                        </span>
                    </label>
                `;
            });
        } else {
            // Handle single contact string
            checkboxHTML = `
                <label class="contact-checkbox">
                    <input type="checkbox"
                           checked
                           data-customer="${customerIndex}"
                           data-contact="0"
                           data-contact-name="${selectedContacts}"
                           data-contact-role="">
                    <span class="contact-info">
                        <strong>${selectedContacts}</strong>
                    </span>
                </label>
            `;
        }

        container.innerHTML = checkboxHTML;
    });
}

// Get selected contacts from checkboxes
function getSelectedContacts() {
    const selectedContacts = {};
    const checkboxes = document.querySelectorAll('.contact-checkbox input[type="checkbox"]:checked');

    checkboxes.forEach(checkbox => {
        const customerIndex = checkbox.dataset.customer;
        const contactName = checkbox.dataset.contactName;
        const contactRole = checkbox.dataset.contactRole;

        if (!selectedContacts[customerIndex]) {
            selectedContacts[customerIndex] = [];
        }

        selectedContacts[customerIndex].push({
            name: contactName,
            role: contactRole || ''
        });
    });

    return selectedContacts;
}

// Send campaign
async function sendCampaign(testMode) {
    if (!currentCampaignId) {
        alert('No campaign selected');
        return;
    }

    // Get selected contacts
    const selectedContacts = [];
    const checkboxes = document.querySelectorAll('input[type="checkbox"][data-customer]');
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            selectedContacts.push({
                customer: checkbox.getAttribute('data-customer'),
                contact: checkbox.getAttribute('data-contact')
            });
        }
    });

    // Get edited messages
    const editedWhatsApp = document.getElementById('edit-whatsapp')?.value;
    const editedEmailSubject = document.getElementById('edit-email-subject')?.value;
    const editedEmailBody = document.getElementById('edit-email-body')?.value;

    const confirmMessage = testMode
        ? 'Send test campaign to YOUR personal contacts?\n\nWhatsApp: +66856644142\nEmail: norbert@bmasiamusic.com\n\n(Will NOT send to actual customers)'
        : `Send campaign to ALL ${window.currentCampaignData?.total_customers || 0} customers? This cannot be undone!`;

    if (!confirm(confirmMessage)) {
        return;
    }

    showLoading(true);

    try {
        const requestBody = {
            channels: ['whatsapp', 'email'],
            test_mode: testMode
        };

        // Include edited messages if they exist
        if (editedWhatsApp || editedEmailSubject || editedEmailBody) {
            requestBody.edited_messages = {
                whatsapp: editedWhatsApp,
                email_subject: editedEmailSubject,
                email_body: editedEmailBody
            };
        }

        // Include selected contacts if any were manually selected/deselected
        if (selectedContacts && Object.keys(selectedContacts).length > 0) {
            requestBody.selected_contacts = selectedContacts;
        }

        const response = await fetch(`${API_BASE}/api/campaigns/${currentCampaignId}/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });

        const result = await response.json();

        if (response.ok) {
            showResults(result);
            showLoading(false);
        } else {
            showLoading(false);
            alert('Error sending campaign: ' + (result.error || 'Unknown error'));
        }
    } catch (error) {
        showLoading(false);
        alert('Error sending campaign: ' + error.message);
    }
}

// Show results
function showResults(result) {
    // Hide preview
    document.getElementById('campaign-preview').style.display = 'none';

    // Build results HTML
    let resultsHTML = `
        <div class="result-summary">
            <h3>Campaign Sent Successfully!</h3>
            <p><strong>Campaign ID:</strong> ${result.campaign_id}</p>
            <p><strong>Channels Used:</strong> ${result.channels && result.channels.length > 0 ? result.channels.join(', ') : 'No channels'}</p>
        </div>

        <h4 style="margin-top: 20px;">Results by Customer:</h4>
    `;

    // Add customer results
    if (result.results_by_customer && result.results_by_customer.length > 0) {
        result.results_by_customer.forEach(customer => {
            const totalSent = Object.values(customer.sent || {}).reduce((a, b) => a + b, 0);
            const totalFailed = Object.values(customer.failed || {}).reduce((a, b) => a + b, 0);

            resultsHTML += `
                <div class="result-item">
                    <div>
                        <strong>${customer.customer}</strong><br>
                        Channels: ${customer.channels_used.join(', ')}
                    </div>
                    <div>
                        <span class="result-success">Sent: ${totalSent}</span> |
                        <span class="result-failed">Failed: ${totalFailed}</span>
                    </div>
                </div>
            `;
        });
    }

    // Add AI report if available
    if (result.ai_report) {
        resultsHTML += `
            <div style="margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 8px;">
                <h4>AI Report:</h4>
                <pre style="white-space: pre-wrap;">${result.ai_report}</pre>
            </div>
        `;
    }

    document.getElementById('results-content').innerHTML = resultsHTML;
    document.getElementById('campaign-results').style.display = 'block';

    // Reload statistics
    loadStatistics();
    loadRecentCampaigns();
}

// Cancel campaign
function cancelCampaign() {
    if (confirm('Cancel this campaign?')) {
        resetForm();
    }
}

// Reset form
function resetForm() {
    // Show all cards
    document.querySelectorAll('.card').forEach(card => {
        if (!card.id || card.id === 'recent-campaigns') {
            card.style.display = 'block';
        }
    });

    // Hide preview and results
    document.getElementById('campaign-preview').style.display = 'none';
    document.getElementById('campaign-results').style.display = 'none';

    // Clear form fields
    document.getElementById('human-request').value = '';
    document.getElementById('campaign-type').selectedIndex = 0;
    document.getElementById('filter-brand').selectedIndex = 0;
    document.getElementById('filter-business').selectedIndex = 0;
    document.getElementById('filter-expiry').selectedIndex = 0;
    document.getElementById('campaign-context').value = '';

    currentCampaignId = null;
}

// Load recent campaigns
async function loadRecentCampaigns() {
    try {
        const response = await fetch(`${API_BASE}/api/campaigns/statistics`);
        const stats = await response.json();

        // For now, just show campaign counts by status
        let html = '';

        if (stats.campaigns_by_status) {
            for (const [status, count] of Object.entries(stats.campaigns_by_status)) {
                const statusClass = `status-${status}`;
                html += `
                    <div class="campaign-list-item">
                        <div class="campaign-info">
                            <h4>${status.charAt(0).toUpperCase() + status.slice(1)} Campaigns</h4>
                            <p>${count} campaign(s)</p>
                        </div>
                        <span class="campaign-status ${statusClass}">${status}</span>
                    </div>
                `;
            }
        }

        if (!html) {
            html = '<p class="help-text">No campaigns yet. Create your first campaign above!</p>';
        }

        document.getElementById('recent-campaigns').innerHTML = html;
    } catch (error) {
        console.error('Error loading recent campaigns:', error);
        document.getElementById('recent-campaigns').innerHTML =
            '<p class="help-text">Error loading campaigns</p>';
    }
}

// Show/hide loading overlay
function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}