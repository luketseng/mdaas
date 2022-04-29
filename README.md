# Setup
1. Edit env config for startup
> vi server/config/env.conf
```
Example:
    [mysql]
    ip=0.0.0.0
    port=3306
    db=mfg
    user=root
    pass=password
    max_connection=128
    wait_timeout=180
```

2. Run docker
> cd server_env/  
> docker-compose up -d

3. Using api docs
> http://xxx.xxx.xxx.xxx:9796/apidocs


# API Result
> curl -X POST "http://0.0.0.0:9796/api/v1/mdaas/sn_info" -H "accept: application/json" -H "Content-Type: application/json" -d "{ \"ip\": \"192.168.11.233\", \"sn\": \"BZA044001A1M01A\"}"
```
After call sn_info api will gen status and history.log in /opt/logs

/opt/logs/
        └── BZA044001A1M01A
           ├── BZA044001A1M01A_20210125082431.log
           └── BZA044001A1M01A.status_1611534271
```

> curl -X POST "http://0.0.0.0:9796/api/v1/mdaas/download" -H "accept: application/json" -H "Content-Type: application/json" -d "{ \"ip\": \"192.168.11.233\", \"sn\": \"BZA044001A1M01A\"}"
```
After call download api will gen status, history.log, blobs and logs in /opt/logs and return zip file to user
/opt/logs/
        └── BZA044001A1M01A
            ├── blobs
            │   ├── xxx
            │   └── ...
            │
            ├── logs
            │   ├── xxx
            │   └── ...
            │
            ├── BZA044001A1M01A_20210125082431.log
            └── BZA044001A1M01A.status_1611534271
        

```


# MySQL Example
```
from connector.mysql_adapter import RetryMySQLDatabase


class MySqlCMD():
    def __init__(self):
        self.db = RetryMySQLDatabase.get_db_instance()

    def run_cmd(self, cmd):
        try:
            cursor = self.db.execute_sql(cmd)
            for row in cursor.fetchall():
                print(row)
        except Exception as e:
            print(str(e))
        finally:
            self.db.close()
```

# Requests Example
```
import requests

def get_json_data(self, url):
    try:
        response = requests.get(url, verify=False)
        if response.status_code != 200:
            print('Call api fail: ' + url)
        result = response.json()
        return result
    except Exception as e:
        print(e)

def get_blob_data(self, url, save_path):
    try:
        response = requests.get(url, verify=False)
        if response.status_code != 200:
            print('Call api fail: ' + url)

        totalbits = 0
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    totalbits += 1024
                    f.write(chunk)
    except Exception as e:
        print(e)
```
