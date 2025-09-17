#!/usr/bin/env python3
"""
Find all venues without contact information in venue_data.md
"""

# Read the venue_data.md file
with open('/Users/benorbe/Documents/BMAsia Social Hub/backend/venue_data.md', 'r') as f:
    lines = f.readlines()

current_venue = None
venues_without_contacts = []
in_contacts_section = False
has_contact = False

for i, line in enumerate(lines):
    # New venue section
    if line.startswith('### '):
        # Check if previous venue had no contact
        if current_venue and not has_contact:
            venues_without_contacts.append(current_venue)

        # Start tracking new venue
        current_venue = line.replace('### ', '').strip()
        in_contacts_section = False
        has_contact = False

    # Entering contacts section
    elif '#### Contacts' in line:
        in_contacts_section = True

    # Check if there's a real contact (not placeholder)
    elif in_contacts_section and '- **General Manager**:' in line:
        # Check if it's not a placeholder
        if i + 1 < len(lines):
            email_line = lines[i + 1]
            if '- Email:' in email_line and '—' not in email_line:
                has_contact = True

# Don't forget the last venue
if current_venue and not has_contact:
    venues_without_contacts.append(current_venue)

# Sort alphabetically for easier reading
venues_without_contacts.sort()

# Print results
print(f"Found {len(venues_without_contacts)} venues without contacts:\n")
print("=" * 60)

for i, venue in enumerate(venues_without_contacts, 1):
    print(f"{i:3}. {venue}")

print("\n" + "=" * 60)
print(f"\nTotal venues without contacts: {len(venues_without_contacts)}")
print(f"You can search for these specific venue names in your Gmail.")

# Also save to a text file for easy reference
with open('/Users/benorbe/Documents/BMAsia Social Hub/backend/venues_without_contacts.txt', 'w') as f:
    f.write("Venues without contact information:\n")
    f.write("=" * 60 + "\n\n")
    for venue in venues_without_contacts:
        f.write(f"- {venue}\n")
    f.write(f"\n\nTotal: {len(venues_without_contacts)} venues")

print("\nList also saved to: venues_without_contacts.txt")