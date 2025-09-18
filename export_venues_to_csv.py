#!/usr/bin/env python3
"""
Export venue_data.md to CSV for Brevo CRM import
Extracts all venues and contacts into a format suitable for email marketing
"""

import csv
import re
from datetime import datetime


def clean_value(value):
    """Clean up values - replace dashes with empty strings"""
    if value in ['—', '-', None]:
        return ''
    return str(value).strip()


def parse_venue_data(file_path):
    """Parse the venue_data.md file and extract all venue and contact information"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by venue separator (---)
    venues = content.split('\n---\n')

    all_contacts = []

    for venue_text in venues:
        if not venue_text.strip() or '### ' not in venue_text:
            continue

        # Extract venue name
        venue_match = re.search(r'### (.+)', venue_text)
        if not venue_match:
            continue

        venue_name = venue_match.group(1).strip()

        # Extract venue details
        venue_info = {
            'venue_name': venue_name,
            'business_type': '',
            'zone_count': '',
            'zone_names': '',
            'music_platform': '',
            'annual_price': '',
            'currency': '',
            'contract_start': '',
            'contract_end': '',
            'account_id': '',
            'hardware_type': ''
        }

        # Parse venue details
        for line in venue_text.split('\n'):
            if '**Business Type**:' in line:
                venue_info['business_type'] = clean_value(line.split(':', 1)[1])
            elif '**Zone Count**:' in line:
                venue_info['zone_count'] = clean_value(line.split(':', 1)[1])
            elif '**Zone Names**:' in line:
                venue_info['zone_names'] = clean_value(line.split(':', 1)[1])
            elif '**Music Platform**:' in line:
                venue_info['music_platform'] = clean_value(line.split(':', 1)[1])
            elif '**Annual Price per Zone**:' in line:
                venue_info['annual_price'] = clean_value(line.split(':', 1)[1])
            elif '**Currency**:' in line:
                venue_info['currency'] = clean_value(line.split(':', 1)[1])
            elif '**Contract Start**:' in line:
                venue_info['contract_start'] = clean_value(line.split(':', 1)[1])
            elif '**Contract End**:' in line:
                venue_info['contract_end'] = clean_value(line.split(':', 1)[1])
            elif '**Hardware Type**:' in line:
                venue_info['hardware_type'] = clean_value(line.split(':', 1)[1])

        # Extract contacts
        contacts_section = False
        current_contact = None

        for line in venue_text.split('\n'):
            # Check if we're in the contacts section
            if '#### Contacts' in line:
                contacts_section = True
                continue
            elif '#### Issue History' in line or '#### Special Notes' in line:
                # End of contacts section
                if current_contact:
                    # Add the last contact
                    contact_record = venue_info.copy()
                    contact_record.update(current_contact)
                    all_contacts.append(contact_record)
                    current_contact = None
                contacts_section = False
                continue

            if contacts_section:
                # Check for contact role line (starts with "- **")
                role_match = re.match(r'- \*\*(.+?)\*\*: (.+)', line)
                if role_match:
                    # Save previous contact if exists
                    if current_contact:
                        contact_record = venue_info.copy()
                        contact_record.update(current_contact)
                        all_contacts.append(contact_record)

                    # Start new contact
                    role = role_match.group(1).strip()
                    name = clean_value(role_match.group(2))

                    current_contact = {
                        'contact_name': name,
                        'contact_role': role,
                        'contact_email': '',
                        'contact_phone': '',
                        'preferred_contact': '',
                        'notes': ''
                    }

                # Parse contact details (indented lines)
                elif current_contact and line.startswith('  '):
                    detail_line = line.strip()
                    if detail_line.startswith('- Email:'):
                        current_contact['contact_email'] = clean_value(detail_line.split(':', 1)[1])
                    elif detail_line.startswith('- Phone:'):
                        current_contact['contact_phone'] = clean_value(detail_line.split(':', 1)[1])
                    elif detail_line.startswith('- Preferred Contact:'):
                        current_contact['preferred_contact'] = clean_value(detail_line.split(':', 1)[1])
                    elif detail_line.startswith('- Notes:'):
                        current_contact['notes'] = clean_value(detail_line.split(':', 1)[1])

        # If no contacts were found, create a default one
        if not any(c['venue_name'] == venue_name for c in all_contacts):
            contact_record = venue_info.copy()
            contact_record.update({
                'contact_name': 'Manager',
                'contact_role': 'General Manager',
                'contact_email': '',
                'contact_phone': '',
                'preferred_contact': 'Email',
                'notes': 'Default contact - no specific contact information available'
            })
            all_contacts.append(contact_record)

    return all_contacts


def export_to_csv(contacts, output_file):
    """Export contacts to CSV file"""

    # Define CSV columns (ordered for easy import to CRM)
    fieldnames = [
        'venue_name',
        'contact_name',
        'contact_role',
        'contact_email',
        'contact_phone',
        'business_type',
        'zone_count',
        'zone_names',
        'contract_end',
        'music_platform',
        'annual_price',
        'currency',
        'contract_start',
        'hardware_type',
        'preferred_contact',
        'notes'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header
        writer.writeheader()

        # Write contacts
        for contact in contacts:
            # Ensure all fields exist
            row = {field: contact.get(field, '') for field in fieldnames}
            writer.writerow(row)

    print(f"✅ Exported {len(contacts)} contacts to {output_file}")

    # Print summary statistics
    venues = set(c['venue_name'] for c in contacts)
    emails = [c for c in contacts if c.get('contact_email')]
    phones = [c for c in contacts if c.get('contact_phone')]

    print(f"\n📊 Export Summary:")
    print(f"   - Total venues: {len(venues)}")
    print(f"   - Total contacts: {len(contacts)}")
    print(f"   - Contacts with email: {len(emails)}")
    print(f"   - Contacts with phone: {len(phones)}")

    # Business type breakdown
    business_types = {}
    for c in contacts:
        bt = c.get('business_type', 'Unknown')
        if bt and bt not in business_types:
            business_types[bt] = 0
        if bt:
            business_types[bt] += 1

    if business_types:
        print(f"\n📈 By Business Type:")
        for bt, count in sorted(business_types.items()):
            print(f"   - {bt}: {count} contacts")


def main():
    """Main function to export venues to CSV"""

    # Input and output files
    input_file = 'backend/venue_data.md'
    output_file = 'bma_social_contacts_export.csv'

    print(f"🚀 Starting export from {input_file}...")

    try:
        # Parse venue data
        contacts = parse_venue_data(input_file)

        # Export to CSV
        export_to_csv(contacts, output_file)

        print(f"\n✨ Export complete! You can now import '{output_file}' into Brevo.")
        print("\n📝 Import tips for Brevo:")
        print("   1. Go to Contacts > Import Contacts")
        print("   2. Upload the CSV file")
        print("   3. Map 'contact_email' to Email field")
        print("   4. Map 'venue_name' to Company field")
        print("   5. Map other fields as custom attributes")
        print("   6. Create segments based on 'business_type' for targeted campaigns")

    except FileNotFoundError:
        print(f"❌ Error: Could not find {input_file}")
        print("   Make sure you're running this from the project root directory")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()