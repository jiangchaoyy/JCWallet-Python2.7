#Coding:utf-8
"""数据库处理类"""

import os
import sqlite3

__FILEDBSQLITE3__ = 'DBModule.DBOperateSqlite3: '

def GetBreakpoint():
    """VS2010中出异常,然后可以跟踪调试"""
    try:
        s = "中文"
        s.decode('gbk')
    except:
        pass

class DBOperateSqlite3(object):
    """使用Sqlite3数据库"""

    def __init__(self,path):
        self.dbPathBase = path
        
        self.dbName = u'myWalletMain'
        try:
            if not os.path.exists(self.dbPathBase):
                os.mkdir(self.dbPathBase)
            self.dbDataPath = os.path.join(self.dbPathBase,self.dbName + '.db')
        except:
            print __FILEDBSQLITE3__,'mkdir ',self.dbPathBase,' failed.'

        #总收支表名
        self.totalIncomeAndPayTableName = u'totalIAP'
        #账户信息表名
        self.accountTableName = u'accountInfo'
        #详细收支表名
        self.totalIAPDTableName = u'totalIAPD'
        #汽车费用表名
        self.carExpensesTableName = u'carExpenses'
        #初始化数据库,相当于Open函数
        self.InitDB()

    def InitDB(self):

        #数据库初始化,sqlite3中路径必须是utf-8编码
        try:
            self.dbConnect = sqlite3.connect(self.dbDataPath.encode("utf-8"))
            self.dbConnect.isolation_level = None
            #创建执行游标
            self.cursor = self.dbConnect.cursor()
        except:
            print __FILEDBSQLITE3__,'connect database failed.'

        #创建总收支表
        self.sqlTotalIAP = '''create table '%s'(
            'id' integer primary key autoincrement not null,
            'date' date NOT NULL,
            'realIncome' float,
            'transferIncome' float,
            'transferPay' float,
            'realPay' float,
            'account' text,
            'subtype' text,
            'description' text
            )''' % self.totalIncomeAndPayTableName

        #创建账户信息表
        self.sqlAccount = '''create table '%s'(
            'id' integer primary key autoincrement not null,
            'number' text,
            'alias' text,
            'bankname' text,
            'balance' float,
            'description' text
            )''' % self.accountTableName

        #创建详细收支信息表
        self.sqlIAPDetail = '''create table '%s'(
            'id' integer primary key autoincrement not null,
            'date' date NOT NULL,
            'number' float,
            'account' text,
            'description' text
            )''' % self.totalIAPDTableName

        #创建汽车费用信息表
        self.sqlCarExpenses = '''create table '%s'(
            'id' integer primary key autoincrement not null,
            'date' date NOT NULL,
            'number' float,
            'type' text,
            'description' text
            )''' % self.carExpensesTableName

        #判断表是否已经创建
        sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        result = self.__ExecuteSQL__(sql)

        listCreateTableSQL = []
        existTableName = []
        if len(result) > 0:
            for i in range(len(result)):
                existTableName.append(result[i][0])

            if self.totalIncomeAndPayTableName not in existTableName:
                listCreateTableSQL.append(self.sqlTotalIAP)
            elif self.accountTableName not in existTableName:
                listCreateTableSQL.append(self.sqlAccount)
            elif self.totalIAPDTableName not in existTableName:
                listCreateTableSQL.append(self.sqlIAPDetail)
            elif self.carExpensesTableName not in existTableName:
                listCreateTableSQL.append(self.sqlCarExpenses)
        else:
            listCreateTableSQL.append(self.sqlTotalIAP)
            listCreateTableSQL.append(self.sqlAccount)
            listCreateTableSQL.append(self.sqlIAPDetail)
            listCreateTableSQL.append(self.sqlCarExpenses)

        for i in range(len(listCreateTableSQL)):
            self.__ExecuteSQL__(listCreateTableSQL[i])

    def __ExecuteSQL__(self,sql):
        '''内部执行SQL语句,并返回执行结果'''
        result = tuple()
        if len(sql) > 0:
            try:
                #print sql
                self.cursor.execute(sql)
                result = self.cursor.fetchall()
            except:
                result = tuple()
                print __FILEDBSQLITE3__,'execute sql failed: ',sql

        return tuple(result)

    def __del__(self):
        try:
            self.cursor.close()
            self.dbConnect.commit()
            self.dbConnect.close()
        except:
            print __FILEDBSQLITE3__,'Close dbconnect failed.'

    def DBClose(self):
        self.dbConnect.close()
