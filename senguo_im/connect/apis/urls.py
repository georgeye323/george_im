from senguo_im.connect.apis.handlers import IMSocketHandler
from senguo_im.core.rabbitmq_kombu.room_handler import room_handler

urlpatterns = [
    (r"/comment/connect", IMSocketHandler, {"room_handler": room_handler}),
]
