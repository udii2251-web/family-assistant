"""Deep link generator for Chinese e-commerce apps.

Generates platform-specific deep link URLs that open product search or
product detail pages directly in the Taobao / JD / Pinduoduo apps.
Each link also has a web fallback for users who don't have the app installed.
"""

import json
from urllib.parse import quote


class DeepLinkGenerator:
    """Generate deep link URLs for Chinese e-commerce apps.

    Deep link schemes:
    - Taobao: taobao://s.taobao.com/search?q={keyword} (search)
              taobao://item.taobao.com/item.htm?id={id} (product)
    - JD: openapp.jdmobile://virtual?params={json} (search and product)
    - PDD: pinduoduo://com.xunmeng.pinduoduo/search_result.html?search_key={keyword}
           pinduoduo://com.xunmeng.pinduoduo/goods.html?goods_id={goods_id}
    """

    @staticmethod
    def generate_search_link(platform: str, keyword: str) -> str:
        """Generate a deep link that opens the app's search page for the keyword."""
        encoded_keyword = quote(keyword)
        if platform == "taobao":
            return f"taobao://s.taobao.com/search?q={encoded_keyword}"
        elif platform == "jd":
            params = json.dumps({"category": "jump", "des": "search", "keyword": keyword})
            return f"openapp.jdmobile://virtual?params={quote(params)}"
        elif platform == "pdd":
            return f"pinduoduo://com.xunmeng.pinduoduo/search_result.html?search_key={encoded_keyword}"
        else:
            raise ValueError(f"Unknown platform: {platform}")

    @staticmethod
    def generate_product_link(platform: str, product_id: str) -> str:
        """Generate a deep link to a specific product page (if product ID is available)."""
        if platform == "taobao":
            return f"taobao://item.taobao.com/item.htm?id={product_id}"
        elif platform == "jd":
            params = json.dumps({"category": "jump", "des": "productDetail", "skuId": product_id})
            return f"openapp.jdmobile://virtual?params={quote(params)}"
        elif platform == "pdd":
            return f"pinduoduo://com.xunmeng.pinduoduo/goods.html?goods_id={product_id}"
        else:
            raise ValueError(f"Unknown platform: {platform}")

    @staticmethod
    def generate_web_fallback(platform: str, keyword: str) -> str:
        """Generate a regular web URL as fallback for users without the app."""
        encoded_keyword = quote(keyword)
        if platform == "taobao":
            return f"https://s.taobao.com/search?q={encoded_keyword}"
        elif platform == "jd":
            return f"https://search.jd.com/Search?keyword={encoded_keyword}"
        elif platform == "pdd":
            return f"https://mobile.yangkeduo.com/search_result.html?search_key={encoded_keyword}"
        else:
            raise ValueError(f"Unknown platform: {platform}")

    @staticmethod
    def generate_product_web_fallback(platform: str, product_id: str) -> str:
        """Generate a web URL for a specific product page."""
        if platform == "taobao":
            return f"https://item.taobao.com/item.htm?id={product_id}"
        elif platform == "jd":
            return f"https://item.jd.com/{product_id}.html"
        elif platform == "pdd":
            return f"https://mobile.yangkeduo.com/goods.html?goods_id={product_id}"
        else:
            raise ValueError(f"Unknown platform: {platform}")

    @staticmethod
    def get_platform_display_name(platform: str) -> str:
        """Get Chinese display name for a platform."""
        names = {"taobao": "淘宝", "jd": "京东", "pdd": "拼多多"}
        return names.get(platform, platform)
