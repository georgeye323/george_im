from kombu import Connection

from senguo_im.core.rabbitmq_kombu.consumer import ConsumerRoutes
from senguo_im.core.rabbitmq_kombu.sender import Producer
from senguo_im.settings import KR_THREAD_NUM, RABBITMQ_BROKE, BURY_RABBITMQ_BROKE


class BaseConfig(object):
    @classmethod
    def get_connection(cls):
        connection = Connection(
            # host=cls.Host,
            # port=cls.Port,
            # virtual_host=cls.VirtualHost,
            # password=cls.PassWord,
            # userid=cls.UserId,
            cls.Broke
        )
        return connection


class Product(BaseConfig):
    # Host = RABBITMQ_HOST
    # Port = RABBITMQ_PORT
    # VirtualHost = RABBITMQ_VIRTUAL_HOST
    # PassWord = RABBITMQ_PASSWORD
    # UserId = RABBITMQ_USER_ID
    Broke = RABBITMQ_BROKE


class BuryProduct(BaseConfig):
    Broke = BURY_RABBITMQ_BROKE


config_dict = {"product": Product, "bury_product": BuryProduct}
config_use = config_dict.get("product")
bury_config_use = config_dict.get("bury_product")

# 生产者
KP = Producer(config_use.get_connection())
BURY_KP = Producer(bury_config_use.get_connection())
# 消费者
KR = ConsumerRoutes(config_use.get_connection(), int(KR_THREAD_NUM))
