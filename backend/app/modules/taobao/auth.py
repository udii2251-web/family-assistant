"""Taobao login authorization module.

Handles:
- Login page automation (Playwright)
- QR code display and wait
- Login status detection (Cookie check)
- Cookie persistence
- Session management
- Login expiry detection
- Feishu notification for re-auth
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.shared.database import SessionLocal
from app.modules.taobao.models import TaobaoAuthStatus
from app.modules.taobao.playwright_manager import playwright_manager

logger = logging.getLogger(__name__)


class TaobaoAuthManager:
    """Manages Taobao login authorization.

    Features:
    - Automatic QR code login
    - Login status tracking
    - Cookie persistence
    - Session expiry detection
    - Feishu notification on expiry
    """

    # Cookie有效期（淘宝通常7-30天）
    COOKIE_EXPIRY_DAYS = 7

    def __init__(self):
        """Initialize auth manager."""
        self._notification_callback = None

    def set_notification_callback(self, callback):
        """Set callback function for Feishu notification.

        Args:
            callback: Async function to send notification
                     Signature: async callback(open_id: str, message: str) -> bool
        """
        self._notification_callback = callback

    async def login_with_qrcode(self, headless: bool = False) -> dict:
        """Open Taobao login page and wait for QR code scan.

        Args:
            headless: Whether to run browser in headless mode
                     (should be False for QR code display)

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'user_nick': str (if successful),
                'timestamp': str
            }
        """
        try:
            # Initialize Playwright
            await playwright_manager.initialize(headless=headless)

            # Navigate to login page
            page = await playwright_manager.goto_login_page()

            logger.info("Waiting for QR code scan...")

            # Wait for login
            success = await playwright_manager.wait_for_login()

            if success:
                # Get user info
                user_info = await self._get_user_info()

                # Update auth status in database
                await self._update_auth_status(
                    is_logged_in=True,
                    user_nick=user_info.get('nick', ''),
                    user_id=user_info.get('user_id', '')
                )

                return {
                    'success': True,
                    'message': '登录成功',
                    'user_nick': user_info.get('nick', ''),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'message': '登录超时，请重新扫码',
                    'timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return {
                'success': False,
                'message': f'登录失败: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }

    async def check_login_status(self) -> dict:
        """Check current login status.

        Returns:
            dict: {
                'is_logged_in': bool,
                'user_nick': str,
                'last_login_time': datetime,
                'expiry_time': datetime,
                'needs_reauth': bool,
                'message': str
            }
        """
        try:
            # Check database for auth status
            db = SessionLocal()
            try:
                auth_status = db.query(TaobaoAuthStatus).first()

                if not auth_status:
                    return {
                        'is_logged_in': False,
                        'user_nick': '',
                        'last_login_time': None,
                        'expiry_time': None,
                        'needs_reauth': True,
                        'message': '未登录'
                    }

                # Check if cookie expired
                needs_reauth = False
                if auth_status.login_expiry_time:
                    if datetime.now() > auth_status.login_expiry_time:
                        needs_reauth = True

                # If marked as logged in, verify with browser
                if auth_status.is_logged_in and not needs_reauth:
                    # Initialize browser if needed
                    if not playwright_manager._initialized:
                        await playwright_manager.initialize(headless=True)

                    # Check actual login status
                    is_actually_logged_in = await playwright_manager.check_login_status()

                    if not is_actually_logged_in:
                        needs_reauth = True
                        auth_status.is_logged_in = False
                        auth_status.needs_reauth = True
                        auth_status.status_message = "登录已失效"
                        db.commit()

                return {
                    'is_logged_in': auth_status.is_logged_in,
                    'user_nick': auth_status.user_nick or '',
                    'last_login_time': auth_status.last_login_time,
                    'expiry_time': auth_status.login_expiry_time,
                    'needs_reauth': needs_reauth,
                    'message': auth_status.status_message or ''
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return {
                'is_logged_in': False,
                'user_nick': '',
                'last_login_time': None,
                'expiry_time': None,
                'needs_reauth': True,
                'message': f'检查登录状态失败: {str(e)}'
            }

    async def refresh_session(self) -> dict:
        """Refresh browser session to extend login validity.

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        try:
            # Initialize if needed
            if not playwright_manager._initialized:
                await playwright_manager.initialize(headless=True)

            # Check if still logged in
            is_logged_in = await playwright_manager.check_login_status()

            if is_logged_in:
                # Navigate to home page to refresh session
                await playwright_manager.goto_home_page()

                # Save cookies
                await playwright_manager.save_cookies()

                # Update expiry time
                db = SessionLocal()
                try:
                    auth_status = db.query(TaobaoAuthStatus).first()
                    if auth_status:
                        auth_status.login_expiry_time = datetime.now() + timedelta(days=self.COOKIE_EXPIRY_DAYS)
                        auth_status.last_check_time = datetime.now()
                        db.commit()
                finally:
                    db.close()

                return {
                    'success': True,
                    'message': 'Session刷新成功'
                }
            else:
                return {
                    'success': False,
                    'message': '登录已失效，需要重新登录'
                }

        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return {
                'success': False,
                'message': f'Session刷新失败: {str(e)}'
            }

    async def logout(self) -> dict:
        """Logout and clear session.

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        try:
            # Clear cookies
            playwright_manager.clear_cookies()

            # Update database
            db = SessionLocal()
            try:
                auth_status = db.query(TaobaoAuthStatus).first()
                if auth_status:
                    auth_status.is_logged_in = False
                    auth_status.needs_reauth = True
                    auth_status.status_message = "已登出"
                    db.commit()
            finally:
                db.close()

            # Close browser
            await playwright_manager.close()

            return {
                'success': True,
                'message': '已成功登出'
            }

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return {
                'success': False,
                'message': f'登出失败: {str(e)}'
            }

    async def notify_login_expiry(self, open_id: str):
        """Send Feishu notification about login expiry.

        Args:
            open_id: User's Feishu open_id
        """
        if self._notification_callback:
            try:
                await self._notification_callback(
                    open_id,
                    "淘宝账号登录已失效，请重新扫码授权。\n\n请回复「登录淘宝」触发登录流程。"
                )
                logger.info(f"Login expiry notification sent to {open_id}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
        else:
            logger.warning("No notification callback set")

    async def _get_user_info(self) -> dict:
        """Get current user info from Taobao.

        Returns:
            dict: {
                'nick': str,
                'user_id': str
            }
        """
        try:
            page = await playwright_manager.get_page()

            # Navigate to home page
            await playwright_manager.goto_home_page()

            # Try to get user nickname
            try:
                # Look for user nickname element
                user_nick_elem = await page.query_selector('.site-user .user-nick')
                if user_nick_elem:
                    nick = await user_nick_elem.text_content()
                else:
                    # Alternative selector
                    user_nick_elem = await page.query_selector('.member-nick')
                    nick = await user_nick_elem.text_content() if user_nick_elem else ''

                return {
                    'nick': nick.strip() if nick else '',
                    'user_id': ''  # User ID is not easily accessible
                }
            except Exception as e:
                logger.warning(f"Could not get user info: {e}")
                return {
                    'nick': '',
                    'user_id': ''
                }

        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return {
                'nick': '',
                'user_id': ''
            }

    async def _update_auth_status(
        self,
        is_logged_in: bool,
        user_nick: str = '',
        user_id: str = ''
    ):
        """Update auth status in database.

        Args:
            is_logged_in: Whether user is logged in
            user_nick: User's Taobao nickname
            user_id: User's Taobao ID
        """
        db = SessionLocal()
        try:
            auth_status = db.query(TaobaoAuthStatus).first()

            if not auth_status:
                # Create new record
                auth_status = TaobaoAuthStatus(
                    is_logged_in=is_logged_in,
                    user_nick=user_nick,
                    user_id=user_id,
                    last_login_time=datetime.now() if is_logged_in else None,
                    last_check_time=datetime.now(),
                    login_expiry_time=datetime.now() + timedelta(days=self.COOKIE_EXPIRY_DAYS) if is_logged_in else None,
                    cookie_file=str(playwright_manager.COOKIE_FILE),
                    status_message="登录成功" if is_logged_in else "已登出",
                    needs_reauth=not is_logged_in
                )
                db.add(auth_status)
            else:
                # Update existing record
                auth_status.is_logged_in = is_logged_in
                auth_status.user_nick = user_nick
                auth_status.user_id = user_id
                auth_status.last_login_time = datetime.now() if is_logged_in else auth_status.last_login_time
                auth_status.last_check_time = datetime.now()
                auth_status.login_expiry_time = datetime.now() + timedelta(days=self.COOKIE_EXPIRY_DAYS) if is_logged_in else None
                auth_status.cookie_file = str(playwright_manager.COOKIE_FILE)
                auth_status.status_message = "登录成功" if is_logged_in else "已登出"
                auth_status.needs_reauth = not is_logged_in

            db.commit()
            logger.info(f"Auth status updated: logged_in={is_logged_in}, nick={user_nick}")

        except Exception as e:
            logger.error(f"Failed to update auth status: {e}")
            db.rollback()
        finally:
            db.close()


# Global instance
taobao_auth_manager = TaobaoAuthManager()