#详细收支表
    def AddDetailIAPItem(self,values):
        """添加详细收支记录项目"""
        if 4 == len(values):
            try:
                values.insert(0,self.totalIAPDTableName)
                sql = "insert into '%s' values(NULL,'%s','%s','%s','%s')" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'AddDetailIAPItem failed:',values

    def ChangedDetailIAPItem(self,values):
        """"修改详细收支记录项目"""
        if 5 == len(values):
            try:
                values.insert(0,self.totalIAPDTableName)
                sql = "update '%s' set 'date' = '%s','number' = '%s','account' = '%s','description' = '%s' where id = '%s'" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'ChangedDetailIAPItem failed:',values

    def GetAllDetailIAPItems(self):
        """获取所有详细收支表记录"""
        sql = "select * from %s order by date asc" % self.totalIAPDTableName
        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def GetDetailIAPExistMonth(self):
        """获取详细收支表中有记录的月份"""
        sql = "select distinct date from %s order by date desc" % (self.totalIAPDTableName)
        result = self.__ExecuteSQL__(sql)

        month = ["",]
        for item in result:
            item = item[0][0:7]
            if item not in month:
                month.append(item)

        return tuple(month)

    def GetDetailIAPItemsForConditionMonth(self,month,alais):
        """根据条件进行查询:月份和账户别名,否则查全部记录"""
        if (len(month) > 0) and (len(alais) > 0):
            #select * from db_xxx where substr(date(field_yyy),1,7) = '2012-07'
            sql = "select * from %s where substr(datetime(date),1,7) = '%s' and account = '%s' order by date asc" % (self.totalIAPDTableName,month,alais)
        elif len(month) > 0:
            sql = "select * from %s where substr(datetime(date),1,7) = '%s' order by date asc" % (self.totalIAPDTableName,month)
        elif len(alais) > 0:
            sql = "select * from %s where account = '%s' order by date asc" % (self.totalIAPDTableName,alais)
        else:
            sql = "select * from %s order by date asc" % (self.totalIAPDTableName)

        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def GetDetailIAPItemsForConditionDate(self,dtStart,dtEnd,alais):
        if len(alais) > 0:
            sql = "select * from %s where datetime(date) >= datetime('%s') and datetime(date) <= datetime('%s') and account = '%s' order by date asc" % (self.totalIAPDTableName,dtStart,dtEnd,alais)
        else:
            sql = "select * from %s where datetime(date) >= datetime('%s') and datetime(date) <= datetime('%s') order by date asc" % (self.totalIAPDTableName,dtStart,dtEnd)

        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def DeleteDetailIAPItems(self,ids):
        """删除详细收支表中记录"""
        for i in range(0,len(ids)):
            sql = "delete from %s where id=%s" % (self.totalIAPDTableName,ids[i])
            self.__ExecuteSQL__(sql)
#账户信息表
    def AddAccountItem(self,values):
        """添加账户记录项目"""
        if 5 == len(values):
            try:
                values.insert(0,self.accountTableName)
                sql = "insert into '%s' values(NULL,'%s','%s','%s','%s','%s')" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'AddAccountItem failed:',values

    def ChangedAccountItem(self,values):
        """"修改账户记录项目"""
        if 6 == len(values):
            try:
                values.insert(0,self.accountTableName)
                sql = "update '%s' set 'number' = '%s','alias' = '%s','bankname' = '%s','balance' = '%s','description' = '%s' where id = '%s'" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'ChangedAccountItem failed:',values

    def GetAllAccountItems(self):
        """获取所有账户信息"""
        sql = "select * from %s " % self.accountTableName
        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def DeleteAccountItems(self,ids):
        """删除账户信息"""
        for i in range(0,len(ids)):
            sql = "delete from %s where id=%s" % (self.accountTableName,ids[i])
            self.__ExecuteSQL__(sql)

    def GetAccountAliasList(self):
        """查询账户信息表,获得账户别名信息"""
        sql = "select alias from %s" % (self.accountTableName)
        result = self.__ExecuteSQL__(sql)
        accountList = [u"",]
        for i in range(len(result)):
            accountList.append(result[i][0])

        if len(accountList) <= 0:
            accountList.append("")

        return tuple(set(accountList))
