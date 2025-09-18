# Soundtrack Your Brand — Technical Requirements

## Supported Devices
- One device per zone; each zone can only be connected to one device at a time.
- **iOS**: Requires iOS 15.1 or later; minimum 2 GB free space.
- **Android**: Requires Android 8 or later; at least 3 GB RAM and 2 GB free space.
- **Windows**: Two apps available — Enterprise Windows app (background service) and new Windows desktop app. Requirements: 512+ MB RAM, 2 GB+ space for install and cache. Supports Windows 8, 10, 11 (32‑ & 64‑bit).
- **macOS**: Supports Intel and Apple Silicon; recommended macOS 14.2+.
- **Chrome OS**: 3 GB+ RAM, 2 GB free space; devices from 2019 onward.
- **Dedicated / partner hardware**:
  - Soundtrack Player (dedicated hardware box)
  - Sonos devices / Sonos integration
  - Axis Communications speakers / audio bridges (C8033, C8110, C1004‑E, C2005, C3003)
  - AUDAC NMP40 modular solution
  - WiiM devices (Pro, Ultra, Amp)

## Network Settings
- Wired connection or separate Wi-Fi channel recommended.
- Dedicated bandwidth: at least 0.5 Mbps per device/zone.
- Cache size recommendation: 4 GB for Android, iOS, and Windows. (Soundtrack Player is pre-configured.)

## Firewall Requirements
- Outbound traffic only; no inbound needed.
- Required open ports:
  - TCP port 443 (HTTPS)
  - TCP/UDP port 53 (DNS)
  - UDP port 123 (NTP)
- Devices must be exempted from filtering, traffic‑inspection, or proxy tools that modify web traffic.

## Additional Notes
- Axis hardware requires SD card installed and updated firmware.
- Static IP can be configured on Soundtrack Player if needed.

---

# Soundtrack Your Brand — Device & Hardware Integrations

## Denon / HEOS Speakers
- Direct integration with Denon/HEOS app is **not supported**.
- Options to play via Denon/HEOS:
  1. Use the *line‑in* output on the HEOS speaker from a supported device.
  2. Connect via Bluetooth from a supported device.
  3. Use AirPlay from an iOS device.

## AUDAC NMP40 Module
- After installing the NMP40 module:
  1. Create a Soundtrack account via AUDAC web interface's settings screen.
  2. In SYB admin, go to "Zones" → Add Zone.
  3. Select "Hardware" and enter the 8‑digit Device ID of the player. (Shown in title bar or settings.)
  4. Click "Connect hardware player".
  5. Once connected, the NMP40 is ready to play music for the assigned zone.

## Soundtrack Player (Dedicated Hardware)
- Stores up to 400 hours of music for offline play.
- Remote software control for schedules/playlists; automatic updates.
- Tamper‑proof, with strong zone, schedule, playlist management.
- **Specs**:
  - Dimensions: ~108 × 79 × 38 mm; weight ~250g; aluminium casing.
  - Connectivity: Ethernet (RJ‑45 10/100 Mbps), IPv4 & IPv6.
  - Outputs: 2x RCA connectors, 3.5 mm headphone jack.
  - Two status LEDs.
  - 1 year warranty.

## Sonos Integration
- Add Soundtrack via the Sonos app ("Add Music Service" → search Soundtrack → connect to your SYB location).
- Sonos automatically assigns the best available Soundtrack zone.
- For multiple Sonos systems or separate Wi‑Fi networks, create separate locations in SYB.
- **Grouping**: Multiple Sonos speakers can be grouped to play the same stream using only one SYB zone.
- **Different music in different rooms**: Requires one SYB zone per distinct stream.
- **Line‑in option**: On Sonos models with line‑in, you can connect a Soundtrack Player; enables full support for schedules and messaging.
- **Playback details**:
  - All playlists and stations play in shuffle mode.
  - Crossfade can be adjusted only in Sonos app (not in SYB).
  - Explicit content filter toggle in SYB takes ~10 minutes to apply.
  - Music stream quality to Sonos is ~96 kbps.

