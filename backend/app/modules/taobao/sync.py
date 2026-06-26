"""Taobao order synchronization module.

Handles:
- Visit "My Orders" page
- Extract last 7 days order data
- Field extraction: order_id, product_name, shop_name, price, order_time, status
- Data deduplication (already synced orders)
- Write to database (SQLite)
- Scheduled task (weekly auto sync)
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.shared.database import SessionLocal
from app.modules.taobao.models import TaobaoOrder, TaobaoOrderItem
from app.modules.taobao.playwright_manager import playwright_manager
from app.modules.taobao.auth import taobao_auth_manager

logger = logging.getLogger(__name__)


class TaobaoSyncManager:
    """Manages Taobao order synchronization.

    Features:
    - Fetch orders from Taobao website
    - Parse order data
    - Deduplicate orders
    - Store to database
    - Sync last 7 days by default
    """

    # 订单状态映射
    ORDER_STATUS_MAP = {
        '待付款': 'pending_payment',
        '待发货': 'pending_shipment',
        '已发货': 'shipped',
        '已签收': 'received',
        '已完成': 'completed',
        '交易关闭': 'closed',
        '退款中': 'refunding',
    }

    def __init__(self):
        """Initialize sync manager."""
        self._last_sync_time = None
        self._sync_in_progress = False

    async def sync_orders(self, days: int = 7, force: bool = False) -> dict:
        """Sync Taobao orders from last N days.

        Args:
            days: Number of days to sync (default 7)
            force: Force sync even if already synced today

        Returns:
            dict: {
                'success': bool,
                'total_orders': int,
                'new_orders': int,
                'updated_orders': int,
                'message': str,
                'orders': list
            }
        """
        # Prevent concurrent sync
        if self._sync_in_progress:
            return {
                'success': False,
                'message': '订单同步正在进行中，请稍后再试',
                'total_orders': 0,
                'new_orders': 0,
                'updated_orders': 0,
                'orders': []
            }

        self._sync_in_progress = True

        try:
            # Check login status
            login_status = await taobao_auth_manager.check_login_status()

            if not login_status['is_logged_in'] or login_status['needs_reauth']:
                return {
                    'success': False,
                    'message': '淘宝账号未登录或登录已失效，请先登录',
                    'total_orders': 0,
                    'new_orders': 0,
                    'updated_orders': 0,
                    'orders': []
                }

            # Initialize browser if needed
            if not playwright_manager._initialized:
                await playwright_manager.initialize(headless=True)

            # Navigate to orders page
            page = await playwright_manager.goto_orders_page()

            # Wait for page load
            await page.wait_for_load_state('networkidle')

            # Extract orders
            orders = await self._extract_orders(page, days)

            if not orders:
                return {
                    'success': True,
                    'message': '未找到订单数据',
                    'total_orders': 0,
                    'new_orders': 0,
                    'updated_orders': 0,
                    'orders': []
                }

            # Save to database
            new_count, updated_count = await self._save_orders(orders)

            self._last_sync_time = datetime.now()

            return {
                'success': True,
                'message': f'同步成功，共{len(orders)}个订单，新增{new_count}个，更新{updated_count}个',
                'total_orders': len(orders),
                'new_orders': new_count,
                'updated_orders': updated_count,
                'orders': orders
            }

        except Exception as e:
            logger.error(f"Order sync failed: {e}")
            return {
                'success': False,
                'message': f'订单同步失败: {str(e)}',
                'total_orders': 0,
                'new_orders': 0,
                'updated_orders': 0,
                'orders': []
            }

        finally:
            self._sync_in_progress = False

    async def _extract_orders(self, page, days: int) -> List[Dict]:
        """Extract order data from orders page.

        Args:
            page: Playwright page object
            days: Number of days to extract

        Returns:
            List of order dictionaries
        """
        orders = []
        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            # Wait for order list to load
            await page.wait_for_selector('.order-list, .bought-wrapper', timeout=10000)

            # Get all order items
            order_elements = await page.query_selector_all('.order-item, .bought-table-mod__table___2pVsn')

            logger.info(f"Found {len(order_elements)} order elements")

            for order_elem in order_elements:
                try:
                    order_data = await self._parse_order_element(order_elem, cutoff_date)

                    if order_data:
                        orders.append(order_data)
                        logger.info(f"Parsed order: {order_data.get('order_id')}")

                except Exception as e:
                    logger.warning(f"Failed to parse order element: {e}")
                    continue

            return orders

        except Exception as e:
            logger.error(f"Failed to extract orders: {e}")
            return []

    async def _parse_order_element(self, order_elem, cutoff_date: datetime) -> Optional[Dict]:
        """Parse a single order element.

        Args:
            order_elem: Playwright element
            cutoff_date: Only parse orders after this date

        Returns:
            Order dictionary or None if invalid/expired
        """
        try:
            # Extract order ID
            order_id_elem = await order_elem.query_selector('.order-number, .bought-table-mod__cell___3jVSp')
            if not order_id_elem:
                return None

            order_id_text = await order_id_elem.text_content()
            order_id_match = re.search(r'\d{15,20}', order_id_text)
            if not order_id_match:
                return None

            order_id = order_id_match.group(0)

            # Extract order time
            order_time_elem = await order_elem.query_selector('.order-time, .bought-table-mod__create-time___3BWQW')
            order_time_str = await order_time_elem.text_content() if order_time_elem else ''

            # Parse order time
            order_time = self._parse_order_time(order_time_str)

            # Skip if order is too old
            if order_time and order_time < cutoff_date:
                return None

            # Extract product name
            product_elem = await order_elem.query_selector('.product-name, .bought-table-mod__title___2WZpE')
            product_name = await product_elem.text_content() if product_elem else ''

            # Extract shop name
            shop_elem = await order_elem.query_selector('.shop-name, .bought-table-mod__seller___2dNCC')
            shop_name = await shop_elem.text_content() if shop_elem else ''

            # Extract price
            price_elem = await order_elem.query_selector('.order-price, .bought-table-mod__price___3pPvM')
            price_text = await price_elem.text_content() if price_elem else '0'
            price = self._parse_price(price_text)

            # Extract status
            status_elem = await order_elem.query_selector('.order-status, .bought-table-mod__status___3_yhl')
            status_text = await status_elem.text_content() if status_elem else ''
            status = self.ORDER_STATUS_MAP.get(status_text.strip(), status_text.strip())

            return {
                'order_id': order_id,
                'product_name': product_name.strip(),
                'shop_name': shop_name.strip(),
                'total_price': price,
                'order_time': order_time,
                'status': status
            }

        except Exception as e:
            logger.error(f"Error parsing order element: {e}")
            return None

    def _parse_order_time(self, time_str: str) -> Optional[datetime]:
        """Parse order time string to datetime.

        Args:
            time_str: Time string from webpage

        Returns:
            datetime object or None
        """
        try:
            # Common formats
            formats = [
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y/%m/%d %H:%M:%S',
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(time_str.strip(), fmt)
                except ValueError:
                    continue

            # Try relative time (e.g., "刚刚", "1小时前")
            if '刚刚' in time_str or '分钟前' in time_str:
                return datetime.now()
            elif '小时前' in time_str:
                hours = int(re.search(r'\d+', time_str).group(0))
                return datetime.now() - timedelta(hours=hours)
            elif '天前' in time_str:
                days = int(re.search(r'\d+', time_str).group(0))
                return datetime.now() - timedelta(days=days)

            return None

        except Exception as e:
            logger.warning(f"Failed to parse time '{time_str}': {e}")
            return None

    def _parse_price(self, price_text: str) -> float:
        """Parse price string to float.

        Args:
            price_text: Price text (e.g., "¥99.00", "99.00元")

        Returns:
            Float price value
        """
        try:
            # Remove currency symbols
            price_text = re.sub(r'[¥￥元$,，]', '', price_text)
            return float(price_text.strip())
        except:
            return 0.0

    async def _save_orders(self, orders: List[Dict]) -> tuple:
        """Save orders to database.

        Args:
            orders: List of order dictionaries

        Returns:
            Tuple of (new_count, updated_count)
        """
        db = SessionLocal()
        new_count = 0
        updated_count = 0

        try:
            for order_data in orders:
                # Check if order already exists
                existing_order = db.query(TaobaoOrder).filter(
                    TaobaoOrder.order_id == order_data['order_id']
                ).first()

                if existing_order:
                    # Update existing order
                    existing_order.product_name = order_data.get('product_name', '')
                    existing_order.shop_name = order_data.get('shop_name', '')
                    existing_order.total_price = order_data.get('total_price', 0.0)
                    existing_order.order_time = order_data.get('order_time')
                    existing_order.status = order_data.get('status', '')
                    existing_order.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # Create new order
                    new_order = TaobaoOrder(
                        order_id=order_data['order_id'],
                        product_name=order_data.get('product_name', ''),
                        shop_name=order_data.get('shop_name', ''),
                        total_price=order_data.get('total_price', 0.0),
                        order_time=order_data.get('order_time'),
                        status=order_data.get('status', ''),
                        synced_at=datetime.now()
                    )
                    db.add(new_order)
                    new_count += 1

            db.commit()
            logger.info(f"Saved {new_count} new orders, updated {updated_count} orders")

        except Exception as e:
            logger.error(f"Failed to save orders: {e}")
            db.rollback()
        finally:
            db.close()

        return new_count, updated_count

    def get_orders_from_db(
        self,
        days: int = None,
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query orders from database.

        Args:
            days: Filter by last N days
            status: Filter by status
            limit: Max number of orders to return

        Returns:
            List of order dictionaries
        """
        db = SessionLocal()
        try:
            query = db.query(TaobaoOrder)

            # Filter by time
            if days:
                cutoff_date = datetime.now() - timedelta(days=days)
                query = query.filter(TaobaoOrder.order_time >= cutoff_date)

            # Filter by status
            if status:
                query = query.filter(TaobaoOrder.status == status)

            # Order by time descending
            query = query.order_by(TaobaoOrder.order_time.desc())

            # Limit
            orders = query.limit(limit).all()

            # Convert to dict
            return [
                {
                    'order_id': order.order_id,
                    'product_name': order.product_name,
                    'shop_name': order.shop_name,
                    'total_price': order.total_price,
                    'order_time': order.order_time.isoformat() if order.order_time else None,
                    'status': order.status,
                    'synced_at': order.synced_at.isoformat() if order.synced_at else None
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"Failed to query orders: {e}")
            return []
        finally:
            db.close()


# Global instance
taobao_sync_manager = TaobaoSyncManager()