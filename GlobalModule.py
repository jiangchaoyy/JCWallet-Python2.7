#Coding:utf-8
"""
公用全局变量
"""
import os
import sys
import DBModule

isLogin = False

#程序运行路径
home = os.path.dirname(os.path.abspath(sys.argv[0]))
home = home.decode("gbk")

#数据库路径
dataPath = os.path.join(home, 'data')
dbOperate = DBModule.DBOperateSqlite3(dataPath)
#数据库备份路径
backupPath = os.path.join(home, u'db_backup')
if not os.path.exists(backupPath):
    os.makedirs(backupPath)

#检测传入文本的编码
def GetStringCode(text):
    code = "utf-8"
    for c in ["gbk","utf-8","big-5"]:
        try:
            text.decode(c)
            code = c
            break
        except:pass

    return code

def GetBreakpoint():
    """VS2010中出异常,然后可以跟踪调试"""
    try:
        s = "中文"
        s.decode('gbk')
    except:
        pass
