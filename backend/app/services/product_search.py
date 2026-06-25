"""Product search service — search and compare products across Chinese e-commerce platforms.

Strategy (MVP):
  When SEARCH_API_KEY is configured: Bing Search API → LLM parse → ProductLink
  When SEARCH_API_KEY is not configured: LLM directly generates product comparison
  based on market knowledge, with deep links to each platform's search page.
"""

import json
import logging
from typing import Optional

import httpx
from openai import OpenAI

from app.config import SEARCH_API_KEY, SEARCH_API_BASE, LLM_API_BASE, LLM_API_KEY, LLM_MODEL
from app.services.deep_link import DeepLinkGenerator

logger = logging.getLogger(__name__)

from app.feishu.card_builder import ProductLink


class ProductSearchService:
    """Search products on Chinese e-commerce sites and generate comparisons."""

    PLATFORM_CONFIG = {
        "taobao": {
            "search_prefix": "淘宝",
            "search_query_template": "{item_name} 淘宝 价格 购买",
        },
        "jd": {
            "search_prefix": "京东",
            "search_query_template": "{item_name} 京东 价格 购买",
        },
        "pdd": {
            "search_prefix": "拼多多",
            "search_query_template": "{item_name} 拼多多 价格 购买",
        },
    }

    # Prompt for LLM-based product comparison (no search API needed)
    LLM_COMPARE_PROMPT = """你是一个商品比价助手，熟悉中国主流电商平台（淘宝、京东、拼多多）的商品价格。

用户需要购买：{item_desc}

请根据你对市场的了解，为每个平台推荐1个最典型的商品，给出合理估算的价格。
价格应该是该平台上同品类同规格商品的常见价格区间中的典型值。

请严格按照以下JSON格式返回（不要添加任何其他内容、不要用markdown包裹）：
{{"products": [
  {{\"platform\": \"taobao\", \"name\": \"商品简称\", \"price\": 价格数字}},
  {{\"platform\": \"jd\", \"name\": \"商品简称\", \"price\": 价格数字}},
  {{\"platform\": \"pdd\", \"name\": \"商品简称\", \"price\": 价格数字}}
]}}

注意：
- platform 必须是 taobao/jd/pdd 三个值之一
- price 是数字（单位：元），不要加¥符号
- name 不要超过15个字
- 拼多多通常最便宜，京东品质好但价格稍高，淘宝中间档"""

    # Prompt for search result parsing (when search API is available)
    PARSE_PROMPT = """从以下搜索结果中提取商品信息。对每个平台，找出1-2个最相关的商品，提取：
- 商品名称（简短，不超过20字）
- 价格（数字，单位元）
- 商品页面URL

搜索结果：
{search_results}

请严格按照以下JSON格式返回（不要添加任何其他内容、不要用markdown包裹）：
{{"products": [
  {{\"platform\": \"taobao/jd/pdd\", \"name\": \"商品名\", \"price\": 59.9, \"url\": "https://..."}}
]}}

platform 必须是 taobao/jd/pdd 三个值之一。"""

    def __init__(self):
        self.search_api_key = SEARCH_API_KEY
        self.search_api_base = SEARCH_API_BASE
        self._llm_client = None
        self.llm_model = LLM_MODEL
        self.deep_link_gen = DeepLinkGenerator()

    @property
    def llm_client(self):
        """Lazy-initialize OpenAI client."""
        if self._llm_client is None:
            self._llm_client = OpenAI(base_url=LLM_API_BASE, api_key=LLM_API_KEY)
        return self._llm_client

    async def search(
        self,
        item_name: str,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
    ) -> list[ProductLink]:
        """Search for a product across all three platforms.

        If SEARCH_API_KEY is configured, uses Bing Search API + LLM parsing.
        Otherwise, uses LLM directly to generate comparison data.
        """
        qty_desc = ""
        if quantity and unit:
            qty_desc = f" {quantity}{unit}"

        if self.search_api_key:
            # Full search mode: Bing API → LLM parse
            return await self._search_via_api(item_name, qty_desc)
        else:
            # LLM-only mode: direct generation based on market knowledge
            return await self._search_via_llm(item_name, qty_desc)

    async def compare(
        self,
        item_name: str,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
    ) -> list[ProductLink]:
        """Alias for search()."""
        return await self.search(item_name, quantity, unit)

    async def _search_via_llm(
        self, item_name: str, qty_desc: str
    ) -> list[ProductLink]:
        """Generate product comparison using LLM's market knowledge.

        No external search API needed. The LLM estimates typical prices
        for each platform based on its knowledge of Chinese e-commerce.
        """
        item_desc = f"{item_name}{qty_desc}"
        prompt = self.LLM_COMPARE_PROMPT.format(item_desc=item_desc)

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是商品比价助手。只返回纯JSON，不要markdown格式。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content or ""
            # Clean up: strip markdown code block wrappers if present
            content = content.strip()
            if content.startswith("```"):
                # Remove ```json or ``` wrapper
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3].strip()

            data = json.loads(content)
            products_raw = data.get("products", [])
            logger.info(f"LLM generated {len(products_raw)} product comparisons for {item_name}")

            return self._raw_to_product_links(products_raw, item_name, qty_desc)

        except json.JSONDecodeError as e:
            logger.error(f"LLM JSON parsing failed: {e}, raw content: {content[:200]}")
            return self._fallback_products(item_name, qty_desc)
        except Exception as e:
            logger.error(f"LLM comparison failed: {e}")
            return self._fallback_products(item_name, qty_desc)

    async def _search_via_api(
        self, item_name: str, qty_desc: str
    ) -> list[ProductLink]:
        """Full search mode: Bing Search API → LLM parsing."""
        all_results = ""
        for platform, config in self.PLATFORM_CONFIG.items():
            query = config["search_query_template"].format(item_name=item_name) + qty_desc
            try:
                results = await self._search_api(query)
                all_results += f"\n=== {config['search_prefix']}搜索结果 ===\n{results}\n"
            except Exception as e:
                logger.warning(f"Search API failed for {platform}: {e}")
                all_results += f"\n=== {config['search_prefix']}搜索结果 ===\n（搜索失败）\n"

        if not all_results.strip():
            return self._fallback_products(item_name, qty_desc)

        products_raw = await self._parse_search_results(all_results, item_name)
        return self._raw_to_product_links(products_raw, item_name, qty_desc)

    def _raw_to_product_links(
        self, products_raw: list[dict], item_name: str, qty_desc: str
    ) -> list[ProductLink]:
        """Convert raw product dicts to ProductLink objects with deep links."""
        keyword = f"{item_name}{qty_desc}"
        product_links = []

        for p in products_raw:
            platform = p.get("platform", "")
            name = p.get("name", item_name)
            price = p.get("price", 0)
            url = p.get("url", "")

            deep_link = self.deep_link_gen.generate_search_link(platform, keyword)
            web_url = self.deep_link_gen.generate_web_fallback(platform, keyword)

            if url and url.startswith("http"):
                web_url = url

            product_links.append(ProductLink(
                platform=platform,
                product_name=name,
                price=price,
                url=deep_link,
                display_url=web_url,
            ))

        return product_links

    async def _parse_search_results(self, search_results: str, item_name: str) -> list[dict]:
        """Use LLM to parse Bing search results into structured product data."""
        prompt = self.PARSE_PROMPT.format(search_results=search_results)

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "你是商品信息提取助手。只返回纯JSON，不要markdown格式。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content or ""
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                if content.endswith("```"):
                    content = content[:-3].strip()

            data = json.loads(content)
            return data.get("products", [])
        except Exception as e:
            logger.error(f"LLM search parsing failed: {e}")
            return self._fallback_product_dicts(item_name)

    async def _search_api(self, query: str) -> str:
        """Call Bing Search API."""
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{self.search_api_base}/search",
                params={"q": query, "count": 10, "mkt": "zh-CN", "setLang": "zh-Hans"},
                headers={"Ocp-Apim-Subscription-Key": self.search_api_key},
            )
            response.raise_for_status()
            data = response.json()

        web_pages = data.get("webPages", {}).get("value", [])
        if not web_pages:
            return "无搜索结果"

        result_lines = []
        for page in web_pages[:8]:
            result_lines.append(f"标题: {page.get('name', '')}")
            result_lines.append(f"摘要: {page.get('snippet', '')}")
            result_lines.append(f"URL: {page.get('url', '')}")
            result_lines.append("")
        return "\n".join(result_lines)

    def _fallback_products(self, item_name: str, qty_desc: str) -> list[ProductLink]:
        """Generate fallback ProductLink objects with deep links only (no price data)."""
        keyword = f"{item_name}{qty_desc}"
        return [
            ProductLink(
                platform="taobao", product_name=f"{item_name}（淘宝搜索）", price=0,
                url=self.deep_link_gen.generate_search_link("taobao", keyword),
                display_url=self.deep_link_gen.generate_web_fallback("taobao", keyword),
            ),
            ProductLink(
                platform="jd", product_name=f"{item_name}（京东搜索）", price=0,
                url=self.deep_link_gen.generate_search_link("jd", keyword),
                display_url=self.deep_link_gen.generate_web_fallback("jd", keyword),
            ),
            ProductLink(
                platform="pdd", product_name=f"{item_name}（拼多多搜索）", price=0,
                url=self.deep_link_gen.generate_search_link("pdd", keyword),
                display_url=self.deep_link_gen.generate_web_fallback("pdd", keyword),
            ),
        ]

    def _fallback_product_dicts(self, item_name: str) -> list[dict]:
        """Generate fallback product dicts."""
        return [
            {"platform": "taobao", "name": item_name, "price": 0, "url": ""},
            {"platform": "jd", "name": item_name, "price": 0, "url": ""},
            {"platform": "pdd", "name": item_name, "price": 0, "url": ""},
        ]
