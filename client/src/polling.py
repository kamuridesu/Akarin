import asyncio
import json
import requests

from typing import Callable, Any

from . import config


class Event:
    def __init__(self, event_type: str, identifier: str, payload: str | None) -> None:
        self.event_type = event_type
        self.payload = payload
        self.identifier = identifier

    @staticmethod
    def new(event_data: dict[str, str]) -> 'Event':
        return Event(event_data['event_type'], event_data['identifier'], event_data['payload'])
    
    async def reply(self, payload: Any):
        data = {
            "identifier": str(self.identifier),
            "payload": json.dumps(payload)
        }
        response = requests.get(f"{config.SERVER_ENDPOINT}/callback", json=data)
    
    def __str__(self) -> str:
        return f"Event: {self.event_type}, Identifier: {self.identifier}, Payload: {self.payload}"
    
    def __repr__(self) -> str:
        return self.__str__()


class EventHandler:
    def __init__(self, event_type: str, callback: Callable[[Any, Any], Any]) -> None:
        self.event_type = event_type
        self.callback = callback

    async def trigger(self, *args, **kwargs) -> None:
        await self.callback(*args, **kwargs)

    def __str__(self) -> str:
        return f"Event: {self.event_type}, Callback: {self.callback}"
    
    def __repr__(self) -> str:
        return self.__str__()


class EventsHandlers:
    def __init__(self):
        self.handlers: list[EventHandler] = []
    
    def register(self, handler: EventHandler) -> None:
        self.handlers.append(handler)

    def new(self, event_name: str):
        def wrapper(func: Callable):
            event_handler = EventHandler(event_name, func)
            self.register(event_handler)
            return func
        return wrapper

    async def handle(self, event: Event) -> None:
        for handle in self.handlers:
            if handle.event_type == event.event_type:
                asyncio.gather(handle.trigger(event))
    
    def __str__(self) -> str:
        return f"Handlers: {self.handlers}"
    
    def __repr__(self) -> str:
        return self.__str__()


class EventPolling:
    def __init__(self, events_handlers: EventsHandlers) -> None:
        self.events_handlers = events_handlers
        self.is_polling = False
        self.running_tasks: set[asyncio.Task] = set()

    async def start(self, polling_interval: int = 1, fetch: int = 10):
        self.is_polling = True
        while self.is_polling:
            events = requests.get(f"{config.SERVER_ENDPOINT}/events?fetch={fetch}")
            if events.status_code == 200:
                event_json = events.json()
                print(event_json)
                for event in event_json:
                    if event_json:
                        event = Event.new(event)
                        await self.__task_manager(event)
            await asyncio.sleep(polling_interval)

    async def __task_manager(self, event: Event):
        task = asyncio.create_task(self.events_handlers.handle(event))
        self.running_tasks.add(task) 
        task.add_done_callback(lambda t: self.running_tasks.remove(t))

    async def stop(self):
        if self.is_polling:
            self.is_polling = False
            for task in self.running_tasks:
                task.cancel()
            for task in self.running_tasks.copy():
                self.running_tasks.remove(task)
