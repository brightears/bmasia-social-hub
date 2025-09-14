"""
Customer Data Manager for Campaign System
Handles customer (business) and venue (zone) relationships
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CustomerManager:
    """
    Manages customer data with proper hierarchy:
    - Customer: The business (e.g., Hilton Pattaya)
    - Brand: Corporate group (e.g., Hilton Hotels & Resorts)
    - Venues/Zones: Music zones within customer (e.g., Edge, Drift Bar)
    """

    def __init__(self):
        self.customers = {}
        self.brands = {}
        self.load_customer_data()

    def load_customer_data(self):
        """Load and parse customer data from venue_data.md"""
        try:
            # Try different paths to find venue_data.md
            import os
            possible_paths = [
                'venue_data.md',
                os.path.join(os.path.dirname(__file__), '..', 'venue_data.md'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'venue_data.md')
            ]

            content = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        content = f.read()
                        logger.info(f"Loaded venue_data.md from: {path}")
                        break

            if content is None:
                raise FileNotFoundError("venue_data.md not found in any expected location")

            # Parse customers from markdown
            customer_sections = re.split(r'\n### (?=\w)', content)

            for customer_section in customer_sections[1:]:  # Skip header
                lines = customer_section.strip().split('\n')
                if not lines:
                    continue

                customer_name = lines[0].strip()

                # Initialize customer object
                customer_info = {
                    'name': customer_name,
                    'customer_id': self._generate_id(customer_name),
                    'brand': self._extract_brand(customer_name),
                    'business_type': None,
                    'zones': [],  # These are the venues/music zones
                    'platform': None,
                    'contract_start': None,
                    'contract_end': None,
                    'annual_price_per_zone': None,
                    'currency': None,
                    'total_zones': 0,
                    'contacts': [],
                    'primary_contact': None,
                    'region': None,
                    'country': 'Thailand',  # Default, can be extracted
                    'city': self._extract_city(customer_name),
                    'tags': [],
                    'notes': [],
                    'account_id': None,
                    'hardware_type': None
                }

                # Parse customer details
                current_section = None
                for line in lines[1:]:
                    # Business type
                    if '**Business Type**:' in line:
                        customer_info['business_type'] = line.split(':', 1)[1].strip()

                    # Zones (venues within customer)
                    elif '**Zone Names**:' in line:
                        zones_text = line.split(':', 1)[1].strip()
                        customer_info['zones'] = [z.strip() for z in zones_text.split(',')]
                        customer_info['total_zones'] = len(customer_info['zones'])

                    # Platform
                    elif '**Music Platform**:' in line:
                        customer_info['platform'] = line.split(':', 1)[1].strip()

                    # Contract dates
                    elif '**Contract Start**:' in line:
                        customer_info['contract_start'] = line.split(':', 1)[1].strip()
                    elif '**Contract End**:' in line:
                        customer_info['contract_end'] = line.split(':', 1)[1].strip()

                    # Pricing
                    elif '**Annual Price per Zone**:' in line:
                        price_text = line.split(':', 1)[1].strip()
                        customer_info['annual_price_per_zone'] = price_text
                        # Extract currency
                        if 'THB' in price_text:
                            customer_info['currency'] = 'THB'
                        elif 'USD' in price_text:
                            customer_info['currency'] = 'USD'

                    # Account ID
                    elif '**Soundtrack Account ID**:' in line:
                        customer_info['account_id'] = line.split(':', 1)[1].strip()

                    # Hardware
                    elif '**Hardware Type**:' in line:
                        customer_info['hardware_type'] = line.split(':', 1)[1].strip()

                    # Contacts section
                    elif '#### Contacts' in line:
                        current_section = 'contacts'

                    # Parse contact entries
                    elif current_section == 'contacts' and '**' in line and ':' in line:
                        contact_role = line.split('**')[1].split('**')[0]
                        contact_name = line.split(':', 1)[1].strip()

                        contact = {
                            'role': contact_role,
                            'name': contact_name,
                            'email': None,
                            'phone': None,
                            'preferred_contact': None,
                            'notes': None
                        }

                        # Look for contact details in next few lines
                        contact_lines = []
                        line_index = lines.index(line)
                        for i in range(line_index + 1, min(line_index + 5, len(lines))):
                            if '**' in lines[i] and ':' in lines[i]:
                                break
                            contact_lines.append(lines[i])

                        for detail_line in contact_lines:
                            if 'Email:' in detail_line:
                                contact['email'] = detail_line.split(':', 1)[1].strip()
                            elif 'Phone:' in detail_line:
                                contact['phone'] = detail_line.split(':', 1)[1].strip()
                            elif 'Preferred Contact:' in detail_line:
                                contact['preferred_contact'] = detail_line.split(':', 1)[1].strip()
                            elif 'Notes:' in detail_line:
                                contact['notes'] = detail_line.split(':', 1)[1].strip()

                        customer_info['contacts'].append(contact)

                        # Set primary contact (first one or GM)
                        if not customer_info['primary_contact'] or 'General Manager' in contact_role:
                            customer_info['primary_contact'] = contact

                    # Special notes
                    elif '#### Special Notes' in line:
                        current_section = 'notes'
                    elif current_section == 'notes' and line.startswith('-'):
                        customer_info['notes'].append(line[1:].strip())

                # Determine region based on country
                customer_info['region'] = self._determine_region(customer_info['country'])

                # Add tags based on characteristics
                customer_info['tags'] = self._generate_tags(customer_info)

                # Store customer
                self.customers[customer_info['customer_id']] = customer_info

                # Track brand
                brand = customer_info['brand']
                if brand:
                    if brand not in self.brands:
                        self.brands[brand] = []
                    self.brands[brand].append(customer_info['customer_id'])

            logger.info(f"Loaded {len(self.customers)} customers from venue_data.md")
            logger.info(f"Identified {len(self.brands)} brands")

            # Debug: Log customer details
            for cid, customer in self.customers.items():
                logger.info(f"Customer: {customer['name']}, Type: {customer.get('business_type')}, Zones: {len(customer.get('zones', []))}")

        except FileNotFoundError as e:
            logger.error(f"venue_data.md not found - no customer data loaded: {e}")
            # Initialize empty to prevent crashes
            self.customers = {}
            self.brands = {}
        except Exception as e:
            logger.error(f"Error loading customer data: {e}")
            # Initialize empty to prevent crashes
            self.customers = {}
            self.brands = {}

    def filter_customers(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter customers based on criteria

        Filters can include:
        - brand: "Hilton Hotels & Resorts"
        - business_type: "Hotel"
        - region: "Asia Pacific"
        - country: "Thailand"
        - city: "Bangkok"
        - platform: "Soundtrack Your Brand"
        - contract_expiry: {"days": 30}  # Expires within 30 days
        - min_zones: 4
        - tags: ["premium", "long-term"]
        """
        filtered = []

        for customer_id, customer in self.customers.items():
            # Check each filter
            if filters.get('brand'):
                if customer['brand'] != filters['brand']:
                    continue

            if filters.get('business_type'):
                if customer['business_type'] != filters['business_type']:
                    continue

            if filters.get('region'):
                if customer['region'] != filters['region']:
                    continue

            if filters.get('country'):
                if customer['country'] != filters['country']:
                    continue

            if filters.get('city'):
                if customer['city'] != filters['city']:
                    continue

            if filters.get('platform'):
                if customer['platform'] != filters['platform']:
                    continue

            if filters.get('min_zones'):
                if customer['total_zones'] < filters['min_zones']:
                    continue

            if filters.get('contract_expiry'):
                expiry_filter = filters['contract_expiry']
                if 'days' in expiry_filter:
                    days = expiry_filter['days']
                    if not self._expires_within_days(customer['contract_end'], days):
                        continue
                elif 'month' in expiry_filter:
                    month = expiry_filter['month']
                    if not self._expires_in_month(customer['contract_end'], month):
                        continue

            if filters.get('tags'):
                required_tags = filters['tags']
                if not all(tag in customer['tags'] for tag in required_tags):
                    continue

            filtered.append(customer)

        logger.info(f"Filtered {len(filtered)} customers from {len(self.customers)} total")
        return filtered

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        return self.customers.get(customer_id)

    def get_customers_by_brand(self, brand: str) -> List[Dict[str, Any]]:
        """Get all customers of a specific brand"""
        customer_ids = self.brands.get(brand, [])
        return [self.customers[cid] for cid in customer_ids if cid in self.customers]

    def get_expiring_contracts(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get customers with contracts expiring within specified days"""
        return self.filter_customers({'contract_expiry': {'days': days}})

    def _generate_id(self, name: str) -> str:
        """Generate unique ID from customer name"""
        return name.lower().replace(' ', '_').replace('-', '_')

    def _extract_brand(self, customer_name: str) -> Optional[str]:
        """Extract brand from customer name"""
        # Common hotel brands
        brands = {
            'Hilton': 'Hilton Hotels & Resorts',
            'Marriott': 'Marriott International',
            'Hyatt': 'Hyatt Hotels Corporation',
            'InterContinental': 'IHG Hotels & Resorts',
            'Sheraton': 'Marriott International',
            'Westin': 'Marriott International',
            'Four Seasons': 'Four Seasons Hotels and Resorts',
            'Mandarin Oriental': 'Mandarin Oriental Hotel Group',
            'Centara': 'Centara Hotels & Resorts',
            'Dusit': 'Dusit International'
        }

        for brand_key, brand_name in brands.items():
            if brand_key in customer_name:
                return brand_name

        return None  # Independent

    def _extract_city(self, customer_name: str) -> Optional[str]:
        """Extract city from customer name"""
        # Common Thai cities
        cities = ['Bangkok', 'Pattaya', 'Phuket', 'Chiang Mai', 'Hua Hin',
                  'Krabi', 'Samui', 'Koh Samui', 'Khao Lak']

        for city in cities:
            if city in customer_name:
                return city

        return None

    def _determine_region(self, country: str) -> str:
        """Determine region from country"""
        regions = {
            'Thailand': 'Asia Pacific',
            'Singapore': 'Asia Pacific',
            'Malaysia': 'Asia Pacific',
            'Indonesia': 'Asia Pacific',
            'Philippines': 'Asia Pacific',
            'Vietnam': 'Asia Pacific',
            'Japan': 'Asia Pacific',
            'China': 'Asia Pacific',
            'USA': 'Americas',
            'Canada': 'Americas',
            'Mexico': 'Americas',
            'UK': 'Europe',
            'France': 'Europe',
            'Germany': 'Europe',
            'Spain': 'Europe'
        }

        return regions.get(country, 'Asia Pacific')  # Default to APAC

    def _generate_tags(self, customer: Dict[str, Any]) -> List[str]:
        """Generate tags based on customer characteristics"""
        tags = []

        # Size tags
        if customer['total_zones'] >= 10:
            tags.append('enterprise')
        elif customer['total_zones'] >= 4:
            tags.append('medium')
        else:
            tags.append('small')

        # Platform tags
        if customer['platform'] == 'Soundtrack Your Brand':
            tags.append('syb')
        elif customer['platform'] == 'Beat Breeze':
            tags.append('beat_breeze')

        # Business type tags
        if customer['business_type']:
            tags.append(customer['business_type'].lower())

        # Brand tags
        if customer['brand']:
            tags.append('chain')
        else:
            tags.append('independent')

        return tags

    def _expires_within_days(self, contract_end: str, days: int) -> bool:
        """Check if contract expires within specified days"""
        if not contract_end:
            return False

        try:
            # Parse contract end date
            end_date = datetime.strptime(contract_end, '%Y-%m-%d')
            days_until = (end_date - datetime.now()).days
            return 0 <= days_until <= days
        except:
            return False

    def _expires_in_month(self, contract_end: str, month: int) -> bool:
        """Check if contract expires in specific month"""
        if not contract_end:
            return False

        try:
            # Parse contract end date
            end_date = datetime.strptime(contract_end, '%Y-%m-%d')
            return end_date.month == month
        except:
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get customer base statistics"""
        stats = {
            'total_customers': len(self.customers),
            'total_brands': len(self.brands),
            'total_zones': sum(c['total_zones'] for c in self.customers.values()),
            'by_platform': {},
            'by_business_type': {},
            'by_region': {},
            'expiring_30_days': len(self.get_expiring_contracts(30)),
            'expiring_60_days': len(self.get_expiring_contracts(60)),
            'expiring_90_days': len(self.get_expiring_contracts(90))
        }

        # Count by platform
        for customer in self.customers.values():
            platform = customer['platform'] or 'Unknown'
            stats['by_platform'][platform] = stats['by_platform'].get(platform, 0) + 1

            # Count by business type
            biz_type = customer['business_type'] or 'Unknown'
            stats['by_business_type'][biz_type] = stats['by_business_type'].get(biz_type, 0) + 1

            # Count by region
            region = customer['region'] or 'Unknown'
            stats['by_region'][region] = stats['by_region'].get(region, 0) + 1

        return stats