#总收支表
    def AddIAPItem(self,values):
        """添加总收支表记录项目"""
        if 8 == len(values):
            try:
                values.insert(0,self.totalIncomeAndPayTableName)
                sql = "insert into '%s' values(NULL,'%s','%s','%s','%s','%s','%s','%s','%s')" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'AddAccountItem failed:',values

    def ChangedIAPItem(self,values):
        """"修改总收支表记录项目"""
        if 9 == len(values):
            try:
                values.insert(0,self.totalIncomeAndPayTableName)
                sql = "update '%s' set 'date' = '%s','realIncome' = '%s','transferIncome' = '%s','transferPay' = '%s','realPay' = '%s','account' = '%s','subtype' = '%s','description' = '%s' where id = '%s'" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'ChangedAccountItem failed:',values

    def GetAllIAPItems(self):
        """获取所有总收支表记录"""
        sql = "select * from %s order by date asc" % self.totalIncomeAndPayTableName
        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def GetIAPExistMonth(self):
        """获取总收支表中有记录的月份"""
        
        sql = "select distinct date from %s order by date desc" % (self.totalIncomeAndPayTableName)
        result = self.__ExecuteSQL__(sql)

        month = ["",]
        for item in result:
            item = item[0][0:7]
            if item not in month:
                month.append(item)

        return tuple(month)

    def GetIAPItemsForMonth(self,month):
        """按月查询所有总收支表记录"""
        sql = "select * from %s where substr(datetime(date),1,7) = '%s' order by date asc" % (self.totalIncomeAndPayTableName,month)
        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def GetIAPItemsForAlais(self,alais):
        """按账户别名查询所有总收支表记录"""
        sql = "select * from %s where account='%s' order by date asc" % (self.totalIncomeAndPayTableName,alais)
        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def GetIAPItemsForSubType(self,alais):
        """按子类型查询所有总收支表记录"""
        sql = "select * from %s where subtype='%s' order by date asc" % (self.totalIncomeAndPayTableName,alais)
        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def GetIAPItemsForDate(self,dtStart,dtEnd,alais,subType):
        """按时间查询所有总收支表记录，附带条件：账户别名，子类型"""

        sql = "select * from %s where datetime(date) >= datetime('%s') and datetime(date) <= datetime('%s') order by date asc" % (self.totalIncomeAndPayTableName,dtStart,dtEnd)

        if len(alais) > 0:
            sql = "select * from %s where datetime(date) >= datetime('%s') and datetime(date) <= datetime('%s') and account='%s' order by date asc" % (self.totalIncomeAndPayTableName,dtStart,dtEnd,alais)
        elif len(subType) > 0:
            sql = "select * from %s where datetime(date) >= datetime('%s') and datetime(date) <= datetime('%s') and subtype='%s' order by date asc" % (self.totalIncomeAndPayTableName,dtStart,dtEnd,subType)

        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def DeleteIAPItems(self,ids):
        """删除总收支表记录"""
        for i in range(0,len(ids)):
            sql = "delete from %s where id=%s" % (self.totalIncomeAndPayTableName,ids[i])
            self.__ExecuteSQL__(sql)

    def GetSubTypeList(self,type):
        """查找已经存在的总收支表中的子类型"""
        sql = "select * from %s where subtype is not null and length(subtype) <> 0" % (self.totalIncomeAndPayTableName)
        result = self.__ExecuteSQL__(sql)
        subType = ["",]
        for i in range(len(result)):
            if (0 == type) and (0 != result[i][2] or 0 != result[i][3]):
                subType.append(result[i][7])
            elif (1 == type) and (0 != result[i][4] or 0 != result[i][5]):
                subType.append(result[i][7])

        return tuple(set(subType))

