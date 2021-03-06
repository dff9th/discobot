import sys
from datetime import datetime, date, timedelta, timezone
import asyncio
import discord

from lib import atcoder

JST = timezone(timedelta(hours=+9), 'JST')
WEEK_LIST = ['月', '火', '水', '木', '金', '土', '日']

def convert_week_knj(week_id: int) -> str:
    if week_id < 0 or week_id >= len(WEEK_LIST):
        raise ValueError(f"[ERROR] week_id is invalid: {week_id}")
    return WEEK_LIST[week_id]

class AtCoderClient(discord.Client):
    _is_called_on_ready = False
    _channel_ids = ()
    _last_get_minute = datetime.now(JST).strftime("%M")
    _last_get_day = date.today()

    def __init__(self, channel_ids: tuple):
        super().__init__()
        self._channel_ids = channel_ids

    @staticmethod
    def _extract_plan(contest_plan: dict, day: int) -> str:
        day_plan = []
        for contest in contest_plan:
            contest_day = contest['start_time'].date()
            if contest_day == day:
                day_plan.append(contest)
        return day_plan

    @staticmethod
    def _format_contest(contest: dict) -> str:
        start_time = contest['start_time']
        end_time = contest['end_time']
        week_knj = convert_week_knj(start_time.weekday())
        contest_time = \
            start_time.strftime('%Y-%m-%d') + f"({week_knj})" + \
            start_time.strftime('%H:%M') + '~' + end_time.strftime('%H:%M')
        return f"{contest_time}  {contest['name']}  Rate対象: {contest['rate']}\n" + \
               f"  {contest['url']}"

    @staticmethod
    def _make_contest_msg(contests: list) -> str:
        msg = ''
        for ctst in contests:
            msg += f"> {AtCoderClient._format_contest(ctst)}\n"
        return msg

    async def _send_plan_msg(self, channel):
        contest_plan = atcoder.get_contest_plan()
        today = date.today()
        today_contests = self._extract_plan(contest_plan, today)
        msg = ''
        if today_contests:
            msg += f"本日開催のコンテストがあります！！\n\n"
        else:
            msg += f"本日開催のコンテストはありません\n\n"
        # Add contest plan to message
        if contest_plan:
            msg += '予定されたコンテストは以下です\n'
            msg += AtCoderClient._make_contest_msg(contest_plan)
        else:
            msg += '予定されたコンテストはありません\n'
        await channel.send(msg)

    async def _inform_plan_everyday(self, channel):
        while True:
            today = date.today()
            if today != self._last_get_day:
                await self._send_plan_msg(channel)
                self._last_get_day = today
            await asyncio.sleep(1)

    async def _inform_contest_before(self, channel, hours=0, minutes=0):
        is_already_sent = True  # Set True not to send message at booted
        while True:
            is_before = False
            now = datetime.now(JST)
            contest_plan = atcoder.get_contest_plan()
            today_contests = []
            # Find contests started within 1h
            for contest in contest_plan:
                if contest['start_time'] - now < timedelta(hours=hours, minutes=minutes):
                    is_before = True
                    today_contests.append(contest)
            if is_before and not is_already_sent:
                before_time = ''
                if hours > 0:
                    before_time += f"{hours}時間"
                if minutes > 0:
                    before_time += f"{minutes}分"
                msg = f"コンテスト開始{before_time}前です！！\n"
                msg += AtCoderClient._make_contest_msg(today_contests)
                await channel.send(msg)
                is_already_sent = True
            elif not is_before:
                is_already_sent = False
            await asyncio.sleep(1)

    async def on_ready(self):
        print('on ready', flush=True)
        if not self._is_called_on_ready:
            for cid in self._channel_ids:
                channel = self.get_channel(cid)
                asyncio.ensure_future(self._inform_plan_everyday(channel))
                asyncio.ensure_future(self._inform_contest_before(channel, hours=1))
                asyncio.ensure_future(self._inform_contest_before(channel, minutes=5))
            self._is_called_on_ready = True


    async def on_message(self, message):
        # API 'get contest'
        if message.content.startswith("get contest"):
            await self._send_plan_msg(message.channel)

def main():
    # Check argument
    args = sys.argv
    if len(args) < 3:
        print(f'[ERROR] Usage: python {__file__} <token> [<channel id> ...]', file=sys.stderr)
        sys.exit(1)
    token = args[1]
    channel_ids = tuple(map(int, args[2:]))
    # Run bot
    ac_cli = AtCoderClient(channel_ids)
    ac_cli.run(token)

if __name__ == '__main__':
    main()
