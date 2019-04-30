
# coding: utf-8

from PyQt4.QtSql import *

class PostgresCon(QSqlDatabase):

    def __init__(self, host, port, dbname, user, password):
        super(PostgresCon, self).__init__('QPSQL')

        self.setHostName(host)
        self.setPort(port or -1)
        self.setDatabaseName(dbname)
        self.setUserName(user)
        self.setPassword(password)

    def select(self, query_string):
        self.open()
        query = QSqlQuery(self)

        try:
            query.exec_(query_string)

            if query.lastError().isValid():
                raise Exception(query.lastError().text())
        except:
            raise

        finally:
            self.close()

        return query

    def get_all_schemas(self):
        pass

    def get_all_tables(self, schema='public'):
        if schema is None:
            return []

        query = u"""SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema='{schema}'""".format(schema=schema)

        l = []
        result = self.select(query)

        while result.next():
            l.append(result.value(0))

        return sorted(l)

    def get_columns(self, table_name, schema='public'):
        query = u"""SELECT column_name, data_type, udt_name
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
        """.format(table=table_name)

        l = []
        result = self.select(query)

        while result.next():
            l.append( tuple((result.value(0), result.value(1), result.value(2))) )

        return sorted(l)
