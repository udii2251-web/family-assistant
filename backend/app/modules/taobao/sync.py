"""Taobao order synchronization module.

Handles:
- Visit "My Orders" page
- Extract last 7 days order data
- Field extraction: order_id, product_name, shop_name, price, order_time, status
- Data deduplication (already synced orders)
- Write to database (SQLite or Supabase)
- Scheduled task (weekly auto sync)
"""

# Placeholder — Session B will implement
pass