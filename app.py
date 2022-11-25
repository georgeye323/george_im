#! /usr/bin/env python3
import signal
import sys
import time
import traceback

import sentry_sdk
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.wsgi

from sentry_sdk.integrations.tornado import TornadoIntegration
from tornado.options import define, options

from senguo_im.init_db import init_db_data
from senguo_im.settings import COOKIE_SECRET, ROOT_HOST_NAME, SENTRY_DSN
from senguo_im.urls import urlpatterns

define("debug", default=0, help="debug mode: 1 to open, 0 to close")
define("port", default=8889, help="port, defualt: 8889")

settings = {"cookie_secret": COOKIE_SECRET, "xsrf_cookies": False}

sentry_sdk.init(dsn=SENTRY_DSN, integrations=[TornadoIntegration()])


class Application(tornado.web.Application):
    def __init__(self):
        settings["debug"] = bool(options.debug)
        super().__init__(urlpatterns, **settings)


# 自定义日志格式
def log_request(handler):
    if handler.get_status() < 400:
        log_method = tornado.log.access_log.info
    elif handler.get_status() < 500:
        log_method = tornado.log.access_log.warning
    else:
        log_method = tornado.log.access_log.error
    request_time = 1000.0 * handler.request.request_time()

    log_method(
        "@ [%d] %d %s %.2fms",
        options.port,
        handler.get_status(),
        handler._request_summary(),
        request_time,
    )


def sig_handler(sig, frame):
    """信号处理函数
    """
    print("\nReceived interrupt signal: %s" % sig)
    tornado.ioloop.IOLoop.instance().add_callback(shutdown)


def shutdown():
    """进程关闭处理
    """
    print("Stopping http server, please wait...")
    # 停止接受Client连接
    application.stop()

    io_loop = tornado.ioloop.IOLoop.instance()
    # 设置最长等待强制结束时间
    deadline = time.time() + 5

    def stop_loop():
        now = time.time()
        if now < deadline:
            io_loop.add_timeout(now + 1, stop_loop)
        else:
            io_loop.stop()

    stop_loop()


if __name__ == "__main__":
    # 等待supervisor发送进程结束信号
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    # 初始化表结构
    init_db_data()

    tornado.options.parse_command_line()
    try:
        from senguo_im.core.rabbitmq_kombu import listen
    except:
        print(traceback.format_exc())
    app = Application()
    app.settings["log_function"] = log_request
    application = tornado.httpserver.HTTPServer(app, xheaders=True)
    application.listen(options.port)
    if options.debug == 1:
        debug_str = "in debug mode"
    elif options.debug == 2:
        print("run test success, exiting...")
        sys.exit(0)
    else:
        debug_str = "in production mode"
    print(f"running {ROOT_HOST_NAME} {debug_str} @ {options.port}...")
    tornado.ioloop.IOLoop.instance().start()
