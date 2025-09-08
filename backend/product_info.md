# BMA Social Product Information & Technical Details

## Products Overview

### Soundtrack Your Brand (SYB)
**Tagline**: Professional Background Music for Business
**Target**: Hotels, Restaurants, Retail, Fitness Centers
**Provider**: Soundtrack Your Brand (Swedish company)

### Beat Breeze
**Tagline**: Affordable Background Music Solution
**Target**: Small businesses, Cafes, Local shops
**Provider**: BMA's proprietary solution

---

## Soundtrack Your Brand - Details

### Pricing Tiers
- **Essential**: 29 USD/month per zone
  - Access to 100+ playlists
  - Basic scheduling
  - Single zone control
  
- **Unlimited**: 39 USD/month per zone
  - Unlimited playlist access
  - Advanced scheduling
  - Multi-zone control
  - Custom playlists
  - Explicit content filter
  
- **Enterprise**: Custom pricing
  - Everything in Unlimited
  - Priority support
  - Custom music curation
  - Brand music alignment
  - Detailed analytics

### Technical Specifications
- **Hardware Required**: Soundtrack Player or compatible device
- **Internet**: Minimum 10 Mbps stable connection
- **Audio Output**: 3.5mm jack or HDMI
- **App Platforms**: iOS, Android, Web Dashboard
- **API Access**: Available for Enterprise (limited for others)

### Key Features
- **Legal Compliance**: Fully licensed for commercial use
- **Spotify Integration**: Import Spotify playlists (converted for commercial use)
- **Scheduling**: Set different music for different times/days
- **Remote Control**: Manage all locations from one dashboard

### Zone Discovery System (As of Sept 8, 2025)
- **Scalable Architecture**: Supports 2000+ venues without hardcoding
- **Multi-Strategy Approach**: 
  1. Redis cache (when available)
  2. Hardcoded venue_accounts.py (for known venues like Hilton)
  3. API search through accessible accounts
  4. Fuzzy matching for venue/zone names
- **Key Files**:
  - `zone_discovery.py` - Main discovery service
  - `venue_accounts.py` - Hardcoded fallback
- **Working Zone IDs** (Hilton Pattaya):
  - Edge: `U291bmRab25lLCwxOGZ5M2R2a2NuNC9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv`
  - Drift Bar: `U291bmRab25lLCwxaDAyZ2k3bHY1cy9Mb2NhdGlvbiwsMW9wM3prbHBjZTgvQWNjb3VudCwsMXN4N242NTZyeTgv`
- **Offline Playback**: Continues playing if internet drops
- **Explicit Filter**: Automatically removes inappropriate content

### CRITICAL: API Authentication & Access (Sept 8, 2025)
- **Current Credentials**: Base64 encoded in SOUNDTRACK_API_CREDENTIALS env var
- **Access Level**: Demo accounts only (NOT production venues like Hilton)
- **Solution**: Using hardcoded zone IDs for known venues
- **Future Need**: OAuth or venue-specific tokens for 2000+ venues

### What SYB API CAN Do
- Adjust volume
- Skip tracks
- Pause/Resume playback
- Check what's currently playing
- Monitor zone status

### What SYB API CANNOT Do (Licensing Restrictions)
- Change playlists programmatically
- Create/edit playlists via API
- Block specific songs via API
- Schedule music changes via API
- Give customers direct control (no "jukebox" mode)

### Setup Process
1. Sign contract & payment
2. Receive Soundtrack Player (or use existing hardware)
3. Connect to internet and audio system
4. Download Soundtrack app
5. Login with credentials
6. Select zones and playlists
7. Set schedule if needed

### Common Issues & Solutions
- **No Sound**: Check audio cable connections and volume on both player and amplifier
- **Music Stops**: Check internet connection, restart player if needed
- **Wrong Playlist**: Update schedule in app, changes take 5-10 minutes
- **Skipping Songs**: Usually network issues, check bandwidth
- **Can't Login**: Reset password via app, contact support if enterprise account

---

## Beat Breeze - Details

### Pricing
- **Basic**: 15 USD/month per location
  - 50+ curated playlists
  - Basic scheduling
  - Single location
  
- **Pro**: 25 USD/month per location
  - 100+ playlists
  - Advanced scheduling
  - Multi-location management
  - Phone support

### Technical Specifications
- **Hardware**: Any Android device, tablet, or computer
- **Internet**: 5 Mbps minimum
- **Audio Output**: Any standard audio connection
- **App Platforms**: Android, Web player
- **Storage**: 2GB for offline cache

### Key Features
- **Affordable**: 50% less than premium solutions
- **Simple Setup**: Works on existing devices
- **Curated Music**: Professionally selected tracks
- **Basic Scheduling**: Day/night modes
- **Offline Mode**: Up to 24 hours offline playback
- **Local Support**: Thailand-based support team

### Limitations vs SYB
- Fewer playlist options
- No Spotify integration
- Limited API access
- No multi-zone per location
- Basic analytics only

### Setup Process
1. Sign up online
2. Download Beat Breeze app
3. Login with credentials
4. Select playlist
5. Connect to audio system
6. Start playing

