from .core.db_configs import MapBase


def init_db_data():
    """ 初始化数据库表 """
    MapBase.metadata.create_all()
    print("init db success")
    return True
