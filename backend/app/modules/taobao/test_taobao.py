#!/usr/bin/env python3
"""Test script for Taobao module.

This script tests:
1. Module imports
2. Database models
3. Tool definitions
4. Basic functionality (without actual browser automation)
"""

import sys
import os

# Add backend parent directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, backend_dir)

import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all modules can be imported."""
    logger.info("Testing imports...")

    try:
        # Test models
        from app.modules.taobao.models import TaobaoOrder, TaobaoOrderItem, TaobaoAuthStatus
        logger.info("✓ Models imported successfully")

        # Test playwright manager
        from app.modules.taobao.playwright_manager import PlaywrightManager, playwright_manager
        logger.info("✓ Playwright manager imported successfully")

        # Test auth manager
        from app.modules.taobao.auth import TaobaoAuthManager, taobao_auth_manager
        logger.info("✓ Auth manager imported successfully")

        # Test sync manager
        from app.modules.taobao.sync import TaobaoSyncManager, taobao_sync_manager
        logger.info("✓ Sync manager imported successfully")

        # Test tools
        from app.modules.taobao.tools import get_taobao_tools, execute_taobao_tool, TaobaoSkill
        logger.info("✓ Tools imported successfully")

        # Test scheduler
        from app.modules.taobao.scheduler import TaobaoScheduler, taobao_scheduler
        logger.info("✓ Scheduler imported successfully")

        # Test module exports
        from app.modules.taobao import get_taobao_tools, TaobaoSkill
        logger.info("✓ Module exports working")

        return True

    except Exception as e:
        logger.error(f"✗ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_models():
    """Test database models can be created."""
    logger.info("\nTesting database models...")

    try:
        from app.modules.taobao.models import TaobaoOrder, TaobaoOrderItem, TaobaoAuthStatus
        from app.shared.database import Base, engine

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")

        # Test creating an order
        test_order = TaobaoOrder(
            order_id="test123456789",
            product_name="测试商品",
            shop_name="测试店铺",
            total_price=99.99,
            status="completed"
        )
        logger.info(f"✓ Test order created: {test_order}")

        # Test creating auth status
        test_auth = TaobaoAuthStatus(
            is_logged_in=True,
            user_nick="测试用户"
        )
        logger.info(f"✓ Test auth status created: {test_auth}")

        return True

    except Exception as e:
        logger.error(f"✗ Database model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools():
    """Test tool definitions."""
    logger.info("\nTesting tool definitions...")

    try:
        from app.modules.taobao import get_taobao_tools

        tools = get_taobao_tools()

        # Check tool count
        if len(tools) != 4:
            logger.error(f"✗ Expected 4 tools, got {len(tools)}")
            return False

        logger.info(f"✓ Got {len(tools)} tools")

        # Check tool names
        tool_names = [tool['function']['name'] for tool in tools]
        expected_names = [
            'sync_taobao_orders',
            'query_taobao_orders',
            'check_taobao_login',
            'login_taobao'
        ]

        for name in expected_names:
            if name in tool_names:
                logger.info(f"  ✓ {name}")
            else:
                logger.error(f"  ✗ {name} not found")
                return False

        # Test TaobaoSkill
        from app.modules.taobao import TaobaoSkill

        skill = TaobaoSkill()
        logger.info(f"✓ TaobaoSkill created: {skill.name}")
        logger.info(f"  Description: {skill.description}")

        # Test skill methods
        tools = skill.get_tools()
        logger.info(f"  ✓ get_tools() returns {len(tools)} tools")

        system_prompt = skill.system_prompt
        logger.info(f"  ✓ system_prompt length: {len(system_prompt)} chars")

        return True

    except Exception as e:
        logger.error(f"✗ Tool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_directory():
    """Test that data directory can be created."""
    logger.info("\nTesting data directory...")

    try:
        from app.modules.taobao.playwright_manager import playwright_manager
        from pathlib import Path

        # Check cookie directory
        cookie_dir = playwright_manager.COOKIE_DIR
        cookie_file = playwright_manager.COOKIE_FILE

        logger.info(f"Cookie directory: {cookie_dir}")
        logger.info(f"Cookie file: {cookie_file}")

        # Create directory if not exists
        cookie_dir.mkdir(parents=True, exist_ok=True)

        if cookie_dir.exists():
            logger.info("✓ Data directory created/exists")
            return True
        else:
            logger.error("✗ Failed to create data directory")
            return False

    except Exception as e:
        logger.error(f"✗ Data directory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Taobao Module Test Suite")
    logger.info("=" * 60)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Database Models", test_database_models()))
    results.append(("Tools", test_tools()))
    results.append(("Data Directory", test_data_directory()))

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    logger.info("=" * 60)
    logger.info(f"Total: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)