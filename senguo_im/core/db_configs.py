import redis as redis_db
from mongoengine import connect
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from ..settings import (
    AUTH_REDIS_PASSWORD,
    AUTH_REDIS_PORT,
    AUTH_REDIS_SERVER,
    DB_CHARSET,
    DB_NAME,
    MYSQL_DRIVER,
    MYSQL_PASSWORD,
    MYSQL_SERVER,
    MYSQL_SLAVE_SERVER,
    MYSQL_USERNAME,
    REDIS_DB_0,
    REDIS_DB_1,
    REDIS_DB_2,
    REDIS_DB_3,
    REDIS_DB_4,
    REDIS_DB_5,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_SERVER,
)

# 主库
engine = create_engine(
    "mysql+{driver}://{username}:{password}@{server}/{database}?charset={charset}".format(
        driver=MYSQL_DRIVER,
        username=MYSQL_USERNAME,
        password=MYSQL_PASSWORD,
        server=MYSQL_SERVER,
        database=DB_NAME,
        charset=DB_CHARSET,
    ),
    pool_size=20,
    max_overflow=100,
    pool_recycle=7200,
    echo=False,  # 调试模式，开启后可输出所有查询语句
)
MapBase = declarative_base(bind=engine)
DBSession = sessionmaker(bind=engine)
scoped_DBSession = scoped_session(DBSession)

# 从库
slave_engine = create_engine(
    "mysql+{driver}://{username}:{password}@{server}/{database}?charset={charset}".format(
        driver=MYSQL_DRIVER,
        username=MYSQL_USERNAME,
        password=MYSQL_PASSWORD,
        server=MYSQL_SLAVE_SERVER,
        database=DB_NAME,
        charset=DB_CHARSET,
    ),
    pool_size=20,
    max_overflow=100,
    pool_recycle=7200,
    echo=False,  # 调试模式，开启后可输出所有查询语句
)
slave_DBSession = sessionmaker(bind=slave_engine, autoflush=False)
scoped_slave_DBSession = scoped_session(slave_DBSession)

# Redis缓存数据库
pool_db0 = redis_db.ConnectionPool(
    host=REDIS_SERVER, port=REDIS_PORT, password=REDIS_PASSWORD, db=int(REDIS_DB_0)
)
redis = redis_db.StrictRedis(connection_pool=pool_db0)

pool_db1 = redis_db.ConnectionPool(
    host=REDIS_SERVER, port=REDIS_PORT, password=REDIS_PASSWORD, db=int(REDIS_DB_1)
)
redis_config = redis_db.StrictRedis(connection_pool=pool_db1)

# passport.senguo.cc redis
auth_pool_db0 = redis_db.ConnectionPool(
    host=AUTH_REDIS_SERVER, port=AUTH_REDIS_PORT, password=AUTH_REDIS_PASSWORD, db=0
)
auth_redis = redis_db.StrictRedis(connection_pool=auth_pool_db0)

# 文件导出
pool_db2 = redis_db.ConnectionPool(
    host=REDIS_SERVER, port=REDIS_PORT, password=REDIS_PASSWORD, db=int(REDIS_DB_2)
)
redis_export = redis_db.StrictRedis(connection_pool=pool_db2)

# 消息队列
pool_db3 = redis_db.ConnectionPool(
    host=REDIS_SERVER, port=REDIS_PORT, password=REDIS_PASSWORD, db=int(REDIS_DB_3)
)
redis_msg = redis_db.StrictRedis(connection_pool=pool_db3)

# 短信发送队列
pool_db4 = redis_db.ConnectionPool(
    host=REDIS_SERVER, port=REDIS_PORT, password=REDIS_PASSWORD, db=int(REDIS_DB_4)
)
redis_send_msg = redis_db.StrictRedis(connection_pool=pool_db4)

# 登录限制相关
pool_db5 = redis_db.ConnectionPool(
    host=REDIS_SERVER, port=REDIS_PORT, password=REDIS_PASSWORD, db=int(REDIS_DB_5)
)
login_redis = redis_db.StrictRedis(connection_pool=pool_db5)

# 默认Mongodb数据库
# mdb = connect(
#     MDB_NAME, host=MDB_HOST + MDB_NAME, serverSelectionTimeoutMS=5000, connect=False
# )
