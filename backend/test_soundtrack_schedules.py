#!/usr/bin/env python3
"""
Test script to explore what schedule/playlist data we can get from Soundtrack API
"""

import json
import logging
from soundtrack_api import soundtrack_api

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def explore_zone_data():
    """Explore what data we can get for zones"""
    
    # First, find Hilton Pattaya zones
    print("\n" + "="*60)
    print("SEARCHING FOR HILTON PATTAYA ZONES")
    print("="*60)
    
    zones = soundtrack_api.find_venue_zones("Hilton Pattaya")
    
    if not zones:
        print("No zones found for Hilton Pattaya")
        return
    
    print(f"\nFound {len(zones)} zones:")
    for zone in zones:
        print(f"\n- {zone.get('name')} (ID: {zone.get('id')})")
        print(f"  Online: {zone.get('online', zone.get('isOnline', False))}")
    
    # Take first zone and explore what data we can get
    if zones:
        first_zone = zones[0]
        zone_id = first_zone.get('id')
        zone_name = first_zone.get('name')
        
        print("\n" + "="*60)
        print(f"EXPLORING ZONE: {zone_name}")
        print("="*60)
        
        # 1. Get zone status (might have schedule info)
        print("\n1. Zone Status:")
        status = soundtrack_api.get_zone_status(zone_id)
        print(json.dumps(status, indent=2))
        
        # 2. Get now playing (might show current playlist)
        print("\n2. Now Playing:")
        now_playing = soundtrack_api.get_now_playing(zone_id)
        print(json.dumps(now_playing, indent=2))
        
        # 3. Try a custom query for schedules
        print("\n3. Trying custom query for zone details:")
        zone_detail_query = """
        query GetZoneDetails($zoneId: ID!) {
            node(id: $zoneId) {
                ... on Zone {
                    id
                    name
                    currentSoundtrack {
                        id
                        name
                    }
                    soundtrackSchedule {
                        id
                        name
                        isActive
                        scheduleItems {
                            id
                            startTime
                            endTime
                            soundtrack {
                                id
                                name
                            }
                            daysOfWeek
                        }
                    }
                    playbackSettings {
                        volume
                        crossfadeDuration
                        gaplessModeEnabled
                    }
                }
            }
        }
        """
        
        zone_details = soundtrack_api._make_graphql_request(
            zone_detail_query,
            {"zoneId": zone_id}
        )
        print(json.dumps(zone_details, indent=2))
        
        # 4. Try to get playlists/soundtracks for the account
        print("\n4. Trying to get account soundtracks:")
        soundtracks_query = """
        query GetSoundtracks {
            me {
                ... on PublicAPIClient {
                    accounts(first: 1) {
                        edges {
                            node {
                                id
                                businessName
                                soundtracks(first: 10) {
                                    edges {
                                        node {
                                            id
                                            name
                                            description
                                            tags
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        soundtracks = soundtrack_api._make_graphql_request(soundtracks_query)
        print(json.dumps(soundtracks, indent=2))


if __name__ == "__main__":
    explore_zone_data()