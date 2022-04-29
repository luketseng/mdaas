# -*- encoding: utf8-*-
from playhouse.pool import PooledMySQLDatabase
from playhouse.shortcuts import ReconnectMixin
import peewee as pw
from configparser import ConfigParser
import os


config = ConfigParser()
config.read(os.path.join(os.path.abspath(
    os.path.dirname(__file__)), '../config', 'env.conf'))

class RetryMySQLDatabase(ReconnectMixin, PooledMySQLDatabase):
    _instance = None

    @staticmethod
    def get_db_instance():
        if not RetryMySQLDatabase._instance:
            RetryMySQLDatabase._instance = PooledMySQLDatabase(
                config.get('mysql', 'db'),
                max_connections=int(config.get('mysql', 'max_connection')),
                stale_timeout=int(config.get('mysql', 'wait_timeout')),
                host=config.get('mysql', 'ip'),
                user=config.get('mysql', 'user'),
                password=config.get('mysql', 'pass'),
                port=int(config.get('mysql', 'port'))
            )
        return RetryMySQLDatabase._instance


class MySQLDatabase():
    _instance = None

    @staticmethod
    def get_db_instance():
        if not MySQLDatabase._instance:
            MySQLDatabase._instance = pw.MySQLDatabase(
                config.get('mysql', 'db'),
                host=config.get('mysql', 'ip'),
                user=config.get('mysql', 'user'),
                passwd=config.get('mysql', 'pass'),
                port=int(config.get('mysql', 'port'))
            )
        return MySQLDatabase._instance

