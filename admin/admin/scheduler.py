"""后台沉淀定时任务：周期执行 FAQ 挖掘与知识缺口识别。"""

from __future__ import annotations

import asyncio

from loguru import logger

from admin.config import get_settings
from admin.database import AsyncSessionLocal
from admin.services import settlement_service


async def settlement_miner_loop() -> None:
    """每隔 ``FAQ_MINER_INTERVAL_MIN`` 分钟跑一次沉淀挖掘，异常仅记录不中断循环。"""
    settings = get_settings()
    interval = settings.FAQ_MINER_INTERVAL_MIN * 60
    while True:
        await asyncio.sleep(interval)
        try:
            async with AsyncSessionLocal() as session:
                result = await settlement_service.mine_knowledge(session)
                if any(result.get(key) for key in ("mined", "gaps_created", "gaps_updated")):
                    logger.info("沉淀挖掘完成：{}", result)
        except Exception:  # noqa: BLE001
            logger.exception("沉淀挖掘任务失败")
