from threading import Thread

from kombu import Exchange
from kombu.pools import producers


class Producer(object):
    def __init__(self, connection):
        self.connection = connection

    def send_as_task(
        self,
        exchange_name="",
        payload={},
        routing_key="",
        exchange_type="fanout",
        durable=True,
    ):
        exchange = Exchange(
            name=exchange_name, type=exchange_type, durable=durable, auto_delete=False
        )
        payload = payload
        # 多线程启动,方便发任务
        t = Thread(
            target=self._start_worker_thread, args=[payload, exchange, routing_key]
        )
        t.start()

    def _start_worker_thread(
        self, payload, exchange, routing_key,
    ):
        # 使用了producers连接池
        with producers[self.connection].acquire(block=True) as producer:
            producer.publish(
                body=payload,
                serializer="json",
                # compression="bzip2",
                exchange=exchange,
                declare=[exchange],
                routing_key=routing_key,
                # retry=True,
                # retry_policy={
                #     "interval_start": 0,  # First retry immediately,
                #     "interval_step": 2,  # then increase by 2s for every retry.
                #     "interval_max": 30,  # but don't exceed 30s between retries.)
                #     "max_retries": 30,  # give up after 30 tries.
                # },
            )
