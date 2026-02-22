import aiohttp
import json
import logging

class Notifier:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger("100x.notifier")

    async def send_discord(self, message: str, embed: dict = None):
        if not self.webhook_url:
            self.logger.info(f"[NOTIFY] No webhook set. Message: {message}")
            return

        payload = {"content": message}
        if embed:
            payload["embeds"] = [embed]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status >= 400:
                        self.logger.error(f"Failed to send Discord notification: {response.status}")
        except Exception as e:
            self.logger.error(f"Notification error: {e}")

    async def notify_trade_execution(self, trade_data: dict):
        side_emoji = "🚀" if trade_data['side'] == 'LONG' else "🔻"
        embed = {
            "title": f"{side_emoji} Trade Executed: {trade_data['symbol']}",
            "color": 3066993 if trade_data['side'] == 'LONG' else 15158332,
            "fields": [
                {"name": "Side", "value": trade_data['side'], "inline": True},
                {"name": "Lev", "value": f"{trade_data['leverage']}x", "inline": True},
                {"name": "Qty", "value": str(trade_data['quantity']), "inline": True},
                {"name": "Entry", "value": f"${trade_data['entry_price']}", "inline": True},
                {"name": "TP", "value": f"${trade_data['tp_price']}", "inline": True},
                {"name": "SL", "value": f"${trade_data['sl_price']}", "inline": True},
            ],
            "timestamp": trade_data.get('created_at', '')
        }
        await self.send_discord("", embed=embed)
