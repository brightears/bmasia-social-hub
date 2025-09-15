#!/usr/bin/env python3
"""
Simple Flask test server for BMA Social Campaign Manager
Tests the checkbox display functionality
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Serve static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(os.path.dirname(__file__), 'backend', 'static')
    return send_from_directory(static_dir, filename)

# Serve main page
@app.route('/')
def index():
    static_dir = os.path.join(os.path.dirname(__file__), 'backend', 'static')
    return send_from_directory(static_dir, 'index.html')

# Mock API endpoints
@app.route('/api/campaigns/statistics')
def get_statistics():
    return jsonify({
        'customer_statistics': {
            'total_customers': 42,
            'total_zones': 150,
            'expiring_30_days': 8
        },
        'active_campaigns': 3,
        'campaigns_by_status': {
            'active': 3,
            'completed': 12,
            'draft': 2
        }
    })

@app.route('/api/campaigns/create', methods=['POST'])
def create_campaign():
    # Return mock campaign data
    return jsonify({
        'success': True,
        'campaign': {
            'id': 'test-campaign-123',
            'type': 'renewal',
            'plan': {
                'campaign_name': 'Test Renewal Campaign',
                'campaign_goal': 'Renew expiring contracts'
            },
            'statistics': {
                'total_customers': 2,
                'total_zones': 5
            },
            'target_customers': [
                {
                    'name': 'Hilton Bangkok Sukhumvit',
                    'customer_id': 'hilton-bkk-001'
                },
                {
                    'name': 'Marriott Bangkok',
                    'customer_id': 'marriott-bkk-001'
                }
            ]
        }
    })

@app.route('/api/campaigns/<campaign_id>/preview')
def preview_campaign(campaign_id):
    # Return mock preview data with contacts
    return jsonify({
        'campaign_id': campaign_id,
        'type': 'renewal',
        'plan': {
            'campaign_name': 'October Renewal Campaign',
            'campaign_goal': 'Renew contracts expiring in October'
        },
        'statistics': {
            'total_zones': 5
        },
        'sample_messages': [
            {
                'customer': 'Hilton Bangkok Sukhumvit',
                'brand': 'Hilton Hotels & Resorts',
                'zones': ['Lobby', 'Restaurant', 'Spa'],
                'contacts': [
                    'Rudolf Troestler (General Manager)',
                    'Dennis Leslie (Director of Food & Beverage)'
                ],
                'contact': 'Rudolf Troestler (General Manager), Dennis Leslie (Director of Food & Beverage)',
                'whatsapp': 'Hello! Your Soundtrack Your Brand contract is expiring soon. We would love to continue providing excellent music for your venue.',
                'email_subject': 'Contract Renewal Reminder - Hilton Bangkok',
                'email_body': 'Dear Rudolf,\n\nYour music service contract is expiring soon...',
                'channels': ['whatsapp', 'email']
            },
            {
                'customer': 'Marriott Bangkok',
                'brand': 'Marriott International',
                'zones': ['Main Lobby', 'Pool Area'],
                'contacts': [
                    'Sarah Johnson (General Manager)',
                    'Mike Chen (Operations Manager)',
                    'Lisa Wong (Marketing Director)'
                ],
                'contact': 'Sarah Johnson (General Manager), Mike Chen (Operations Manager), Lisa Wong (Marketing Director)',
                'whatsapp': 'Hello! Your Soundtrack Your Brand contract is expiring soon. We would love to continue providing excellent music for your venue.',
                'email_subject': 'Contract Renewal Reminder - Marriott Bangkok',
                'email_body': 'Dear Sarah,\n\nYour music service contract is expiring soon...',
                'channels': ['whatsapp', 'email']
            }
        ],
        'total_customers': 2,
        'estimated_sends': {
            'whatsapp': 2,
            'email': 2,
            'line': 0
        }
    })

@app.route('/api/campaigns/<campaign_id>/send', methods=['POST'])
def send_campaign(campaign_id):
    return jsonify({
        'campaign_id': campaign_id,
        'channels': ['whatsapp', 'email'],
        'results_by_customer': [
            {
                'customer': 'Hilton Bangkok Sukhumvit',
                'channels_used': ['whatsapp', 'email'],
                'sent': {'whatsapp': 2, 'email': 2},
                'failed': {'whatsapp': 0, 'email': 0}
            },
            {
                'customer': 'Marriott Bangkok',
                'channels_used': ['whatsapp', 'email'],
                'sent': {'whatsapp': 3, 'email': 3},
                'failed': {'whatsapp': 0, 'email': 0}
            }
        ],
        'ai_report': 'Campaign sent successfully to 2 customers with 100% delivery rate.'
    })

if __name__ == '__main__':
    print("=" * 60)
    print("BMA SOCIAL CAMPAIGN MANAGER - TEST SERVER")
    print("=" * 60)
    print("\n✅ Starting test server with checkbox fix...")
    print("\n📌 Open your browser and go to: http://localhost:5002")
    print("\n🔧 Test Instructions:")
    print("1. Click 'Create Campaign with AI' or use Advanced options")
    print("2. In the preview, you should see CHECKBOXES next to each contact name")
    print("3. Try unchecking some contacts (e.g., uncheck Rudolf)")
    print("4. Click 'Test Send' to verify selection works")
    print("\n⚠️  Press Ctrl+C to stop the server")
    print("=" * 60)

    app.run(host='0.0.0.0', port=5002, debug=True)