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
        const activeCampaignsCount = stats.active_campaigns || 0;
        const activeCampaignsEl = document.getElementById('active-campaigns');
        if (activeCampaignsEl) {
            activeCampaignsEl.textContent = activeCampaignsCount;
            // Make clickable if there are campaigns
            if (activeCampaignsCount > 0) {
                activeCampaignsEl.style.cursor = 'pointer';
                activeCampaignsEl.style.textDecoration = 'underline';
                activeCampaignsEl.onclick = () => showCampaignsList();
            }
        }
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

// Removed createAdvancedCampaign - using AI Quick Creator only

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
                <h5>Email Subject:</h5>
                <input type="text" id="edit-email-subject" value="${sample.email_subject}" />

                <h5 style="margin-top: 15px;">Email Body:</h5>
                <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; background: #f9f9f9;">
                    <strong>Preview:</strong>
                    <div style="margin-top: 8px; padding: 10px; background: white; border-radius: 3px;">
                        ${sample.email_body || sample.whatsapp || 'Email body content'}
                    </div>
                </div>
                <textarea id="edit-email-body" class="message-editor">${sample.email_body || 'Email body content'}</textarea>
            </div>

            <h4 style="margin-top: 20px;">👥 This will be sent to:</h4>
        `;

        // Show all target customers with contact selection
        preview.sample_messages.forEach((sample, customerIndex) => {
            // Build contact checkboxes HTML directly
            let contactCheckboxes = '';

            // Get contacts array, handling various data structures
            let contacts = [];
            if (sample.contacts && Array.isArray(sample.contacts) && sample.contacts.length > 0) {
                contacts = sample.contacts.filter(c => c && c.trim() !== ''); // Filter out empty contacts
            } else if (sample.contact && sample.contact.trim() !== '') {
                contacts = [sample.contact];
            }

            // Debug logging (can be removed in production)
            console.log(`Processing customer: ${sample.customer}`);
            console.log('Contacts data:', { contacts: sample.contacts, contact: sample.contact });

            // Generate checkbox HTML for each contact
            if (contacts.length > 0) {
                contacts.forEach((contact, idx) => {
                    // Skip empty or null contacts
                    if (!contact || typeof contact !== 'string' || contact.trim() === '') {
                        return;
                    }

                    // Parse contact string if it's in format "Name (Role)"
                    let name = contact.trim();
                    let role = '';
                    if (contact.includes('(') && contact.includes(')')) {
                        const match = contact.match(/(.+)\s*\((.+)\)/);
                        if (match) {
                            name = match[1].trim();
                            role = match[2].trim();
                        }
                    }

                    // Generate checkbox HTML for this contact with inline styles for visibility
                    contactCheckboxes += `
                        <label class="contact-checkbox" style="display: flex; align-items: flex-start; padding: 8px 12px; background: white; border: 1px solid #ddd; border-radius: 6px; margin-bottom: 8px; cursor: pointer;">
                            <input type="checkbox"
                                   checked
                                   style="margin-right: 10px; margin-top: 2px; width: 18px; height: 18px; cursor: pointer;"
                                   data-customer="${customerIndex}"
                                   data-contact="${idx}"
                                   data-contact-name="${name}"
                                   data-contact-role="${role}"
                                   onchange="console.log('Checkbox changed:', this.checked, '${name}')">
                            <span class="contact-info" style="flex: 1; line-height: 1.4;">
                                <strong style="color: #333; font-weight: 600;">${name}</strong>
                                ${role ? `<br><small style="color: #666; font-size: 0.85rem;">${role}</small>` : ''}
                            </span>
                        </label>
                    `;
                });
            } else {
                // No valid contacts found - create fallback display
                const contactInfo = sample.contact || (sample.contacts && sample.contacts.length > 0 ? sample.contacts.join(', ') : 'Unknown');
                contactCheckboxes = `<p style="color: #666; font-style: italic;">Debug: Contact data received: "${contactInfo}" - No valid contacts to display checkboxes</p>`;
            }

            // Final safety check - if no checkboxes were generated, create a simple fallback
            if (!contactCheckboxes || contactCheckboxes.trim() === '') {
                console.warn('Fallback mode activated for customer:', sample.customer);
                // Try to create basic checkboxes from whatever data we have
                const fallbackContacts = sample.contacts || [sample.contact] || ['Unknown Contact'];
                contactCheckboxes = '<div style="border: 2px solid orange; padding: 10px; margin: 5px; border-radius: 5px;"><strong>⚠️ FALLBACK MODE:</strong><br>';

                if (Array.isArray(fallbackContacts)) {
                    fallbackContacts.forEach((contact, idx) => {
                        if (contact) {
                            contactCheckboxes += `
                                <label class="contact-checkbox" style="display: flex; align-items: center; margin: 5px 0; padding: 8px; background: #f0f0f0; border-radius: 4px;">
                                    <input type="checkbox" checked style="margin-right: 8px; width: 18px; height: 18px;">
                                    <span><strong>${contact}</strong></span>
                                </label>
                            `;
                        }
                    });
                } else {
                    contactCheckboxes += `
                        <label class="contact-checkbox" style="display: flex; align-items: center; margin: 5px 0; padding: 8px; background: #f0f0f0; border-radius: 4px;">
                            <input type="checkbox" checked style="margin-right: 8px; width: 18px; height: 18px;">
                            <span><strong>${fallbackContacts}</strong></span>
                        </label>
                    `;
                }
                contactCheckboxes += '</div>';
            }

            // Build the recipients HTML with checkboxes and email addresses
            let recipientsHTML = '';
            if (sample.contacts && Array.isArray(sample.contacts)) {
                sample.contacts.forEach((contact, idx) => {
                    // Contacts now include email addresses in format "Name (Role) - email@example.com"
                    recipientsHTML += `
                        <label style="display: block; margin: 5px 0; cursor: pointer; font-size: 14px;">
                            <input type="checkbox" checked
                                   data-customer="${customerIndex}"
                                   data-contact="${idx}"
                                   style="margin-right: 8px;">
                            ${contact}
                        </label>
                    `;
                });
            } else if (sample.contact) {
                recipientsHTML = `
                    <label style="display: block; margin: 5px 0; cursor: pointer; font-size: 14px;">
                        <input type="checkbox" checked
                               data-customer="${customerIndex}"
                               data-contact="0"
                               style="margin-right: 8px;">
                        ${sample.contact}
                    </label>
                `;
            }

            previewHTML += `
                <div class="preview-item">
                    <h4>${sample.customer}</h4>
                    <p><strong>Brand:</strong> ${sample.brand || 'Independent'}</p>
                    <p><strong>Zones:</strong> ${sample.zones.join(', ')}</p>
                    <p><strong>📧 Selected Recipients:</strong></p>
                    <div style="margin-left: 20px;">
                        ${recipientsHTML || '<p>No recipients available</p>'}
                    </div>
                    <p><strong>Channel:</strong> Email</p>
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
            <p>Email Messages: ${preview.estimated_sends?.email || 0}</p>
        </div>
    `;

    document.getElementById('preview-content').innerHTML = previewHTML;
    document.getElementById('campaign-preview').style.display = 'block';

    // Verify checkboxes were rendered
    setTimeout(() => {
        const checkboxes = document.querySelectorAll('.contact-checkbox input[type="checkbox"]');
        console.log(`✅ Rendered ${checkboxes.length} contact checkboxes`);
        if (checkboxes.length === 0) {
            console.error('⚠️ WARNING: No checkboxes found after rendering!');
            console.log('Preview data:', preview);
        } else {
            // Make absolutely sure checkboxes are visible
            checkboxes.forEach(cb => {
                cb.style.display = 'inline-block';
                cb.style.visibility = 'visible';
                cb.style.opacity = '1';
            });
        }
    }, 100);
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
    const allCheckboxes = document.querySelectorAll('.contact-checkbox input[type="checkbox"]');
    const checkedCheckboxes = document.querySelectorAll('.contact-checkbox input[type="checkbox"]:checked');

    console.log(`📊 Contact selection: ${checkedCheckboxes.length} of ${allCheckboxes.length} contacts selected`);

    checkedCheckboxes.forEach(checkbox => {
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

    // Log the selected contacts for debugging
    console.log('Selected contacts by customer:', selectedContacts);
    return selectedContacts;
}

// Send campaign
async function sendCampaign(testMode) {
    if (!currentCampaignId) {
        alert('No campaign selected');
        return;
    }

    // Get selected contacts
    const selectedContacts = getSelectedContacts();

    // Get edited messages
    const editedEmailSubject = document.getElementById('edit-email-subject')?.value;
    const editedEmailBody = document.getElementById('edit-email-body')?.value;

    const confirmMessage = testMode
        ? 'Send test EMAIL campaign to YOUR personal email?\n\nEmail: norbert@bmasiamusic.com\n\n(Will NOT send to actual customers)'
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
        if (editedEmailSubject || editedEmailBody) {
            requestBody.edited_messages = {
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
    const totalSent = result.results_by_customer?.reduce((sum, c) =>
        sum + Object.values(c.sent || {}).reduce((a, b) => a + b, 0), 0) || 0;
    const totalFailed = result.results_by_customer?.reduce((sum, c) =>
        sum + Object.values(c.failed || {}).reduce((a, b) => a + b, 0), 0) || 0;

    let resultsHTML = `
        <div class="result-summary" style="background: #f0f8ff; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3>✅ Campaign Sent Successfully!</h3>
            <p><strong>Campaign ID:</strong> ${result.campaign_id}</p>
            <p><strong>Channel:</strong> Email</p>
            <p><strong>Total Sent:</strong> ${totalSent} | <strong>Failed:</strong> ${totalFailed}</p>
        </div>

        <h4 style="margin-top: 20px;">📧 Email Recipients:</h4>
    `;

    // Add customer results
    if (result.results_by_customer && result.results_by_customer.length > 0) {
        resultsHTML += `<div style="background: white; border: 1px solid #ddd; border-radius: 5px; padding: 15px;">`;

        result.results_by_customer.forEach(customer => {
            const emailSent = customer.sent?.email || 0;
            const emailFailed = customer.failed?.email || 0;
            const status = emailSent > 0 ? '✅ Sent' : emailFailed > 0 ? '❌ Failed' : '⏳ Pending';
            const statusColor = emailSent > 0 ? '#4CAF50' : emailFailed > 0 ? '#f44336' : '#ff9800';

            resultsHTML += `
                <div style="padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="font-size: 16px;">${customer.customer}</strong><br>
                        <span style="color: #666; font-size: 14px;">📧 ${customer.email || 'No email'}</span><br>
                        <span style="color: #999; font-size: 12px;">Zones: ${customer.zones ? customer.zones.join(', ') : 'N/A'}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="color: ${statusColor}; font-weight: bold;">${status}</span><br>
                        <span style="font-size: 12px; color: #666;">
                            ${customer.contact_count || 1} contact(s)
                        </span>
                    </div>
                </div>
            `;
        });

        resultsHTML += `</div>`;
    } else {
        resultsHTML += `<p style="color: #666;">No recipient details available.</p>`;
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

        let html = '';

        // Show recent campaigns if available
        if (stats.recent_campaigns && stats.recent_campaigns.length > 0) {
            html = '<div style="max-height: 400px; overflow-y: auto;">';

            stats.recent_campaigns.forEach(campaign => {
                const statusColor = campaign.status === 'completed' ? '#4CAF50' :
                                  campaign.status === 'tested' ? '#2196F3' :
                                  campaign.status === 'sending' ? '#ff9800' : '#666';

                const sentTime = campaign.completed_at || campaign.sent_at || campaign.created_at;
                const timeStr = sentTime ? new Date(sentTime).toLocaleString() : 'Not sent yet';

                html += `
                    <div style="background: white; border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h4 style="margin: 0 0 5px 0; color: #333;">${campaign.name}</h4>
                                <p style="margin: 0; color: #666; font-size: 14px;">
                                    Type: ${campaign.type} | Recipients: ${campaign.recipients} | Zones: ${campaign.zones}
                                </p>
                                <p style="margin: 5px 0 0 0; color: #999; font-size: 12px;">
                                    ${timeStr}
                                </p>
                            </div>
                            <div style="text-align: right;">
                                <span style="background: ${statusColor}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 12px;">
                                    ${campaign.status.toUpperCase()}
                                </span>
                                ${campaign.results ? `
                                    <p style="margin: 5px 0 0 0; font-size: 12px;">
                                        ✅ ${campaign.results.sent} sent<br>
                                        ${campaign.results.failed > 0 ? `❌ ${campaign.results.failed} failed` : ''}
                                    </p>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });

            html += '</div>';
        } else if (stats.campaigns_by_status) {
            // Fallback to showing status counts
            for (const [status, count] of Object.entries(stats.campaigns_by_status)) {
                html += `
                    <div class="campaign-list-item">
                        <div class="campaign-info">
                            <h4>${status.charAt(0).toUpperCase() + status.slice(1)} Campaigns</h4>
                            <p>${count} campaign(s)</p>
                        </div>
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

// Show campaigns list modal
async function showCampaignsList() {
    try {
        const response = await fetch(`${API_BASE}/api/campaigns/list`);
        const data = await response.json();

        if (data.success && data.campaigns) {
            let modalHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: center; justify-content: center;" onclick="if(event.target === this) this.remove()">
                    <div style="background: white; border-radius: 8px; padding: 20px; max-width: 800px; width: 90%; max-height: 80vh; overflow-y: auto;">
                        <h2>📊 All Campaigns</h2>
                        <button onclick="this.closest('div').parentElement.remove()" style="float: right; margin-top: -40px;">✖</button>
            `;

            if (data.campaigns.length > 0) {
                data.campaigns.forEach(campaign => {
                    modalHTML += `
                        <div style="border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin: 10px 0;">
                            <h3>${campaign.name}</h3>
                            <p>Type: ${campaign.type} | Status: ${campaign.status}</p>
                            <p>Recipients: ${campaign.recipients} | Zones: ${campaign.zones}</p>
                            ${campaign.results ? `<p>Sent: ${campaign.results.sent} | Failed: ${campaign.results.failed}</p>` : ''}
                        </div>
                    `;
                });
            } else {
                modalHTML += '<p>No campaigns found.</p>';
            }

            modalHTML += '</div></div>';
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }
    } catch (error) {
        console.error('Error loading campaigns list:', error);
        alert('Error loading campaigns');
    }
}

// Show/hide loading overlay
function showLoading(show) {
    document.getElementById('loading-overlay').style.display = show ? 'flex' : 'none';
}