### Sonos Scheduling Feature
- Sonos supports "Alarm" scheduling to auto‑start music at defined times, days, and durations.
- This allows day‑parting: different moods/playlists in morning, afternoon, evening, etc.

---

# Soundtrack Your Brand — Licensing & Availability

## Licensing Model (Summary)
- Soundtrack provides **reproduction rights** (copyrights) for streaming and caching background music from record labels and music publishers.
- **Public performance rights** are handled differently by country:
  - **US & Canada**: Public performance is covered through Soundtrack's agreements for typical background‑music use. Extra activities (live music, DJs, karaoke, ticketed events) may require additional licensing.
  - **UK, Australia, New Zealand**: A separate public performance license from the local PRO is required for venues.
  - **Thailand**: Venues need to obtain a license from MPC Thailand for public performance rights.
  - **Other countries**: Most require a local public performance license from their PRO/collecting society.
- **Important**: While Soundtrack includes reproduction rights, most venues outside US/Canada will still need to pay their local PRO for public performance rights.

## Where Soundtrack Is Available (by region)

### Africa
- Egypt, Morocco, South Africa

### Asia Pacific
- Australia, India, Indonesia, Malaysia, Maldives, New Zealand, Singapore, Thailand

### Caribbean
- Anguilla, Bahamas, Bermuda, Cayman Islands, Martinique, Puerto Rico

### Europe
- Austria, Belgium, Bulgaria, Croatia, Cyprus, Czech Republic, Estonia, Germany, Denmark, Finland, France, Gibraltar, Greece, Hungary, Iceland, Ireland, Italy, Latvia, Liechtenstein, Lithuania, Luxembourg, Malta, Netherlands, Norway, Poland, Portugal, Slovakia, Spain, Sweden, Switzerland, Turkey, United Kingdom

### Latin America
- Argentina, Bolivia, Chile, Colombia, Costa Rica, Ecuador, Guatemala, Honduras, Nicaragua, Panama, Paraguay, Peru, Uruguay

### Middle East
- Bahrain, Jordan, Kuwait, Lebanon, Oman, Saudi Arabia, United Arab Emirates, Qatar

### North America
- Canada, Mexico, United States of America

## Local PROs — Quick Guidance
- **UK**: PPL PRS Ltd (The Music Licence) required.
- **Australia/New Zealand**: OneMusic / OneMusic NZ required.
- **EU & many other countries**: Local PRO(s) typically required for public performance.
- **US/Canada**: Background music via Soundtrack generally covered; extra activities may require additional PRO coverage.

## Common Licensing Scenarios
- **Background music only**: Use Soundtrack in an available country. Acquire local PRO licence where required.
- **Multiple zones/venues**: License applies per zone/device. Ensure each location's PRO obligations are met.
- **Special events (DJ/live/karaoke)**: Additional licensing often needed regardless of background‑music coverage.

---

# Soundtrack Your Brand — Getting Started & Setup

## Quick Start

1. **Sign up** and create your account.
2. **Download the app** on the device that will play music (phone, tablet, desktop) or use a **Soundtrack Player** / **Sonos**.
3. **Pair the device to a zone** (see below).
4. **Add music** (playlists, stations, brand mixes) and **connect to speakers**.
5. Optional: **Create schedules** and **Messaging campaigns**.

---

## Pairing & Switching Devices

### iOS / Android

* Start playback by **logging in** or using a **pairing code** shown in the admin (Zones).
* If moving playback to another device, **unpair** the current one first, then pair the new device.

### Windows / macOS (Desktop Player)

* Log into admin → **Zones** → select zone → **download desktop app** → open app → **enter pairing code** → *Pair now*.

### Soundtrack Player (hardware)

* In admin → **Zones** → choose zone → **Setup → Hardware** → enter **Device ID** (printed on the unit) → connect **power**, **Ethernet**, and **audio out** (RCA or 3.5 mm).
* Auto‑updates firmware/software. Allow some time after network connection before music starts.

### Sonos

