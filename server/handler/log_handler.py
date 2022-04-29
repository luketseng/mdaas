# -*- encoding: utf8-*-
from datetime import datetime, timedelta
from os import listdir
import os
import re
import sys
import time
import inspect


class LogHandler():
    def __init__(self, module_name, output_path='output/', log_file_name='mdaas'):
        self.module_name = module_name
        self.output_path = output_path
        self.log_file_name = log_file_name
        if not os.path.exists(output_path):
            os.makedirs(output_path)

    def _write_log(self, level, message):
        '''write message to log
            Args:
                level: log level
                message: log content
        '''
        try:
            self._delete_log_file()
            which_func = self.tracefunc()
            date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log = '[%s] [%s.%s] [%s] %s \n' % (date, self.module_name, which_func, level, str(message))
            log_date = datetime.now().strftime("%Y%m%d")
            with open(self.output_path + '/' + self.log_file_name + '_' + log_date + '.log', 'a') as log_file:
                log_file.write(log)
                sys.stdout.write(log)
                log_file.close()
        except Exception as e:
            print (e)

    def _delete_log_file(self, days=30):
        '''delete log file over timeout x days
            Args:
                days: timeout day
        '''
        today = datetime.now()
        offset = timedelta(days=-days)
        re_date = (today + offset)
        re_date_unix = time.mktime(re_date.timetuple())
        files = listdir(self.output_path)
        for file_name in files:
            filename, file_extension = os.path.splitext(file_name)
            if file_extension == '.log':
                date = re.search('[\d]{8}|$', filename).group()
                if date:
                    fullpath = os.path.join(self.output_path, file_name)
                    file_time = time.mktime(
                        datetime.strptime(date, "%Y%m%d").timetuple())
                    if file_time <= re_date_unix:
                        os.remove(fullpath)

    def tracefunc(self):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 1)
        return calframe[3][3]

    def debug(self, message):
        self._write_log('DEBUG', message)

    def info(self, message):
        self._write_log('INFO', message)

    def warning(self, message):
        self._write_log('WARNING', message)

    def error(self, message):
        self._write_log('ERROR', message)

    def critical(self, message):
        self._write_log('CRITICAL', message)