### Common Issues
- **App Crashes**: Update to latest version, clear cache
- **Limited Playlists**: Upgrade to Pro for more options
- **Scheduling Issues**: Only 2 schedules on Basic plan

---

## Comparison Chart

| Feature | Soundtrack Your Brand | Beat Breeze |
|---------|----------------------|-------------|
| **Starting Price** | $29/zone/month | $15/location/month |
| **Playlists** | Unlimited (on higher tiers) | 50-100 |
| **Spotify Integration** | ✅ Yes | ❌ No |
| **Multi-zone** | ✅ Yes | ❌ No (one zone per location) |
| **API Access** | ✅ Limited | ❌ Very Limited |
| **Custom Playlists** | ✅ Yes (Unlimited+) | ❌ No |
| **Scheduling** | ✅ Advanced | ⚠️ Basic |
| **Hardware** | Dedicated player available | Use existing devices |
| **Support** | 24/7 Global | Business hours Thailand |
| **Offline Playback** | ✅ Yes | ✅ Yes (24 hours) |
| **Explicit Filter** | ✅ Yes | ⚠️ Basic |
| **Commercial License** | ✅ Full global | ✅ Thailand/SEA |

---

## Frequently Asked Questions

### For New Customers

**Q: Why can't I just use Spotify/YouTube?**
A: Consumer streaming services are not licensed for commercial use. Using them in business can result in legal action and fines from copyright holders. Our solutions include proper commercial licensing.

**Q: How many zones/locations do I need?**
A: Each distinct area where you want different music needs its own zone. For example: Restaurant dining area (1 zone), Bar area (1 zone), Outdoor terrace (1 zone) = 3 zones total.

**Q: Can customers request songs?**
A: No, due to licensing restrictions, customers cannot directly control the music. However, staff can skip songs or adjust volume through the app.

**Q: What happens if internet goes down?**
A: Both systems continue playing cached music. SYB can play indefinitely offline, Beat Breeze for 24 hours.

**Q: Can I use my own music/playlists?**
A: SYB Unlimited+ allows custom playlists using licensed tracks. You cannot upload your own MP3s due to licensing requirements.

### For Existing Customers

**Q: How do I change playlists?**
A: Open the app, select your zone, choose new playlist. Changes take 5-10 minutes to apply. For scheduled changes, our team can help set this up.

**Q: Why did the music stop?**
A: Usually internet connectivity. Check your connection, restart the player if needed. If problem persists, our team will help remotely.

**Q: Can I block specific songs?**
A: This needs to be done by our support team through the business dashboard. Send us the song details and we'll block it within 24 hours.

**Q: How do I add more zones?**
A: Contact our sales team. We'll upgrade your plan and help configure the new zones.

**Q: Volume changes aren't working?**
A: Check that volume is not controlled by your amplifier. The app controls the player's output volume, not external amplifier volume.

---

## Sales Talking Points

### Why Choose Professional Background Music?
1. **Legal Protection**: Avoid copyright fines (up to $150,000 per song in some countries)
2. **Brand Alignment**: Music that matches your brand identity
3. **Customer Experience**: Proven to increase dwell time and sales
4. **Professional Curation**: No inappropriate songs or dead air
5. **Remote Management**: Control all locations from anywhere

### Why BMA Social?
1. **Local Support**: Thailand-based team, support in Thai and English
2. **Quick Response**: Most issues resolved within 1 hour
3. **Flexible Solutions**: From affordable Beat Breeze to premium SYB
4. **Integration Expertise**: We handle all technical setup
5. **Proven Track Record**: 500+ venues across Thailand

### ROI Arguments
- Background music increases sales by 9% on average (studies show)
- Customers stay 18% longer with appropriate music
- 76% of customers say music affects their choice of venue
- Reduces perceived wait time by up to 15%

---

## Technical Support Escalation

### Level 1 (Bot Can Handle)
- What's currently playing
- Volume adjustment
- Skip track
- Pause/resume
- Basic troubleshooting steps

### Level 2 (Needs Human Support)
- Playlist changes
- Schedule modifications
- Song blocking
- Account/billing issues
- Hardware problems

### Level 3 (Needs Technical Team)
- API integration issues
- Network configuration
- Multi-location setup
- Custom development requests
- Hardware replacement

---

## Contact Information

### Sales Inquiries
- **Email**: sales@bmasocial.com
- **Phone**: +66 2 123 4567
- **Hours**: Mon-Fri 9:00-18:00 ICT

### Technical Support
- **Email**: support@bmasocial.com
- **Phone**: +66 2 123 4568
- **Hours**: 24/7 for SYB Enterprise, Business hours for others

### Emergency Support (Enterprise Only)
- **Hotline**: +66 2 123 4569
- **Response Time**: Within 30 minutes

---

## Notes for Bot Implementation

When responding to product inquiries:
1. First identify if they're asking about SYB or Beat Breeze
2. If unsure, present both options with clear comparison
3. For pricing, always mention "starting from" as prices vary by zone/features
4. For technical issues, try basic troubleshooting first
5. Escalate to human sales team for: custom quotes, enterprise deals, contract negotiations
6. Escalate to human support for: playlist changes, song blocking, billing issues