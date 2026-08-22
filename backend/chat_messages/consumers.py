import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Grab the conversation_id from the WebSocket URL
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'

        # Join the conversation group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the conversation group when the user closes the app
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # This method is triggered whenever your View broadcasts a message
    async def chat_message(self, event):
        message_data = event['message']

        # Send the JSON data down the open WebSocket to the frontend
        await self.send(text_data=json.dumps(message_data))