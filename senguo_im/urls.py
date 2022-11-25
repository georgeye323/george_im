def load_urls(name):
    """Load the (URL pattern, handler) tuples for each component."""
    name = "senguo_im.{}.apis.urls".format(name)
    mod = __import__(name, fromlist=["urlpatterns"])
    return mod.urlpatterns


urlpatterns = []
urlpatterns.extend(load_urls("connect"))  # 测试
urlpatterns.extend(load_urls("user"))  # 测试
urlpatterns.extend(load_urls("chat"))  # 测试
