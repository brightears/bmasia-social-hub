#!/usr/bin/env python3
"""Google Sheets Structure Guide - What the bot expects"""

print('=' * 60)
print('📋 Google Sheets Structure Guide for BMA Social Bot')
print('=' * 60)
print()

print("✅ OPTIMIZED STRUCTURE (AI Best Practices):")
print("-" * 40)
print("""
Column | Field Name              | Format Example
-------|------------------------|---------------------------
A      | property_name          | Hilton Pattaya
B      | business_type          | Hotel
C      | zone_count             | 4
D      | zone_names             | Drift Bar|Edge|Horizon|Shore
E      | music_platform         | Soundtrack Your Brand
F      | annual_price_per_zone  | 10500
G      | currency               | THB
H      | contract_start         | 2024-11-01
I      | contract_end           | 2025-10-31
J      | primary_contact_name   | Jittima Ruttitham
K      | primary_contact_title  | Purchasing Manager
L      | primary_contact_email  | jittima.ruttitham@hilton.com
M      | soundtrack_account_id  | QWNjb3VudCwsMXN4N242NTZyeTgv
N      | hardware_type          | Soundtrack Player
O      | special_notes          | Special rate THB 10,500
""")

print("\n⚠️  ACCEPTABLE (Current Structure - Still Works):")
print("-" * 40)
print("""
Column | Field Name                            | Format Example
-------|---------------------------------------|---------------------------
A      | property_name                         | Hilton Pattaya
B      | business_type                         | Hotel
C      | amount_of_zones_venues                | 4
D      | name_of_zones_venues                  | Drift Bar, Edge, Horizon, Shore
E      | music_platform                        | Soundtrack Your Brand
F      | current_price_per_zone_venue_per_year | THB 10,500
G      | contract_expiry                       | 31st October 2025
H      | contact_name_1                        | Jittima Ruttitham
I      | contact_title_1                       | Purchasing Manager
J      | contact_email_1                       | jittima.ruttitham@hilton.com
""")

print("\n🔄 KEY IMPROVEMENTS TO MAKE:")
print("-" * 40)
print("""
1. DATE FORMATS:
   Current:  31st October 2025
   Better:   2025-10-31
   Why:      ISO format is unambiguous for AI

2. PRICE FIELDS:
   Current:  THB 10,500 (mixed text/number)
   Better:   10500 (number) + THB (separate currency field)
   Why:      Enables calculations

3. ZONE SEPARATOR:
   Current:  Zone A, Zone B, Zone C
   Better:   Zone A|Zone B|Zone C
   Why:      Commas can appear in names

4. FIELD NAMES:
   Current:  amount_of_zones_venues
   Better:   zone_count
   Why:      Simpler is better for AI
""")

print("\n📌 VALIDATION RULES TO ADD (Data → Data Validation):")
print("-" * 40)
print("""
1. business_type dropdown:
   - Hotel
   - Restaurant  
   - Bar
   - Club
   - Resort
   - Other

2. music_platform dropdown:
   - Soundtrack Your Brand
   - Beat Breeze (Royalty-Free)
   - Multiple Platforms
   - Other

3. Date validation:
   - Format: Date
   - Criteria: Valid date

4. Email validation:
   - Format: Text contains @
""")

print("\n✨ The bot will work with EITHER structure,")
print("   but the optimized version will be more reliable!")
print("\n💡 Most important: Be CONSISTENT across all entries!")