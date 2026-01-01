import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from .models import Match
from .engine import (
    play_character,
    place_trap,
    serialize_match_for_viewer,
    ensure_match_initialized,
    timeout_forfeit_if_needed,
)

class MatchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", AnonymousUser())
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return

        self.match_id = str(self.scope["url_route"]["kwargs"]["match_id"])
        self.user = user

        match = await self._get_match()
        if not match:
            await self.close(code=4004)
            return

        self.player_num = await self._get_player_num(match, user.id)
        if self.player_num == 0:
            await self.close(code=4003)
            return

        self.group_name = f"match_{self.match_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self._init_if_needed(match)

        # watchdog timer por conexión
        self._timer_task = asyncio.create_task(self._watch_timeout_loop())

        await self._send_state()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "_timer_task") and self._timer_task:
            self._timer_task.cancel()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self.send_json({"type": "ERROR", "message": "JSON inválido"})
            return

        msg_type = data.get("type")

        # ✅ check timeout before processing
        did_forfeit = await self._timeout_check()
        if did_forfeit:
            await self.channel_layer.group_send(self.group_name, {"type": "broadcast_state"})
            return

        if msg_type == "SYNC":
            await self._send_state()
            return

        if msg_type == "PLAY_CHARACTER":
            await self._handle_play_character(data)
            return

        if msg_type == "PLACE_TRAP":
            await self._handle_place_trap(data)
            return

        await self.send_json({"type": "ERROR", "message": "Evento no soportado"})

    async def _handle_play_character(self, data):
        card_id = int(data.get("card_id", 0))
        pos = int(data.get("pos", -1))

        try:
            await self._apply_play_character(card_id, pos)
        except Exception as e:
            await self.send_json({"type": "ERROR", "message": str(e)})
            return

        await self.channel_layer.group_send(self.group_name, {"type": "broadcast_state"})

    async def _handle_place_trap(self, data):
        trap_id = int(data.get("trap_id", 0))
        pos = int(data.get("pos", -1))

        try:
            await self._apply_place_trap(trap_id, pos)
        except Exception as e:
            await self.send_json({"type": "ERROR", "message": str(e)})
            return

        await self.channel_layer.group_send(self.group_name, {"type": "broadcast_state"})

    async def broadcast_state(self, event):
        await self._send_state()

    async def _send_state(self):
        match = await self._get_match()
        payload = await self._serialize(match)
        await self.send_json({"type": "STATE", "payload": payload})

    async def send_json(self, obj):
        await self.send(text_data=json.dumps(obj))

    async def _timeout_check(self) -> bool:
        """
        Retorna True si forfeit fue aplicado.
        """
        return await self._timeout_forfeit()

    async def _watch_timeout_loop(self):
        """
        Loop: duerme poco y chequea si se venció.
        (ligero, pero efectivo sin Celery)
        """
        try:
            while True:
                await asyncio.sleep(1.0)
                did_forfeit = await self._timeout_forfeit()
                if did_forfeit:
                    await self.channel_layer.group_send(self.group_name, {"type": "broadcast_state"})
        except asyncio.CancelledError:
            return

    @database_sync_to_async
    def _timeout_forfeit(self) -> bool:
        try:
            match = Match.objects.select_related("player1", "player2").get(id=self.match_id)
        except Match.DoesNotExist:
            return False
        return timeout_forfeit_if_needed(match)

    @database_sync_to_async
    def _get_match(self):
        try:
            return Match.objects.select_related("player1", "player2").get(id=self.match_id)
        except Match.DoesNotExist:
            return None

    @database_sync_to_async
    def _init_if_needed(self, match):
        ensure_match_initialized(match)

    @database_sync_to_async
    def _get_player_num(self, match, user_id: int) -> int:
        if match.player1_id == user_id:
            return 1
        if match.player2_id == user_id:
            return 2
        return 0

    @database_sync_to_async
    def _apply_play_character(self, card_id: int, pos: int):
        match = Match.objects.select_related("player1", "player2").get(id=self.match_id)
        return play_character(match, self.player_num, card_id, pos)

    @database_sync_to_async
    def _apply_place_trap(self, trap_id: int, pos: int):
        match = Match.objects.select_related("player1", "player2").get(id=self.match_id)
        return place_trap(match, self.player_num, trap_id, pos)

    @database_sync_to_async
    def _serialize(self, match):
        return serialize_match_for_viewer(match, self.player_num)
