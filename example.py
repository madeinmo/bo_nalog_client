#!/usr/bin/env python3
"""
Example usage of bo-nalog-client
"""

import asyncio
from bo_nalog_client import NalogClient


async def main():
    """Example of fetching financial data for an organization."""
    client = NalogClient()
    
    async with client:
        # Example organization ID
        org_id = 9392519
        
        try:
            year, revenue, profit = await client.get_last_year_revenue_profit(org_id)
            
            if year and revenue is not None and profit is not None:
                print(f"Organization ID: {org_id}")
                print(f"Year: {year}")
                print(f"Revenue: {revenue:,.2f}")
                print(f"Profit: {profit:,.2f}")
            else:
                print(f"No financial data found for organization {org_id}")
                
        except Exception as e:
            print(f"Error fetching data: {e}")


if __name__ == "__main__":
    asyncio.run(main())
