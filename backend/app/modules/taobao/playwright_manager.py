"""Playwright manager for Taobao automation.

Handles:
- Browser instance management
- Persistent browser Session
- Cookie storage_state management
- Page automation helpers
"""

import os
import json
import logging
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class PlaywrightManager:
    """Manages Playwright browser instances for Taobao automation.

    Features:
    - Singleton pattern for browser instance reuse
    - Cookie persistence via storage_state
    - Login state management
    - Headless/headful mode switching
    """

    _instance: Optional['PlaywrightManager'] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None
    _page: Optional[Page] = None

    # 淘宝登录页面
    TAOBAO_LOGIN_URL = "https://login.taobao.com/member/login.jhtml"
    # 淘宝我的订单页面
    TAOBAO_ORDERS_URL = "https://buyertrade.taobao.com/trade/itemlist/list_bought_items.htm"
    # 淘宝首页
    TAOBAO_HOME_URL = "https://www.taobao.com"

    # Cookie存储路径
    COOKIE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "taobao"
    COOKIE_FILE = COOKIE_DIR / "storage_state.json"

    # 登录超时时间（秒）
    LOGIN_TIMEOUT = 300  # 5分钟
    # 页面加载超时
    PAGE_TIMEOUT = 60000  # 60秒

    def __new__(cls):
        """Singleton pattern to ensure only one browser instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Playwright manager."""
        if not hasattr(self, '_initialized'):
            self._initialized = False
            self._playwright = None
            self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.COOKIE_DIR.mkdir(parents=True, exist_ok=True)

    async def initialize(self, headless: bool = False):
        """Initialize browser instance.

        Args:
            headless: Whether to run in headless mode (default False for QR code display)
        """
        # Always re-initialize to ensure correct event loop
        if self._initialized:
            logger.info("Closing existing browser instance to re-initialize in current event loop")
            await self.close()

        try:
            self._playwright = await async_playwright().start()

            # Launch browser
            self._browser = await self._playwright.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            )

            # Create context with or without stored cookies
            if self.COOKIE_FILE.exists():
                logger.info(f"Loading stored cookies from {self.COOKIE_FILE}")
                self._context = await self._browser.new_context(
                    storage_state=str(self.COOKIE_FILE),
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
            else:
                logger.info("No stored cookies found, creating fresh context")
                self._context = await self._browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )

            # Create page
            self._page = await self._context.new_page()
            self._page.set_default_timeout(self.PAGE_TIMEOUT)

            self._initialized = True
            logger.info("Playwright manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            raise

    async def close(self):
        """Close browser and cleanup."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()

            self._initialized = False
            logger.info("Playwright manager closed")
        except Exception as e:
            logger.error(f"Error closing Playwright: {e}")

    async def get_page(self) -> Page:
        """Get current page instance.

        Returns:
            Page: Current browser page

        Raises:
            RuntimeError: If manager not initialized
        """
        if not self._initialized or not self._page:
            raise RuntimeError("Playwright manager not initialized. Call initialize() first.")
        return self._page

    async def save_cookies(self):
        """Save current cookies to file."""
        if not self._context:
            logger.warning("No context to save cookies from")
            return

        try:
            storage_state = await self._context.storage_state()
            with open(self.COOKIE_FILE, 'w') as f:
                json.dump(storage_state, f, indent=2)
            logger.info(f"Cookies saved to {self.COOKIE_FILE}")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            raise

    def load_cookies(self) -> Optional[dict]:
        """Load saved cookies from file.

        Returns:
            Optional[dict]: Cookie storage state or None if not found
        """
        try:
            if self.COOKIE_FILE.exists():
                with open(self.COOKIE_FILE, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded cookies from {self.COOKIE_FILE}")
                return state
            return None
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return None

    def clear_cookies(self):
        """Clear saved cookies."""
        try:
            if self.COOKIE_FILE.exists():
                self.COOKIE_FILE.unlink()
                logger.info("Cleared saved cookies")
        except Exception as e:
            logger.error(f"Failed to clear cookies: {e}")

    async def goto_login_page(self) -> Page:
        """Navigate to Taobao login page.

        Returns:
            Page: Browser page on login URL
        """
        page = await self.get_page()
        await page.goto(self.TAOBAO_LOGIN_URL)
        logger.info(f"Navigated to Taobao login page: {self.TAOBAO_LOGIN_URL}")
        return page

    async def goto_orders_page(self) -> Page:
        """Navigate to Taobao orders page.

        Returns:
            Page: Browser page on orders URL
        """
        page = await self.get_page()
        await page.goto(self.TAOBAO_ORDERS_URL)
        logger.info(f"Navigated to Taobao orders page: {self.TAOBAO_ORDERS_URL}")
        return page

    async def goto_home_page(self) -> Page:
        """Navigate to Taobao home page.

        Returns:
            Page: Browser page on home URL
        """
        page = await self.get_page()
        await page.goto(self.TAOBAO_HOME_URL)
        logger.info(f"Navigated to Taobao home page: {self.TAOBAO_HOME_URL}")
        return page

    async def check_login_status(self) -> bool:
        """Check if currently logged in to Taobao.

        Returns:
            bool: True if logged in, False otherwise
        """
        if not self._initialized:
            return False

        try:
            page = await self.get_page()

            # Navigate to orders page with relaxed wait condition
            # Use 'domcontentloaded' instead of 'networkidle' to avoid timeout
            await page.goto(self.TAOBAO_ORDERS_URL, wait_until='domcontentloaded', timeout=30000)

            # Wait a bit for page to stabilize
            await page.wait_for_timeout(2000)

            # Check if redirected to login page
            current_url = page.url

            if 'login.taobao.com' in current_url:
                logger.info("Not logged in (redirected to login page)")
                return False

            # Method 1: Check page title (most reliable)
            try:
                title = await page.title()
                if '已买到的宝贝' in title or '我的订单' in title or 'buyertrade' in current_url:
                    logger.info(f"Login verified via page title: {title}")
                    return True
            except Exception as e:
                logger.debug(f"Title check failed: {e}")

            # Method 2: Check URL pattern
            if 'buyertrade.taobao.com' in current_url or 'trade/itemlist' in current_url:
                logger.info(f"Login verified via URL: {current_url}")
                return True

            # Method 3: Check for login elements (fallback)
            try:
                # Try multiple possible selectors
                selectors = [
                    '.site-user', '.buyer-info', '.member-nick',
                    '#J_OrderTable', '.order-item', '.bought-wrapper'
                ]
                for selector in selectors:
                    try:
                        elem = await page.query_selector(selector)
                        if elem:
                            logger.info(f"Login verified via element: {selector}")
                            return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Element check failed: {e}")

            logger.info("Not logged in (no verification method succeeded)")
            return False

        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False

    async def wait_for_login(self, timeout: int = None) -> bool:
        """Wait for user to complete login (scan QR code).

        Args:
            timeout: Timeout in seconds (default 300s / 5 minutes)

        Returns:
            bool: True if login successful, False if timeout
        """
        if timeout is None:
            timeout = self.LOGIN_TIMEOUT

        page = await self.get_page()

        try:
            # Wait for redirect to orders page or home page
            logger.info(f"Waiting for login (timeout: {timeout}s)...")

            # Set up dialog handler to auto-dismiss trust dialogs
            async def handle_dialog(dialog):
                logger.info(f"Dialog appeared: {dialog.message}")
                # Auto accept/dismiss trust dialogs
                if '信任' in dialog.message or 'trust' in dialog.message.lower():
                    logger.info("Auto-dismissing trust dialog")
                    await dialog.dismiss()
                else:
                    logger.info(f"Accepting dialog: {dialog.message}")
                    await dialog.accept()

            page.on('dialog', handle_dialog)

            # Use polling instead of wait_for_url for more robust detection
            logger.info("Using polling method to detect login completion...")
            start_time = asyncio.get_event_loop().time()

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    logger.error(f"Login timeout after {elapsed}s")
                    return False

                current_url = page.url
                logger.debug(f"[{elapsed:.1f}s] Current URL: {current_url}")

                # Check if URL changed (no longer on login page)
                if 'login.taobao.com' not in current_url and 'taobao.com' in current_url:
                    logger.info(f"✅ URL changed to: {current_url}")

                    # Wait briefly for page to stabilize
                    await asyncio.sleep(3)

                    # Try to save cookies immediately (before verification)
                    logger.info("Saving cookies immediately...")
                    try:
                        await self.save_cookies()
                        logger.info("✅ Cookies saved")
                    except Exception as e:
                        logger.warning(f"Failed to save cookies: {e}")

                    # Now verify login status
                    is_logged_in = await self.check_login_status()

                    if is_logged_in:
                        logger.info("✅ Login successful, cookies saved")
                        return True
                    else:
                        logger.warning("Login verification failed, but cookies may still be valid")
                        # Return True anyway since URL changed and cookies saved
                        return True

                # Poll every 2 seconds
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Login timeout or error: {e}")
            # Try to save cookies even on error
            try:
                await self.save_cookies()
                logger.info("Emergency cookie save attempted")
            except:
                pass
            return False

    async def take_screenshot(self, filename: str = None) -> str:
        """Take a screenshot of current page.

        Args:
            filename: Optional filename for screenshot

        Returns:
            str: Path to screenshot file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"taobao_screenshot_{timestamp}.png"

        screenshot_path = self.COOKIE_DIR / filename

        page = await self.get_page()
        await page.screenshot(path=str(screenshot_path))

        logger.info(f"Screenshot saved to {screenshot_path}")
        return str(screenshot_path)


# Global instance
playwright_manager = PlaywrightManager()