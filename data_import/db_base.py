import yaml
import pymongo
from contextlib import contextmanager
from pathlib import Path


class MongoDBBase:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBBase, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._client:
            self._init_connection()

    def _init_connection(self):
        """初始化MongoDB连接"""
        try:
            # 读取配置文件
            config_path = Path(__file__).parent / 'config.yaml'
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 获取MongoDB配置
            mongo_config = config['mongodb']
            username = mongo_config['username']
            password = mongo_config['password']
            host = mongo_config['host']
            port = mongo_config['port']
            database = mongo_config['database']
            
            # 连接MongoDB
            self._client = pymongo.MongoClient(f"mongodb://{username}:{password}@{host}:{port}/")
            self._db = self._client[database]
        except Exception as e:
            raise Exception(f"MongoDB连接初始化失败: {e}")

    @property
    def db(self):
        """获取数据库实例"""
        return self._db

    @property
    def client(self):
        """获取客户端实例"""
        return self._client

    def __del__(self):
        """析构函数，确保连接被关闭"""
        if self._client:
            self._client.close()

    @contextmanager
    def get_connection(self):
        """上下文管理器，用于临时获取数据库连接"""
        try:
            yield self.db
        finally:
            pass  # 连接会在对象销毁时关闭 