* Add **Soundtrack** as a service in the Sonos app → connect to your **location**.
* Sonos will auto‑select the best available **zone** for playback.
* Large venues with multiple Wi‑Fi networks / separate Sonos systems should create **separate locations**.

---

## Connect to Speakers

* **Bluetooth**: Pair device → open app → play.
* **AirPlay 1**: iOS and speaker on same Wi‑Fi → in app choose **connect speaker** → select speaker. *(AirPlay 2 not supported.)*
* **Line‑in**: Connect device's audio out to the sound system's line input.
* **Android → Google Home/Nest**: Use **Google Home** app → **Cast my audio** to the target device.
* **Alexa / Google Home via Bluetooth**: You can pair via Bluetooth (skip/pause control; search by voice not supported).

---

## Core Concepts

### What is a **Zone**?

A **zone** is a single audio stream assigned to a specific area or system (e.g., Lobby, Bar). One **device per zone** at a time. Each zone holds its own music, schedule, and messaging settings.

### What is a **Location**?

A **location** groups one or more zones under a single venue/site (address). Locations are used for access control, Sonos pairing, and reporting. Large venues with separate Sonos systems or networks may use multiple locations.

---

## Multi‑Room / Multiple Zones

* **Same music in multiple rooms**: Group speakers (e.g., in Sonos) → one **zone** can serve the group.
* **Different music in different rooms**: Use **one zone per simultaneous stream**.
* **Multiple Sonos systems / Wi‑Fi networks**: Create additional **locations** and pair each Sonos system accordingly.

---

## Sonos Scheduling (Alarms)

* Use Sonos app **Alarms** to auto‑start music at specific **times**, **days**, and **durations**.
* Combine alarms to **day‑part** (morning/afternoon/evening playlists). Crossfade and other playback settings are controlled in the Sonos app.

---

## Messaging (In‑Store Announcements)

* Works with **Soundtrack Players** and app‑based players; **not compatible with Sonos**.
* Create **Messages** (Audio upload, **Text‑to‑Speech**, or **SSML**); then bundle into **Campaigns**.

### Create Messages

* **Upload audio**: Accepts **.mp3** or **.ogg**; **≤ 5 MB** per file.
* **Text‑to‑Speech (TTS)**: Choose language/voice; adjust pitch/speed; preview before saving.
* **SSML**: Paste SSML to control pauses, pronunciation, pitch/speed. Tip: add brief leading/trailing silence to avoid crossfade cutting.

### Campaigns & Playback

* **Once per day**: Option to **interrupt music playback** to hit the exact minute; otherwise message queues after the current track.
* **Multiple times per day**: Set **active timespan** and **frequency** (e.g., every hour at :15).
* **Dates**: Set start/end; leave end blank for ongoing.
* **Targeting**: Select one or more **zones**. If multiple messages are attached, one is **randomly selected** each time.

### Emergency Messages (On‑Demand)

* From the web admin, instantly **play a message now** to selected zone(s). Music is interrupted, the message plays, then music resumes.

---

# Soundtrack Your Brand — Music Curation, Scheduling & Controls

## Playlists (Unlimited plan)

**What:** Manually curated collections you control track‑by‑track.

**Create a playlist**

1. Go to **Create** and choose **Playlist** (or **Spotify import**).
2. Name it, then add songs by searching artists/titles or using the **…** menu next to any track (**Add to playlist**).
3. Choose **linear** or **shuffled** playback (toggle in playlist menu or Now Playing view).

**Tips**

* To import from Spotify, make the source playlist **public** first.
* In the player app you can **hide/show unavailable songs** within a playlist.

---

## Stations (Essential & Unlimited)

**What:** Algorithmic "radio‑style" streams you can tailor; songs always play **shuffled**.

**Create a station** (three options)

1. **Tags**: energy, genre, sound, decade; optional explicit‑content allowance.
2. **AI prompt**: e.g., "Chillout vibes for a hotel lobby".
3. **From a Spotify playlist** (min \~5 songs).
   • On Essential: create in the app.
   • On Unlimited: create from a web browser.

