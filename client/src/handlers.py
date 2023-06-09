import json

from Shimarin.client.events import EventsHandlers, Event
from .jellyfin import AkarinClient

ev_handlers = EventsHandlers()
client = AkarinClient()

@ev_handlers.new(event_name="UserItems")
async def get_all_media(event: Event):
    params = None
    if event.payload:
        params = json.loads(event.payload)
    result = client.jellyfin.user_items(params=params)
    return await event.reply(result)
