from threading import Thread

from kombu import Exchange, Queue, pools
from kombu.mixins import ConsumerMixin

connections = pools.Connections(limit=100)


class ConsumerRoutes:
    def __init__(self, connection, thread_num):
        self.connection = connection
        self.thread_num = thread_num

    def route(self, **kwargs):
        def func_wrapper(func):
            self._route(callback=func, **kwargs)
            return func

        return func_wrapper

    def _route(
        self,
        exchange_name="",
        exchange_type="fanout",
        routing_key=None,
        queue_name_list=[],
        callback=None,
    ):
        exchange = Exchange(
            exchange_name, type=exchange_type, durable=True, auto_delete=False
        )
        queues = []
        for queue_name in queue_name_list:
            queue_name = queue_name or routing_key
            queue = Queue(
                queue_name,
                exchange,
                routing_key=routing_key,
                durable=True,
                auto_delete=False,
            )
            queues.append(queue)
        # 线程启动任务
        for i in range(self.thread_num):
            t = Thread(
                target=self._start_worker_thread, args=[queues, callback], daemon=True
            )
            t.start()

    def _start_worker_thread(self, queues: list, callback):
        with connections[self.connection].acquire(block=True) as conn:
            worker = Worker(conn, queues, callback)
            worker.run()


class Worker(ConsumerMixin):
    def __init__(self, connection, queues: list, callback):
        self.connection = connection
        self.queues = queues
        self.callback = callback

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queues, callbacks=[self.callback])]
