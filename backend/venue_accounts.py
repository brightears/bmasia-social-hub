"""
Known venue account IDs for direct access
Since the API credentials only show the BMAsia parent account,
we need to directly query specific venue accounts by their IDs
"""

VENUE_ACCOUNTS = {
    'hilton_pattaya': {
        'account_id': 'QWNjb3VudCwsMXN4N242NTZyeTgv',
        'name': 'Hilton Pattaya',
        'aliases': ['hilton pattaya', 'pattaya hilton', 'hilton hotel pattaya'],
        'zones': {
            'drift_bar': 'U291bmRab25lLCwxaDAyZ2k3bHY1cy9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv',
            'edge': 'U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv',
            'horizon': 'U291bmRab25lLCwxZTA5ZGpnMmU0Zy9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv',
            'shore': 'U291bmRab25lLCwxbmVidGE2c2dlOC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv'
        }
    },
    # Add more venues as we discover their account IDs
}

def find_venue_account(venue_name: str) -> dict:
    """Find venue account by name or alias"""
    search_term = venue_name.lower()
    
    for venue_key, venue_data in VENUE_ACCOUNTS.items():
        # Check main name
        if search_term in venue_data['name'].lower():
            return venue_data
        
        # Check aliases
        for alias in venue_data.get('aliases', []):
            if search_term in alias or alias in search_term:
                return venue_data
    
    return None

def get_zone_id(venue_name: str, zone_name: str) -> str:
    """Get zone ID for a specific venue and zone"""
    venue = find_venue_account(venue_name)
    if not venue:
        return None
    
    zone_search = zone_name.lower().replace(' ', '_')
    return venue.get('zones', {}).get(zone_search)