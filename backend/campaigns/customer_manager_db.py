"""
Database-Powered Customer Manager for Campaign System
Replaces the file-based approach with high-performance PostgreSQL queries
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncpg
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class DatabaseCustomerManager:
    """
    Manages customer data through PostgreSQL instead of venue_data.md
    Provides high-performance filtering and pagination
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.pool = None
        self._initialized = False

    async def initialize(self):
        """Create connection pool"""
        if self._initialized:
            return

        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            self._initialized = True
            logger.info("Database customer manager initialized")

            # Get statistics
            stats = await self.get_statistics()
            logger.info(f"Loaded {stats['total_customers']} venues from database")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

    async def get_statistics(self) -> Dict[str, int]:
        """Get customer statistics"""
        async with self.pool.acquire() as conn:
            stats = {}

            # Total venues
            stats['total_customers'] = await conn.fetchval(
                "SELECT COUNT(*) FROM venues WHERE is_active = TRUE"
            )

            # By platform
            platform_stats = await conn.fetch("""
                SELECT platform, COUNT(*) as count
                FROM venues
                WHERE is_active = TRUE AND platform IS NOT NULL
                GROUP BY platform
            """)
            for row in platform_stats:
                stats[f'platform_{row["platform"]}'] = row['count']

            # By business type
            type_stats = await conn.fetch("""
                SELECT business_type, COUNT(*) as count
                FROM venues
                WHERE is_active = TRUE AND business_type IS NOT NULL
                GROUP BY business_type
            """)
            for row in type_stats:
                stats[f'type_{row["business_type"]}'] = row['count']

            # Expiring contracts
            stats['expiring_30_days'] = await conn.fetchval("""
                SELECT COUNT(*)
                FROM venues
                WHERE is_active = TRUE
                AND contract_end BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
            """)

            stats['expiring_90_days'] = await conn.fetchval("""
                SELECT COUNT(*)
                FROM venues
                WHERE is_active = TRUE
                AND contract_end BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '90 days'
            """)

            # Total zones
            stats['total_zones'] = await conn.fetchval(
                "SELECT COUNT(*) FROM zones WHERE status = 'active'"
            )

            # Contacts
            stats['total_contacts'] = await conn.fetchval(
                "SELECT COUNT(*) FROM contacts"
            )

            return stats

    async def filter_customers(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """
        Filter customers based on criteria

        Args:
            filters: Filtering criteria
                - business_type: Hotel, Restaurant, etc.
                - platform: SYB, Beat Breeze, BMS
                - contract_expiring_days: Number of days until expiry
                - min_zones: Minimum number of zones
                - max_zones: Maximum number of zones
                - search: Text search in venue name
                - brand: Brand name pattern (e.g., "Hilton%")

            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            Tuple of (customers list, total count)
        """
        async with self.pool.acquire() as conn:
            # Build WHERE clause
            where_clauses = ["v.is_active = TRUE"]
            params = []
            param_count = 0

            # Business type filter - single or multiple
            if filters.get('business_type'):
                param_count += 1
                where_clauses.append(f"v.business_type = ${param_count}")
                params.append(filters['business_type'])
            elif filters.get('business_types'):  # Handle multiple business types
                # Create IN clause for multiple business types
                placeholders = []
                for business_type in filters['business_types']:
                    param_count += 1
                    placeholders.append(f"${param_count}")
                    params.append(business_type)
                where_clauses.append(f"v.business_type IN ({', '.join(placeholders)})")

            # Platform filter
            if filters.get('platform'):
                param_count += 1
                where_clauses.append(f"v.platform = ${param_count}")
                params.append(filters['platform'])

            # Contract expiring filter
            if filters.get('contract_expiring_days'):
                where_clauses.append(
                    f"v.contract_end BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '{filters['contract_expiring_days']} days'"
                )

            # Zone count filters
            if filters.get('min_zones'):
                param_count += 1
                where_clauses.append(f"v.zone_count >= ${param_count}")
                params.append(filters['min_zones'])

            if filters.get('max_zones'):
                param_count += 1
                where_clauses.append(f"v.zone_count <= ${param_count}")
                params.append(filters['max_zones'])

            # Text search
            if filters.get('search'):
                param_count += 1
                where_clauses.append(f"v.name ILIKE ${param_count}")
                params.append(f"%{filters['search']}%")

            # Brand filter (pattern match)
            if filters.get('brand'):
                param_count += 1
                where_clauses.append(f"v.name ILIKE ${param_count}")
                params.append(f"%{filters['brand']}%")

            # Region/country filters (assuming we add these fields)
            if filters.get('country'):
                param_count += 1
                where_clauses.append(f"v.country = ${param_count}")
                params.append(filters['country'])

            where_clause = " AND ".join(where_clauses)

            # Get total count
            count_query = f"""
                SELECT COUNT(*)
                FROM venues v
                WHERE {where_clause}
            """
            total_count = await conn.fetchval(count_query, *params)

            # Get paginated results with zones and contacts
            param_count += 1
            limit_param = param_count
            params.append(limit)

            param_count += 1
            offset_param = param_count
            params.append(offset)

            query = f"""
                SELECT
                    v.id,
                    v.name,
                    v.business_type,
                    v.platform,
                    v.zone_count,
                    v.annual_price_per_zone,
                    v.currency,
                    v.contract_start,
                    v.contract_end,
                    v.soundtrack_account_id,
                    v.hardware_type,
                    v.special_notes,
                    -- Get zones as array
                    COALESCE(
                        array_agg(
                            DISTINCT z.name
                            ORDER BY z.name
                        ) FILTER (WHERE z.name IS NOT NULL),
                        ARRAY[]::text[]
                    ) as zones,
                    -- Get primary contact
                    (
                        SELECT json_build_object(
                            'name', c.name,
                            'email', c.email,
                            'phone', c.phone,
                            'role', c.role
                        )
                        FROM contacts c
                        WHERE c.venue_id = v.id AND c.is_primary = TRUE
                        LIMIT 1
                    ) as primary_contact,
                    -- Count total contacts
                    (
                        SELECT COUNT(*)
                        FROM contacts c
                        WHERE c.venue_id = v.id
                    ) as contact_count
                FROM venues v
                LEFT JOIN zones z ON v.id = z.venue_id AND z.status = 'active'
                WHERE {where_clause}
                GROUP BY v.id
                ORDER BY v.name
                LIMIT ${limit_param} OFFSET ${offset_param}
            """

            rows = await conn.fetch(query, *params)

            # Convert to customer format
            customers = []
            for row in rows:
                customer = {
                    'customer_id': f"venue_{row['id']}",
                    'name': row['name'],
                    'business_type': row['business_type'],
                    'platform': row['platform'],
                    'zones': list(row['zones']),
                    'zone_count': row['zone_count'],
                    'annual_price': float(row['annual_price_per_zone']) if row['annual_price_per_zone'] else None,
                    'currency': row['currency'],
                    'contract_start': row['contract_start'].isoformat() if row['contract_start'] else None,
                    'contract_end': row['contract_end'].isoformat() if row['contract_end'] else None,
                    'primary_contact': row['primary_contact'],
                    'contact_count': row['contact_count'],
                    'venue_id': row['id']  # Keep original ID for reference
                }

                # Calculate days until expiry
                if row['contract_end']:
                    days_until = (row['contract_end'] - datetime.now().date()).days
                    customer['days_until_expiry'] = days_until

                customers.append(customer)

            return customers, total_count

    async def get_customer_by_id(self, customer_id: str) -> Optional[Dict]:
        """Get single customer by ID"""
        # Extract venue ID from customer_id (format: "venue_123")
        if customer_id.startswith('venue_'):
            venue_id = int(customer_id.replace('venue_', ''))
        else:
            venue_id = int(customer_id)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    v.*,
                    array_agg(DISTINCT z.name ORDER BY z.name) as zones,
                    json_agg(
                        DISTINCT jsonb_build_object(
                            'id', c.id,
                            'name', c.name,
                            'email', c.email,
                            'phone', c.phone,
                            'role', c.role,
                            'is_primary', c.is_primary
                        )
                    ) FILTER (WHERE c.id IS NOT NULL) as contacts
                FROM venues v
                LEFT JOIN zones z ON v.id = z.venue_id AND z.status = 'active'
                LEFT JOIN contacts c ON v.id = c.venue_id
                WHERE v.id = $1 AND v.is_active = TRUE
                GROUP BY v.id
            """, venue_id)

            if not row:
                return None

            return self._format_customer(row)

    async def get_customers_by_brand(self, brand_pattern: str) -> List[Dict]:
        """Get all customers matching a brand pattern"""
        customers, _ = await self.filter_customers(
            {'brand': brand_pattern},
            limit=1000  # Get all for a brand
        )
        return customers

    async def get_expiring_customers(self, days: int = 30) -> List[Dict]:
        """Get customers with contracts expiring soon"""
        customers, _ = await self.filter_customers(
            {'contract_expiring_days': days},
            limit=1000
        )
        return customers

    async def search_customers(self, search_term: str, limit: int = 20) -> List[Dict]:
        """Quick search for customers by name"""
        customers, _ = await self.filter_customers(
            {'search': search_term},
            limit=limit
        )
        return customers

    async def get_customer_contacts(self, venue_id: int) -> List[Dict]:
        """Get all contacts for a venue"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id, name, email, phone, role,
                    is_primary, notes
                FROM contacts
                WHERE venue_id = $1
                ORDER BY is_primary DESC, role
            """, venue_id)

            return [dict(row) for row in rows]

    async def get_brand_list(self) -> List[Tuple[str, int]]:
        """Extract unique brand patterns from venue names"""
        async with self.pool.acquire() as conn:
            # Get common prefixes (first word of multi-property chains)
            rows = await conn.fetch("""
                WITH brand_patterns AS (
                    SELECT
                        CASE
                            WHEN name LIKE 'Hilton%' THEN 'Hilton'
                            WHEN name LIKE 'Marriott%' THEN 'Marriott'
                            WHEN name LIKE 'Centara%' THEN 'Centara'
                            WHEN name LIKE 'Anantara%' THEN 'Anantara'
                            WHEN name LIKE 'DoubleTree%' THEN 'DoubleTree'
                            WHEN name LIKE 'Sheraton%' THEN 'Sheraton'
                            WHEN name LIKE 'Novotel%' THEN 'Novotel'
                            WHEN name LIKE 'Ibis%' THEN 'Ibis'
                            WHEN name LIKE 'Pullman%' THEN 'Pullman'
                            WHEN name LIKE 'Holiday Inn%' THEN 'Holiday Inn'
                            WHEN name LIKE 'Conrad%' THEN 'Conrad'
                            ELSE NULL
                        END as brand,
                        name
                    FROM venues
                    WHERE is_active = TRUE
                )
                SELECT brand, COUNT(*) as count
                FROM brand_patterns
                WHERE brand IS NOT NULL
                GROUP BY brand
                ORDER BY count DESC, brand
            """)

            return [(row['brand'], row['count']) for row in rows]

    def _format_customer(self, row) -> Dict:
        """Format database row into customer object"""
        return {
            'customer_id': f"venue_{row['id']}",
            'venue_id': row['id'],
            'name': row['name'],
            'business_type': row.get('business_type'),
            'platform': row.get('platform'),
            'zones': list(row.get('zones', [])) if row.get('zones') else [],
            'zone_count': row.get('zone_count', 0),
            'contacts': row.get('contacts', []),
            'annual_price': float(row['annual_price_per_zone']) if row.get('annual_price_per_zone') else None,
            'currency': row.get('currency'),
            'contract_start': row['contract_start'].isoformat() if row.get('contract_start') else None,
            'contract_end': row['contract_end'].isoformat() if row.get('contract_end') else None,
        }


# Singleton instance
_manager_instance = None


async def get_customer_manager() -> DatabaseCustomerManager:
    """Get or create the customer manager singleton"""
    global _manager_instance

    if not _manager_instance:
        _manager_instance = DatabaseCustomerManager()
        await _manager_instance.initialize()

    return _manager_instance