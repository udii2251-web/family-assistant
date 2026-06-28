"""Migration wrapper for CardBuilder.

This module provides backward-compatible CardBuilder methods that use the new
UniversalCardRenderer internally. Existing code can continue using CardBuilder
while gradually migrating to UniversalCardRenderer.

Migration Path:
1. CardBuilder methods now delegate to UniversalCardRenderer
2. Return values are still Feishu JSON (via convert_universal_to_feishu)
3. New code should use UniversalCardRenderer directly
4. Eventually, CardBuilder will be deprecated
"""

from typing import List, Optional
from datetime import datetime

from app.services.universal_card import (
    UniversalCardRenderer,
    ProductInfo,
    AlertLevel,
)
from app.feishu.card_adapter import convert_universal_to_feishu


# Keep ProductLink for backward compatibility
class ProductLink:
    """Deprecated: Use ProductInfo instead.

    Kept for backward compatibility with existing code.
    """
    def __init__(
        self,
        platform: str,
        product_name: str,
        price: float,
        url: str,
        display_url: str,
        image_url: Optional[str] = None,
    ):
        self.platform = platform
        self.product_name = product_name
        self.price = price
        self.url = url
        self.display_url = display_url
        self.image_url = image_url

    def to_product_info(self) -> ProductInfo:
        """Convert to ProductInfo."""
        return ProductInfo(
            platform=self.platform,
            product_name=self.product_name,
            price=self.price,
            deep_link=self.url,
            web_url=self.display_url,
            image_url=self.image_url,
        )


class CardBuilder:
    """Backward-compatible card builder using UniversalCardRenderer.

    DEPRECATED: New code should use UniversalCardRenderer directly.

    This class provides the same interface as the original CardBuilder but
    internally uses UniversalCardRenderer + convert_universal_to_feishu.
    """

    @staticmethod
    def restock_alert_card(
        item_name: str,
        remaining: float,
        unit: str,
        days_until_empty: int,
        suggested_quantity: float,
        products: list,
        alert_id: int,
    ) -> dict:
        """Build a restock alert card with product comparison and buy buttons.

        DEPRECATED: Use UniversalCardRenderer.restock_alert_card instead.

        Args:
            item_name: Name of the item
            remaining: Current stock amount
            unit: Unit of measurement
            days_until_empty: Days until stock runs out
            suggested_quantity: Suggested purchase amount
            products: List of ProductLink objects
            alert_id: Alert ID for callback tracking

        Returns:
            Feishu card JSON dict
        """
        # Convert ProductLink to ProductInfo
        product_infos = []
        if products:
            # Find cheapest price
            prices = [p.price for p in products if p.price > 0]
            cheapest_price = min(prices) if prices else 0

            for p in products:
                # Handle both ProductLink and dict
                if isinstance(p, ProductLink):
                    product_info = p.to_product_info()
                elif isinstance(p, dict):
                    product_info = ProductInfo(
                        platform=p.get("platform", ""),
                        product_name=p.get("product_name", ""),
                        price=p.get("price", 0),
                        deep_link=p.get("url", ""),
                        web_url=p.get("display_url", ""),
                        image_url=p.get("image_url"),
                        is_best_price=(p.get("price", 0) == cheapest_price and p.get("price", 0) > 0),
                    )
                else:
                    continue

                product_info.is_best_price = (p.price == cheapest_price and p.price > 0)
                product_infos.append(product_info)

        # Build universal card
        universal_card = UniversalCardRenderer.restock_alert_card(
            item_name=item_name,
            remaining=remaining,
            unit=unit,
            days_until_empty=days_until_empty,
            suggested_quantity=suggested_quantity,
            products=product_infos,
            alert_id=alert_id,
        )

        # Convert to Feishu format
        return convert_universal_to_feishu(universal_card)

    @staticmethod
    def inventory_summary_card(items: list[dict]) -> dict:
        """Build a summary card showing inventory overview.

        DEPRECATED: Use UniversalCardRenderer.inventory_summary_card instead.

        Args:
            items: List of dicts with keys: name, remaining, unit, days_until_empty

        Returns:
            Feishu card JSON dict
        """
        universal_card = UniversalCardRenderer.inventory_summary_card(items)
        return convert_universal_to_feishu(universal_card)

    @staticmethod
    def simple_text_card(title: str, content: str, template: str = "blue") -> dict:
        """Build a simple card with title and text content.

        DEPRECATED: Use UniversalCardRenderer.simple_text_card instead.

        Args:
            title: Card title
            content: Text content (markdown supported)
            template: Header template color (blue/red/green/orange)

        Returns:
            Feishu card JSON dict
        """
        # Map template string to AlertLevel
        template_to_level = {
            "blue": AlertLevel.INFO,
            "red": AlertLevel.ERROR,
            "green": AlertLevel.SUCCESS,
            "orange": AlertLevel.WARNING,
        }
        alert_level = template_to_level.get(template, AlertLevel.INFO)

        universal_card = UniversalCardRenderer.simple_text_card(
            title=title,
            content=content,
            alert_level=alert_level,
        )
        return convert_universal_to_feishu(universal_card)