**Assign** the station to a **zone** after creation.

---

## Spotify Sync (Unlimited)

* Playlists copied from Spotify show a **Spotify badge**.
* To refresh with changes made in Spotify, open the copied playlist and press **Sync** (use **Edit** to pick additional songs to bring over).

---

## Scheduling

### In the web account

1. **Create → Weekly schedule** → **Create a schedule**.
2. Drag & drop **stations** and/or **playlists** onto the grid; ensure opening hours are covered.
3. Save; preview via the info (ⓘ) on any slot; press **Play** and choose zone(s).
   • Schedules loop week‑to‑week; you can maintain multiple schedules.
   • Auto‑start tip: on mobile, have the app in the **foreground** when connecting power.

### In the app

* Switch between **Daily** and **Weekly** modes.
* Use curated, ready‑made schedules per business type; save a copy and adapt.

### Sonos note

* Native scheduling doesn't run on Sonos players. Workarounds include using the mobile app with AirPlay to Sonos, or Sonos Alarms (separate concept).

---

## Queue & Play Queue (Unlimited)

* **Queue a song**: In any playlist, tap **… → Queue to… → Zone**. Queued songs play after the current track, then playback returns to the prior collection.
* **View the play queue**: From Now Playing, open the **…** menu to see the next \~5 tracks.

---

## Block Songs (per‑zone)

* Block from Now Playing (**… → Block song**) or from **Recently played** lists.
* Unblock from the same views.
* On Sonos, block/unblock inside the Soundtrack interfaces (not from the Sonos app).

---

## Explicit Filter (company‑wide)

* Company settings → **Music control → Block all explicit songs**.
* Blocks tracks flagged explicit; you can still play "explicit" playlists/stations but explicit‑flagged tracks won't play.
* You can also block **specific songs** manually per zone (see above).

---

## Linear vs Shuffled

* **Playlists**: Toggle shuffle off to play **linear** (Unlimited).
* **Stations**: Always **shuffled**; linear not available.

---

## Limit Music Selection for Users

* Company settings → **Playback devices → Limit music selection for playback devices**.
* Hides **Home** and **Add music** on iOS/Android/Sonos players; applies to **playback devices** only.
* To prevent in‑app search on devices, connect them via **pairing code**.
* Note: The legacy Enterprise Windows player cannot change playlists in‑app (admins change from the web).

---

## Offline Playback

**How it works**

* Songs you play are cached automatically; playback switches to the cache if the connection drops.

**"More offline play" (Unlimited)**

* Enable per zone in **Zone → Settings → More offline play** to pre‑download a larger set.

**Device & storage notes**

* Require **≥ 4 GB** free storage for offline mode.
* Music stays available offline for **up to \~30 days**; bring the player online periodically.
* While offline, you can't browse new music; you can play what's saved in **Your music**.
* Desktop player: selecting/removing downloads while offline isn't supported.
* **Soundtrack Player** must be online to receive selections; when offline it shuffles what's downloaded.
* Download rotation is automatic as storage fills; to cache an entire playlist, keep the player online and playing it.
* **Sonos** does **not** support offline playback.

---

# Soundtrack Your Brand — Pricing & Add‑Ons

**Note:** Since BMAsia handles pricing and quotations in Asia, the bot should direct price inquiries to the Sales team via Google Chat.

## Plans & Billing Model (Overview)

* **Per‑zone pricing**: Each active **zone** = one concurrent stream and is billed separately.
* **Per‑location structure**: Add unlimited **locations** (venues). Each location needs at least one zone to play music.
* **Trial**: 14‑day free trial (no charges if you cancel within the trial period).
* **Billing cycles**: Monthly or **annual** ("from" prices shown on site typically refer to **per zone, per month when billed annually**).
* **Users**: Invite unlimited users; control permissions.

### Plan lineup

* **Starter** — Simplified, licensed background music for businesses.
  * 1,500+ ready‑made playlists; ad‑free; explicit‑lyrics filter; custom scheduling; one zone of music.