#汽车费用表
    def GetCarExpensesExistMonth(self):
        """获取汽车费用表中有记录的月份"""
        sql = "select distinct date from %s order by date desc" % (self.carExpensesTableName)
        result = self.__ExecuteSQL__(sql)

        month = ["",]
        for item in result:
            item = item[0][0:7]
            if item not in month:
                month.append(item)

        return tuple(month)

    def GetExpensesTypeList(self):
        """查询汽车费用信息表,获得费用类型信息"""
        sql = "select type from %s" % (self.carExpensesTableName)
        result = self.__ExecuteSQL__(sql)
        typeList = [u"",]
        for i in range(len(result)):
            typeList.append(result[i][0])

        if len(typeList) <= 0:
            typeList.append("")

        return tuple(set(typeList))

    def AddCarExpensesItem(self,values):
        """添加汽车费用记录项目"""
        if 4 == len(values):
            try:
                values.insert(0,self.carExpensesTableName)
                sql = "insert into '%s' values(NULL,'%s','%s','%s','%s')" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'AddCarExpensesItem failed:',values

    def ChangedCarExpensesItem(self,values):
        """"修改汽车费用记录项目"""
        if 5 == len(values):
            try:
                values.insert(0,self.carExpensesTableName)
                sql = "update '%s' set 'date' = '%s','number' = '%s','type' = '%s','description' = '%s' where id = '%s'" % tuple(values)
                sql = sql.replace('\r','')
                sql = sql.replace('\n','')
                self.__ExecuteSQL__(sql)
            except:
                print __FILEDBSQLITE3__,'ChangedCarExpensesItem failed:',values

    def GetCarExpensesTypeList(self):
        """查询汽车费用信息表,获得汽车费用支出类型信息"""
        sql = "select type from %s" % (self.carExpensesTableName)
        result = self.__ExecuteSQL__(sql)
        typeList = [u"",]
        for i in range(len(result)):
            typeList.append(result[i][0])

        if len(typeList) <= 0:
            typeList.append("")

        return tuple(set(typeList))

    def GetCarExpensesItemsForConditionMonth(self,month,type):
        """根据条件进行查询:月份和支出类型,否则查全部记录"""
        if (len(month) > 0) and (len(type) > 0):
            #select * from db_xxx where substr(date(field_yyy),1,7) = '2012-07'
            sql = "select * from %s where substr(datetime(date),1,7) = '%s' and type = '%s' order by date asc" % (self.carExpensesTableName,month,type)
        elif len(month) > 0:
            sql = "select * from %s where substr(datetime(date),1,7) = '%s' order by date asc" % (self.carExpensesTableName,month)
        elif len(type) > 0:
            sql = "select * from %s where type = '%s' order by date asc" % (self.carExpensesTableName,type)
        else:
            sql = "select * from %s order by date asc" % (self.carExpensesTableName)

        result = self.__ExecuteSQL__(sql)

        return tuple(result)
    
    def GetCarExpensesItemsForConditionDate(self,dtStart,dtEnd,type):
        """根据日期条件进行查询:日期，支出类型,否则查全部记录"""
        if len(type) > 0:
            sql = "select * from %s where datetime(date) >= datetime('%s') and datetime(date) <= datetime('%s') and type = '%s' order by date asc" % (self.carExpensesTableName,dtStart,dtEnd,type)
        else:
            sql = "select * from %s where datetime(date) >= datetime('%s') and datetime(date) <= datetime('%s') order by date asc" % (self.carExpensesTableName,dtStart,dtEnd)

        result = self.__ExecuteSQL__(sql)

        return tuple(result)

    def DeleteCarExpensesItems(self,ids):
        """删除汽车费用表中记录"""
        for i in range(0,len(ids)):
            sql = "delete from %s where id=%s" % (self.carExpensesTableName,ids[i])
            self.__ExecuteSQL__(sql)

    def GetAllCarExpensesItems(self):
        """获取所有汽车费用表记录"""
        sql = "select * from %s order by date asc" % self.carExpensesTableName
        result = self.__ExecuteSQL__(sql)

        return tuple(result)