* **Essential** — Reliable streaming + creation of **Stations** (AI, tags, from Spotify), **Sonos** compatible; API access; multi‑location dashboard.

* **Unlimited** — Full control: **create your own Playlists**, **on‑demand** play, **queue exactly what you want**, **play offline**, make your **Spotify playlists legal** for business.

* **Enterprise** — Tailored plan for larger companies (dedicated AM, priority support, assisted onboarding, flexible billing, SSO/SAML).

> **Notes**
> * Feature availability can vary by region. Pricing is shown in local currency on the website and may exclude taxes/fees.

---

## Add‑Ons

### 1) Messaging (Overhead announcements)

* **Price**: **USD 9 / zone / month** (applies to **every zone** on the account, even if a zone isn't playing messages).
* **Availability**: Essential & Unlimited plans.
* **What it does**: In‑platform **Text‑to‑Speech** and **Audio Uploads** (.mp3/.ogg, ≤5 MB) with **scheduling** and **targeting** by zone(s).
* **Intervals**: 10, 15, 20, 30 or 60‑minute options; or set specific times.
* **Compatibility**: **Not compatible with Sonos**.

### 2) Unlimited music control (capability add‑on)

* **Purpose**: Unlocks **on‑demand control** (play/queue exactly what you want), **Playlist creation**, and **Offline** playback.
* **Included in free trial**.
* **Note**: Packaging may vary by region; on some pages this capability is offered as an add‑on rather than a separate "Unlimited" plan.

### 3) Hi‑Fi Audio

* **Price**: **USD 7 / zone / month**.
* **What it does**: Enables **320 kbps** streaming.
* **Account‑wide**: The price applies to **all active zones** on the account (even if some zones don't use 320 kbps).
* **Compatibility**: Hi‑Fi works on all players **except Sonos** (Sonos playback is capped at \~96 kbps).

### 4) Single Sign‑On (SSO)

* **Type**: SAML‑based SSO.
* **Price**: **Quote** (contact sales).

---

## Products & Services (Related)

* **Soundtrack Player** (dedicated hardware): Tamper‑proof device with tight control over zones/schedules/playlists; designed for reliability and offline caching. Sold separately; pricing varies by region.
* **Music Curation (Professional service)**: Optional expert curation for your brand. Setup and recurring fees may apply (region‑specific).

---

## FAQs (Billing & Admin)

* **How many streams can I run?** One per **active zone**. Each additional simultaneous stream requires another zone (additional cost).
* **Can I use one subscription across multiple locations?** Yes—add as many **locations** as needed; each requires at least one zone to play.
* **What happens after the trial?** If you keep using the service, add payment details and choose a plan. If you cancel during the trial, no charges apply.
* **What if I cancel after the trial?** Service continues through the paid period; no auto‑renewal charge for the next period.

---
---
---

# Beat Breeze — Product Information

**Important:** Beat Breeze is a separate product from Soundtrack Your Brand. The bot must clearly identify which product the customer is asking about.

## Beat Breeze Overview

Beat Breeze is BMAsia's proprietary background music solution designed for businesses seeking a cost-efficient, completely royalty-free music system.

## Key Features

* **30,000 Royalty-Free Tracks** — Curated library of completely royalty-free music
* **50 Playlists** — Ready-made playlists for various business types
* **Complete Royalty-Free Licensing** — No copyright or performance rights fees ever
* **No PRO Fees Required** — Completely royalty-free means no collecting society payments
* **Centralized Multi-Zone Setup** — Control multiple zones from one interface
* **Hardware Diagnostics Service** — Monitor and troubleshoot hardware remotely
* **Advanced Scheduling Function** — Day-parting and time-based playlist changes
* **Integrated Messaging System** — In-store announcements and promotions
* **Offline Playback Capability** — Continue playing during internet outages
* **Bespoke design service** — Custom playlist creation for your brand
* **24/7 Technical support** — Round-the-clock assistance
* **License-Free Cost Efficiency** — No recurring licensing fees

## Supported Platforms

* **Android** — Android devices and tablets
* **Windows** — Windows PCs and compatible devices

## Pricing

**Note:** For Beat Breeze pricing and quotations, please direct inquiries to the BMAsia Sales team via Google Chat.

---

## Bot Guidance for Product Differentiation

When a customer contacts via WhatsApp or LINE:

1. **Ask which product they're interested in:**
   - "Are you asking about Soundtrack Your Brand or Beat Breeze?"
   - "Which music system are you currently using or interested in?"

2. **If unclear, briefly explain both:**
   - **Soundtrack Your Brand**: Global platform with Spotify integration, 50+ countries
   - **Beat Breeze**: BMAsia's cost-efficient solution with included PRO licenses

3. **Never mix product information:**
   - SYB sections are clearly marked: "Soundtrack Your Brand —"
   - Beat Breeze sections are marked: "Beat Breeze —"
   - Provide information only from the relevant product section

4. **For pricing inquiries on either product:**
   - Escalate to Sales team via Google Chat
   - Do not quote prices directly

---

# Licensing Comparison — Beat Breeze vs Soundtrack Your Brand

## Overview

Both products provide legal background music for businesses, but their licensing models differ significantly.

## Beat Breeze Licensing

### Complete Royalty-Free Solution
* **100% Royalty-Free Music** — No copyright or performance rights fees
* **NO PRO payments ever** — Completely royalty-free library
* **30,000 royalty-free tracks** — All cleared for commercial use worldwide
* **Works in ALL countries** — No regional licensing complications
* **One simple payment** — No hidden fees or additional licenses

### Key Advantage
**Beat Breeze uses completely royalty-free music.** This means you NEVER need to pay any PRO, collecting society, or rights organization. No MCPT (Thailand), no PPL PRS (UK), no OneMusic (Australia) - nothing. The music is 100% royalty-free for commercial use.

---

## Soundtrack Your Brand Licensing

### What's Included
* **100+ Million tracks** — Massive library including major labels and artists
* **Reproduction rights included** — Copyrights cleared from labels and publishers
* **Legal Spotify synchronization** — Convert personal playlists for business use
* **Multi-country availability** — 50+ countries supported

### Additional PRO License May Be Required
**IMPORTANT**: With Soundtrack Your Brand, you typically still need to pay for Public Performance Rights to your local collecting society:
* **Thailand**: MCPT (Music Copyright Protection Thailand) license required
* **UK**: PPL PRS Ltd (The Music Licence) required
* **Australia/New Zealand**: OneMusic / OneMusic NZ required
* **EU & other countries**: Local PRO license required
* **US & Canada**: Exception - PRO included for typical background music

---

## Key Licensing Differences

| Aspect | Beat Breeze | Soundtrack Your Brand |
|--------|------------|----------------------|
| **Track Library** | 30,000 royalty-free tracks | 100+ Million licensed tracks |
| **Music Type** | Royalty-free music | Major labels & artists |
| **PRO License Required** | NO - Completely royalty-free | YES - In most countries |
| **Additional Fees** | None | PRO fees in most countries |
| **Geographic Coverage** | Works everywhere, no complications | 50+ countries with variations |
| **Spotify Integration** | No | Yes (Unlimited plan) |
| **Licensing Complexity** | Simple - no licenses needed | Complex - varies by country |

---

## Which Product for Licensing Simplicity?

### Choose Beat Breeze if:
* You want **completely royalty-free music** with no PRO fees ever
* You operate in countries with **expensive PRO licenses** (like Thailand's MCPT)
* You prefer **simple, one-time payment** without ongoing licensing fees
* 30,000 royalty-free tracks is sufficient for your needs

### Choose Soundtrack Your Brand if:
* You need **maximum music variety** (100+ million tracks including major artists)
* You want **Spotify playlist integration**
* You're in US/Canada where PRO is included
* You don't mind managing regional PRO requirements

---

## Bot Guidance for Licensing Questions

When customers ask about licensing:

### For Beat Breeze:
"Beat Breeze uses completely royalty-free music, so you don't need ANY licenses - no PRO fees, no MCPT (Thailand), no collecting society payments ever. The music is 100% royalty-free for commercial use."

### For Soundtrack Your Brand:
"Soundtrack Your Brand includes reproduction rights (copyrights) for over 100 million tracks from major labels. However, in most countries including Thailand, you'll still need a Public Performance License from your local PRO (MCPT in Thailand). Only in the US and Canada is the PRO license included."

### If comparing both:
"The main licensing difference:
- Beat Breeze: 30,000 completely royalty-free tracks - NO licenses or PRO fees needed
- Soundtrack Your Brand: 100+ million licensed tracks - reproduction rights included but PRO license needed in most countries (like MCPT in Thailand)

Would you like to know more about either option?"

### Note to bot:
Only mention consumer services (Spotify, YouTube) being illegal if the customer specifically asks about using them.

---

# Sales Process & Demo Booking

## For New Customer Inquiries

When a potential customer shows interest in either product, the bot should:

### 1. Initial Assessment
Determine if the customer is:
- **Existing customer** with issues → Handle or escalate to support
- **Existing customer** with sales questions → Escalate to Sales
- **New prospect** interested in learning more → Offer demo or escalate

### 2. For Qualified Prospects

If the customer seems genuinely interested (asking about features, pricing, or implementation), the bot can:

**Option A: Offer a Demo/Tutorial Call**
```
"I'd be happy to arrange a presentation where we can show you exactly how [Product Name] works for your business.

You can book a convenient time for a demo call here:
[Book a Demo](https://calendly.com/bmasia/sound-innovations)

During the call, we'll:
- Show you the platform in action
- Discuss your specific needs
- Answer all your questions
- Provide pricing for your setup"
```

**Option B: Direct to Sales Team**
```
"Let me connect you with our Sales team who can provide detailed pricing and a customized solution for your business."
[Then escalate to Google Chat Sales space]
```

### 3. When to Offer Demo Booking

**Good candidates for demo:**
- Asking detailed questions about features
- Comparing both products
- Multiple locations or complex needs
- Requesting a quote or pricing
- Saying "I'm interested" or "Tell me more"

**Skip demo, escalate directly:**
- Urgent issues or complaints
- Very basic questions already answered
- Existing customer problems
- Not a business (consumer inquiry)

### 4. Demo Booking Link Usage

**Calendly Link:** https://calendly.com/bmasia/sound-innovations

**How to present it:**
- Always use markdown format: `[Book a Demo](https://calendly.com/bmasia/sound-innovations)`
- This displays as a clickable "Book a Demo" link
- Never paste the raw URL - it looks unprofessional
- Include brief description of what happens in the demo

### 5. Follow-up Message

After providing the booking link:
```
"Once you've booked a time, you'll receive a confirmation email with the meeting details. If you have any urgent questions before the demo, feel free to ask!"
```

## Bot Decision Tree for Sales

```
New Inquiry
├── Existing Customer?
│   ├── Yes → Support Issue? → Escalate to appropriate team
│   └── No → Continue below
│
├── Interested in Product?
│   ├── Basic Info Needed → Answer from product_info.md
│   ├── Pricing Request → Offer demo OR escalate to Sales
│   └── Complex/Multiple Questions → Offer demo booking
│
└── Not Qualified
    └── Provide basic info and close politely
```

## Sample Responses

### For interested prospect:
"Great to hear you're interested in [Product]! I can see you have a [type of business] that could really benefit from our background music solution.

Would you like to schedule a quick demo where we can show you exactly how it works and discuss pricing for your specific needs?

[Book a Demo](https://calendly.com/bmasia/sound-innovations)"

### For price-only inquiry:
"For pricing, I can either:
1. Connect you with our Sales team right away for a quick quote
2. Schedule a demo where we'll show you the platform and provide customized pricing

Which would you prefer?"

### For comparison shopper:
"Since you're evaluating both Soundtrack Your Brand and Beat Breeze, I'd recommend booking a demo where we can show you both platforms and help you choose the best fit for your business.

[Schedule a Comparison Demo](https://calendly.com/bmasia/sound-innovations)"