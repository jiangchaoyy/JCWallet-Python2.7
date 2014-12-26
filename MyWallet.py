#Coding:utf-8
"""
使用cxfreeze打包命令：
C:\Python27\Python_EXE\MyWallet>cxfreeze MyWallet.py --target-dir dist --base-name=win32gui --icon=wallet256.ico

v2:我的钱包界面部分
更新功能：
1，数字部分可以添加负号

v3:
更新的功能：
1,添加“汽车费用”独立板块[2014-01-10]
2,总收支表:编辑时,SQL语句中实际支出和转账支出位置反了,导致错误,已经修改SQL[2014-01-12]
3,自定义事件:界面之间相互更新的问题，不能同步，比如添加新的项以后，已经存在的月份不能及时从数据返回.[2014-01-17]

发现未解决的问题：

v4:2014-03-04
更新的功能：
1，总收支表：添加按子类型查找功能
2，总收支表：按时间段查询时，附带条件：账户或子类型

v5:2014-06-24
更新功能：
1，详细收支表：导入按钮功能修改为导入部分数据，即不清空原有数据，方便每月导入信用卡数据，避免一笔一笔的添加
2, 详细收支表：导入时时间和金额的处理更完善一些，金额中的？，等替换掉

开发环境说明：
python:   2.7 - 32
wxPython: wxPython2.8-win32-unicode-2.8.12.1-py27.exe
"""

import GlobalModule
import wx
import wx.html
import os
import time
import sys
import re
import codecs

#自定义刷新事件，根据标签索引来区分
#2 创建一个事件类型
myEVT_RefreshTab = wx.NewEventType()
#3 创建一个绑定器对象
EVT_RefreshTab = wx.PyEventBinder(myEVT_RefreshTab, 1)

#1 定义事件
class RefreshTabEvent(wx.PyCommandEvent):
    """根据索引来触发标签页刷新"""

    def __init__(self, evtType, id):
        wx.PyCommandEvent.__init__(self, evtType, id)
        self.index = 0

    def GetIndex(self):
        return self.index

    def SetIndex(self, i):
        self.index = i

class cjAccountDetail(wx.Panel):
    """账户信息表"""
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)
        #顶端客户区
        self.panelHeader = wx.Panel(self,size=(-1,25))

        self.btnRefresh = wx.Button(self.panelHeader, label = u'刷新', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnRefresh_Account,self.btnRefresh)

        self.btnDelete = wx.Button(self.panelHeader, label = u'删除', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnDelete_Account,self.btnDelete)

        self.btnEdit = wx.Button(self.panelHeader, label = u'编辑', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnEdit_Account,self.btnEdit)

        self.btnLoadAccount = wx.Button(self.panelHeader, label = u'导入', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnLoadAccount,self.btnLoadAccount)
        
        self.btnExportAccount = wx.Button(self.panelHeader, label = u'导出', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnExportAccount,self.btnExportAccount)

        self.pSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pSizer.Add(self.btnRefresh, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnEdit, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnDelete, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnLoadAccount, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.pSizer.Add(self.btnExportAccount, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        self.panelHeader.SetSizer(self.pSizer)
        self.pSizer.Fit(self.panelHeader)

        self.panelLC = wx.Panel(self, -1)
        #账户信息表
        self.lcAccountItem = wx.ListCtrl(self.panelLC, wx.NewId(),style=wx.LC_REPORT,size=(-1,-1))
        self.lcAccountItem.InsertColumn(0, u"ID",width=40,format=wx.LIST_FORMAT_CENTER)
        self.lcAccountItem.InsertColumn(1, u"帐号",width=200,format=wx.LIST_FORMAT_LEFT)
        self.lcAccountItem.InsertColumn(2, u"别名",width=200,format=wx.LIST_FORMAT_CENTER)
        self.lcAccountItem.InsertColumn(3, u"银行",width=120,format=wx.LIST_FORMAT_CENTER)
        self.lcAccountItem.InsertColumn(4, u"余额",width=100,format=wx.LIST_FORMAT_CENTER)
        self.lcAccountItem.InsertColumn(5, u"备注",width=265)
        
        self.hboxLC = wx.BoxSizer(wx.HORIZONTAL)
        self.hboxLC.Add(self.lcAccountItem, 1, wx.EXPAND)
        self.panelLC.SetSizer(self.hboxLC)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.panelHeader, 0, wx.EXPAND|wx.ALL, 1)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self.panelLC, 1, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)
        
        #导入文件路径
        self.loadAccountPath = ""

        #导出文件路径
        self.exportAccountPath = ""

        self.OnRefresh_Account(None)

        self.lcAccountItem.Bind(wx.EVT_SIZE, self.OnLCAccountItemResize)

    def OnRefreshTabEvent(self,event):
        """刷新界面"""
        self.OnRefresh_Account(None)

    def OnLCAccountItemResize(self,event):
         lcWidth,lcHeight = self.lcAccountItem.GetSize()
         #print "account",lcWidth,lcHeight
         if lcWidth <= 946:
             self.lcAccountItem.SetColumnWidth(self.lcAccountItem.ColumnCount - 1,265)
         else:
             self.lcAccountItem.SetColumnWidth(self.lcAccountItem.ColumnCount - 1,(lcWidth - 21 - 660))

    #账户信息的导入导出处理:开始
    def OnLoadAccount(self,event):
        wildcard = "Text (*.txt)|*.txt|All files (*.*)|*.*"
        loadDlg = wx.FileDialog(None,u"请选择需要导入的账户信息文本文件",os.getcwd(),"",wildcard,wx.OPEN)
        retCode = loadDlg.ShowModal()
        loadDlg.Destroy()
        self.loadAccountPath = ""

        if  (wx.ID_OK == retCode):
            self.loadAccountPath = loadDlg.GetPath()
            self.Enable = False
            self.LoadAccountDoWork()
            self.Enable = True

            messDlg = wx.MessageDialog(self, u"账户信息导入完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

    def LoadAccountDoWork(self):
        """从文本文件导入账户信息到数据库"""
        import codecs
        if len(self.loadAccountPath) > 0:

            #print self.loadTotalIAPPath
            with open(self.loadAccountPath,'rb') as txtfile:
                header = txtfile.readline()
                code = GlobalModule.GetStringCode(header)
                AccountTableHeader = header.decode(code)
                
                for line in txtfile.readlines():
                    line = line.decode(code)   #文件是一ASCII码保存的,但中间有中文,实际要按GBK来处理,所以要先用GBK解码
                    items = []
                    index = 0
                    lines = line.split('\t')
                    if 6 == len(lines):
                        bIsAdd = False
                        for item in lines:
                            if len(item) > 0:
                                bIsAdd = True
                            if (item.find("\"?") > -1) or (item.find("?") > -1):
                                item = item.replace("\"","")
                                item = item.replace("?","")
                                item = item.replace(",","")
                                items.append(str(item))
                            else:
                                items.append(item)
                            if index == 4:
                                break
                            index += 1
                        #存入数据库
                        if (bIsAdd) and (5 == len(items)):
                            GlobalModule.dbOperate.AddAccountItem(items)
                        else:
                            print line

    def OnExportAccount(self,event):
        file_wildcard = "Text (*.txt)|*.txt|All files(*.*)|*.*"
        curTime = tuple(time.localtime())
        name = 'account_Backup[%04d%02d%02d%02d%02d%02d].txt' % (curTime[0],curTime[1],curTime[2],curTime[3],curTime[4],curTime[5])
        exportDlg = wx.FileDialog(self, 
                            u"文件保存到...",
                            os.getcwd(), 
                            defaultFile = name,
                            style = wx.SAVE | wx.OVERWRITE_PROMPT,  
                            wildcard = file_wildcard)  
        retCode = exportDlg.ShowModal()
        exportDlg.Destroy();
        self.exportAccountPath = ""

        if (retCode == wx.ID_OK):
            filename = exportDlg.GetPath()
            if not os.path.splitext(filename)[1]: #如果没有文件名后缀
                filename = filename + '.txt'  
            self.exportAccountPath = filename
            self.Enabled = False
            self.ExportAccountDoWork()
            self.Enabled = True

            messDlg = wx.MessageDialog(self, u"账户信息数据导出完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

    def ExportAccountDoWork(self):
        """数据库账户信息记录导出到文本文件"""
        if len(self.exportAccountPath) > 0:
            result = GlobalModule.dbOperate.GetAllAccountItems()

            content = ""
            if 0 == len(content):
                content = "%s\t%s\t%s\t%s\t%s\t" % (u'帐号',u'别名',u'银行名',u'余额',u'备注')
                content += os.linesep
                
            for i in range(len(result)):
                content += ('%s\t%s\t%s\t%s\t%s\t' % (result[i][1],result[i][2],result[i][3],result[i][4],result[i][5]))
                content += os.linesep

            with codecs.open(self.exportAccountPath,'w','utf-8') as backupfile:
                backupfile.write(content)

    def OnEdit_Account(self,event):
        index = self.lcAccountItem.GetFirstSelected()
        if -1 == index:
            return
        old = []
        for i in range(0,self.lcAccountItem.ColumnCount):
            old.append((self.lcAccountItem.GetItem(index,i)).GetText())

        #编辑
        dlgItem = AccountItemDialog(1,(self.Parent).Parent,old)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        self.OnRefreshTabEvent(None)

    def OnDelete_Account(self,event):
        """删除当前选中记录"""

        #提示确认
        dlgDelete = wx.MessageDialog(None,u"你即将删除此条记录,是否继续?",u"删除警告",wx.YES_NO | wx.ICON_QUESTION)
        retCode = dlgDelete.ShowModal()
        dlgDelete.Destroy()

        if (wx.ID_YES == retCode):
            ids = []
            for i in range(0,self.lcAccountItem.ItemCount):
                index = self.lcAccountItem.GetFirstSelected()
                if index >= 0:
                    id = (self.lcAccountItem.GetItem(index,0)).GetText()
                    if len(id) > 0:
                        ids.append(id)
                    
                    self.lcAccountItem.DeleteItem(index)

            GlobalModule.dbOperate.DeleteAccountItems(ids)

            self.OnRefreshTabEvent(None)

    def Refresh_Account(self,result):
        """更新ListCtrl中的数据"""
        #清空原来的
        self.lcAccountItem.DeleteAllItems()
        curBalance = 0
        for i in range(len(result)):
            index = self.lcAccountItem.InsertStringItem(sys.maxint,str(result[i][0]))
            for j in range(1,len(result[i])):
                if (4 == j):
                    self.lcAccountItem.SetStringItem(index,j,str(result[i][j]))
                    curBalance += float(result[i][j])
                else:
                    self.lcAccountItem.SetStringItem(index,j,(result[i][j]))

            if (0 == index % 2):
                self.lcAccountItem.SetItemBackgroundColour(index,wx.LIGHT_GREY)

        index = self.lcAccountItem.InsertStringItem(sys.maxint,"")
        self.lcAccountItem.SetStringItem(index,3,u"总资产")
        self.lcAccountItem.SetStringItem(index,4,str(curBalance))

    def OnRefresh_Account(self,event):
        """账户信息:显示全部记录"""
        result = GlobalModule.dbOperate.GetAllAccountItems()
        self.Refresh_Account(result)

class cjTotalIncomeAndPay(wx.Panel):
    """总收支表"""
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)
        #顶端客户区
        self.panelHeader = wx.Panel(self,size=(-1,25))

        self.startDate_l = wx.StaticText(self.panelHeader,-1,u"开始",size=(25,16))
        self.startDate_t = wx.GenericDatePickerCtrl(self.panelHeader, dt=wx.DateTime(), size=(120, 25), style=wx.DP_DROPDOWN|
                    wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)

        self.endDate_l = wx.StaticText(self.panelHeader,-1,u"结束",size=(25,16))
        self.endDate_t = wx.GenericDatePickerCtrl(self.panelHeader, dt=wx.DateTime(), size=(120, 25), style=wx.DP_DROPDOWN|
                    wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)

        self.btnSearch = wx.Button(self.panelHeader, label = u'查询', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnSearch_TIAP,self.btnSearch)

        self.btnAllSearch = wx.Button(self.panelHeader, label = u'全部记录', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnAllSearch_TIAP,self.btnAllSearch)

        self.btnEdit = wx.Button(self.panelHeader, label = u'编辑', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnEdit_TIAP,self.btnEdit)

        self.btnDelete = wx.Button(self.panelHeader, label = u'删除', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnDelete_TIAP,self.btnDelete)

        self.cbMonthSearch_l = wx.StaticText(self.panelHeader,-1,u"按月查看",size=(50,16))
        self.listMonthSearch = list(GlobalModule.dbOperate.GetIAPExistMonth())
        self.cbMonthSearch = wx.ComboBox(self.panelHeader, -1, self.listMonthSearch[0], (100,25), choices=self.listMonthSearch, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX,self.OnMonthSearch,self.cbMonthSearch)
        
        self.btnLoadTotalIAP = wx.Button(self.panelHeader, label = u'导入', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnLoadTotalIAP,self.btnLoadTotalIAP)
        
        self.btnExportTotalIAP = wx.Button(self.panelHeader, label = u'导出', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnExportTotalIAP,self.btnExportTotalIAP)

        self.pSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pSizer.Add(self.cbMonthSearch_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.cbMonthSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.startDate_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.startDate_t, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.endDate_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.endDate_t, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnAllSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnEdit, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnDelete, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnLoadTotalIAP, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.pSizer.Add(self.btnExportTotalIAP, 0, wx.ALIGN_LEFT|wx.ALL, 5)

        self.panelHeader.SetSizer(self.pSizer)
        self.pSizer.Fit(self.panelHeader)
        
        #顶端状态区
        self.pnHeaderStatus = wx.Panel(self,size=(-1,16))
        self.curIncomeText_l = wx.StaticText(self.pnHeaderStatus,-1,u"收入:",size=(40,16))
        self.curIncomeText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(100,16))
        self.curIncomeText_s.SetBackgroundColour(wx.LIGHT_GREY)
        self.curPayText_l = wx.StaticText(self.pnHeaderStatus,-1,u"支出:",size=(40,16))
        self.curPayText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(100,16))
        self.curPayText_s.SetBackgroundColour(wx.LIGHT_GREY)
        self.curBalanceText_l = wx.StaticText(self.pnHeaderStatus,-1,u"余额:",size=(40,16))
        self.curBalanceText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(100,16))
        self.curBalanceText_s.SetBackgroundColour(wx.LIGHT_GREY)
        #wx.CheckBox(panel, -1, "Alpha", (35, 40), (150, 20))
        #radio1 = wx.RadioButton(panel, -1, u"按账户查看", pos=(20, 50), style=wx.RB_GROUP)
        #radio2 = wx.RadioButton(panel, -1, u"按子类型查看",size=(50,16))
        self.radioAccountAliasSearch = wx.RadioButton(self.pnHeaderStatus, -1, u"按账户查看", size=(80, 16), style=wx.RB_GROUP)
        self.radioAccountAliasSearch.SetValue(True);
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRadioEvent, self.radioAccountAliasSearch)
        self.listAccountAlias = list(GlobalModule.dbOperate.GetAccountAliasList())
        self.cbAccountAliasSearch = wx.ComboBox(self.pnHeaderStatus, -1, self.listAccountAlias[0], (100,25), choices=self.listAccountAlias, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX,self.OnAccountAliasSearch,self.cbAccountAliasSearch)
        
        self.radioSubTypeSearch = wx.RadioButton(self.pnHeaderStatus, -1, u"按子类型查看",size=(100,16))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnRadioEvent, self.radioSubTypeSearch)
        self.listSubType = list(GlobalModule.dbOperate.GetSubTypeList(0))
        self.listSubType.extend(list(GlobalModule.dbOperate.GetSubTypeList(1)))
        self.cbSubTypeSearch = wx.ComboBox(self.pnHeaderStatus, -1, self.listSubType[0], (100,25), choices=self.listSubType, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.cbSubTypeSearch.Enabled = False;
        self.Bind(wx.EVT_COMBOBOX,self.OnSubTypeSearch,self.cbSubTypeSearch)

        self.pHStatusSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pHStatusSizer.Add(self.curIncomeText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curIncomeText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curPayText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curPayText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curBalanceText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curBalanceText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.radioAccountAliasSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.cbAccountAliasSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.radioSubTypeSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.cbSubTypeSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.pnHeaderStatus.SetSizer(self.pHStatusSizer)
        self.pHStatusSizer.Fit(self.pnHeaderStatus)

        self.panelLC = wx.Panel(self, -1)
        #总收支表
        self.lcIncomeAndPay = wx.ListCtrl(self.panelLC, wx.NewId(),style=wx.LC_REPORT,size=(-1,-1))
        self.lcIncomeAndPay.InsertColumn(0, u"ID",width=40,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPay.InsertColumn(1, u"日期",width=80,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPay.InsertColumn(2, u"实际收入",width=70,format=wx.LIST_FORMAT_RIGHT)
        self.lcIncomeAndPay.InsertColumn(3, u"转账收入",width=70,format=wx.LIST_FORMAT_RIGHT)
        self.lcIncomeAndPay.InsertColumn(4, u"转账支出",width=70,format=wx.LIST_FORMAT_RIGHT)
        self.lcIncomeAndPay.InsertColumn(5, u"实际支出",width=70,format=wx.LIST_FORMAT_RIGHT)
        self.lcIncomeAndPay.InsertColumn(6, u"当前余额",width=80,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPay.InsertColumn(7, u"账户",width=120,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPay.InsertColumn(8, u"子类型",width=100,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPay.InsertColumn(9, u"备注",width=200)

        self.hboxLC = wx.BoxSizer(wx.HORIZONTAL)
        self.hboxLC.Add(self.lcIncomeAndPay, 1, wx.EXPAND)
        self.panelLC.SetSizer(self.hboxLC)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.panelHeader, 0, wx.EXPAND|wx.ALL, 1)
        self.sizer.Add(self.pnHeaderStatus, 0, wx.EXPAND|wx.ALL, 1)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self.panelLC, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        #导入文件路径
        self.loadTotalIAPPath = ""

        #导出文件路径
        self.exportTotalIAPPath = ""

        self.OnMonthSearch(None)

        self.lcIncomeAndPay.Bind(wx.EVT_SIZE, self.OnLCIncomeAndPayResize)

    def OnRefreshTabEvent(self,event):
        """刷新界面"""
        self.cbMonthSearch.SetItems(list(GlobalModule.dbOperate.GetIAPExistMonth()))
        self.OnAllSearch_TIAP(None)

    def OnLCIncomeAndPayResize(self,event):
         lcWidth,lcHeight = self.lcIncomeAndPay.GetSize()

         if lcWidth <= 946:
             self.lcIncomeAndPay.SetColumnWidth(self.lcIncomeAndPay.ColumnCount - 1,225)
         else:
             self.lcIncomeAndPay.SetColumnWidth(self.lcIncomeAndPay.ColumnCount - 1,(lcWidth - 21 - 620 - 80))

    #总收支表的导入导出处理:开始
    def OnLoadTotalIAP(self,event):
        wildcard = u"Text (*.txt)|*.txt|All files (*.*)|*.*"
        loadDlg = wx.FileDialog(None,u"请选择需要导入的总收支表文本文件",os.getcwd(),"",wildcard,wx.OPEN)

        retCode = loadDlg.ShowModal()
        loadDlg.Destroy()
        self.loadTotalIAPPath = ""

        if  (wx.ID_OK == retCode):
            self.loadTotalIAPPath = loadDlg.GetPath()
            self.Enable = False
            self.LoadTotalIAPDoWork()
            self.Enable = True

            messDlg = wx.MessageDialog(self, u"总收支表导入完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

    def LoadTotalIAPDoWork(self):
        """从文本文件导入总收支表到数据库"""
        import codecs
        if len(self.loadTotalIAPPath) > 0:

            #print self.loadTotalIAPPath
            with open(self.loadTotalIAPPath,'rb') as txtfile:
                text = txtfile.readline()
                code = GlobalModule.GetStringCode(text)
                totalTableHeader = (text.decode(code))
                #totalTableHeader += ((txtfile.readline()).decode(code))

                date = ""
                for line in txtfile.readlines():
                    line = line.replace('\r\n','')
                    line = line.decode(code)   #文件是一ASCII码保存的,但中间有中文,实际要按GBK来处理,所以要先用GBK解码,文件有可能是utf-8的,所有先要查看编码,然后再解码
                    items = []
                    index = 0
                    lines = line.split('\t')
                    if len(lines) >= 9:
                        bIsAdd = False
                        for item in lines:
                            if len(item) > 0:
                                bIsAdd = True
                            if 5 == index:
                                index += 1
                                continue
                            if (0 == index):
                                if (len(item) > 0):
                                    date = (((item.split(' '))[0]).replace(u'年','-').replace(u'月','-').replace(u'日','-')).split('-')
                                    date = "%04d-%02d-%02d" % (int(date[0]),int(date[1]),int(date[2]))
                                items.append(date)
                            elif (item.find("\"?") > -1) or (item.find("?") > -1):
                                item = item.replace("\"","")
                                item = item.replace("?","")
                                item = item.replace(",","")
                                items.append(str(item))
                            elif (0 == len(item)) and (1 <= index <= 4):
                                items.append("0")
                            else:
                                items.append(item)
                            if index == 8:
                                break
                            index += 1
                        #存入数据库
                        if (bIsAdd) and (8 == len(items)):
                            if ("0" != items[2]) or ("0" != items[3]) or ("0" != items[4]) or ("0" != items[5]):
                                GlobalModule.dbOperate.AddIAPItem(items)
                        else:
                            print line

    def OnExportTotalIAP(self,event):
        file_wildcard = "Text (*.txt)|*.txt|All files(*.*)|*.*"
        curTime = tuple(time.localtime())
        name = 'totalIAP_Backup[%04d%02d%02d%02d%02d%02d].txt' % (curTime[0],curTime[1],curTime[2],curTime[3],curTime[4],curTime[5])
        exportDlg = wx.FileDialog(self, 
                            u"文件保存到...",
                            os.getcwd(), 
                            defaultFile = name,
                            style = wx.SAVE | wx.OVERWRITE_PROMPT,  
                            wildcard = file_wildcard)  
        retCode = exportDlg.ShowModal()
        exportDlg.Destroy();
        self.exportTotalIAPPath = ""

        if (retCode == wx.ID_OK):
            filename = exportDlg.GetPath()
            if not os.path.splitext(filename)[1]: #如果没有文件名后缀  
                filename = filename + '.txt'
            self.exportTotalIAPPath = filename
            self.Enabled = False
            self.ExportTotalIAPDoWork()
            self.Enabled = True

            messDlg = wx.MessageDialog(self, u"总收支表数据导出完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

    def ExportTotalIAPDoWork(self):
        """数据库总收支表记录导出到文本文件"""
        if len(self.exportTotalIAPPath) > 0:
            result = GlobalModule.dbOperate.GetAllIAPItems()

            content = ""
            if 0 == len(content):
                content = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t' % (u'日期',u'实际收入',u'转账收入',u'转账支出',u'实际支出',u'余额',u'账户',u'子类型',u'备注')
                content += os.linesep

            for i in range(len(result)):
                content += ('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t' % (result[i][1],result[i][2],result[i][3],result[i][4],result[i][5],'',result[i][6],result[i][7],result[i][8]))
                content += os.linesep

            with codecs.open(self.exportTotalIAPPath,'w','utf-8') as backupfile:
                backupfile.write(content)

    def OnMonthSearch(self,event):
        month = self.cbMonthSearch.GetValue()
        
        if len(month) > 0:
            result = GlobalModule.dbOperate.GetIAPItemsForMonth(month)
            self.Refresh_TIAP(result)
        else:
            self.OnAllSearch_TIAP(None)

    def OnRadioEvent(self, event):
        self.cbAccountAliasSearch.Enabled = self.radioAccountAliasSearch.GetValue()
        self.cbSubTypeSearch.Enabled = self.radioSubTypeSearch.GetValue()

    def OnEdit_TIAP(self,event):
        index = self.lcIncomeAndPay.GetFirstSelected()
        if -1 == index:
            return

        oldItem = []
        for i in range(0,self.lcIncomeAndPay.ColumnCount):
            oldItem.append((self.lcIncomeAndPay.GetItem(index,i)).GetText())

        type = 0
        if (oldItem[4] != '0.0') or (oldItem[5] != '0.0'):
            type = 1

        dlgItem = IAPItemDialog(type,(self.Parent).Parent,oldItem,1)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        self.OnRefreshTabEvent(None)

    def OnDelete_TIAP(self,event):
        """删除当前选中记录"""

        #提示确认
        dlgDelete = wx.MessageDialog(None,u"你即将删除此条记录,是否继续?",u"删除警告",wx.YES_NO | wx.ICON_QUESTION)
        retCode = dlgDelete.ShowModal()
        dlgDelete.Destroy()

        if (wx.ID_YES == retCode):
            ids = []
            for i in range(0,self.lcIncomeAndPay.ItemCount):
                index = self.lcIncomeAndPay.GetFirstSelected()
                if index >= 0:
                    id = (self.lcIncomeAndPay.GetItem(index,0)).GetText()
                    if len(id) > 0:
                        ids.append(id)

                    self.lcIncomeAndPay.DeleteItem(index)

            GlobalModule.dbOperate.DeleteIAPItems(ids)

            self.OnRefreshTabEvent(None)

    def Refresh_TIAP(self,result):
        """更新ListCtrl中的数据"""
        #清空原来的
        self.lcIncomeAndPay.DeleteAllItems()
        curBalance = 0.0
        curIncome = 0.0
        curPay = 0.0
        for i in range(len(result)):
            index = self.lcIncomeAndPay.InsertStringItem(0,str(result[i][0]))
            for j in range(1,len(result[i])):
                if j >= 6:
                    self.lcIncomeAndPay.SetStringItem(index,j + 1,(result[i][j]))
                else:
                    self.lcIncomeAndPay.SetStringItem(index,j,str(result[i][j]))

            if (0 == self.lcIncomeAndPay.ItemCount % 2):
                self.lcIncomeAndPay.SetItemBackgroundColour(index,wx.LIGHT_GREY)
            #计算当前余额
            curBalance = curBalance + float(result[i][2]) + float(result[i][3]) - float(result[i][4]) - float(result[i][5])
            if abs(curBalance) < 0.001:
                curBalance = 0
            self.lcIncomeAndPay.SetStringItem(index,6,str(curBalance))

            curIncome += float(result[i][2])
            curPay += float(result[i][5])

        self.curIncomeText_s.SetLabel(str(curIncome))
        self.curPayText_s.SetLabel(str(curPay))
        self.curBalanceText_s.SetLabel(str(curBalance))
        
        if (curBalance < 0):
            self.curBalanceText_s.SetForegroundColour(wx.RED)
        else:
            self.curBalanceText_s.SetForegroundColour(wx.BLACK)

    def OnAccountAliasSearch(self,event):
        """总收支表:按账户信息显示"""
        alais = self.cbAccountAliasSearch.GetValue()
        if len(alais) > 0:
            result = GlobalModule.dbOperate.GetIAPItemsForAlais(alais)
            self.Refresh_TIAP(result)
        else:
            self.OnAllSearch_TIAP(event)

    def OnSubTypeSearch(self,event):
        """总收支表:按子类型显示"""
        alais = self.cbSubTypeSearch.GetValue()
        if len(alais) > 0:
            result = GlobalModule.dbOperate.GetIAPItemsForSubType(alais)
            self.Refresh_TIAP(result)
        else:
            self.OnAllSearch_TIAP(event)

    def OnAllSearch_TIAP(self,event):
        """总收支表:显示全部记录"""
        result = GlobalModule.dbOperate.GetAllIAPItems()
        self.Refresh_TIAP(result)

    def OnSearch_TIAP(self,event):
        """总收支表:查询按钮处理函数"""
        dtStart = "%4d-%02d-%02d" % (self.startDate_t.GetValue().GetYear(),self.startDate_t.GetValue().GetMonth() + 1,self.startDate_t.GetValue().GetDay())
        dtEnd = "%4d-%02d-%02d" % (self.endDate_t.GetValue().GetYear(),self.endDate_t.GetValue().GetMonth() + 1,self.endDate_t.GetValue().GetDay())
        alais = ""
        subType = ""

        if self.radioAccountAliasSearch.GetValue():
            alais = self.cbAccountAliasSearch.GetValue()
        elif self.radioSubTypeSearch.GetValue():
            subType = self.cbSubTypeSearch.GetValue()

        result = GlobalModule.dbOperate.GetIAPItemsForDate(dtStart,dtEnd,alais,subType)
        self.Refresh_TIAP(result)

class cjTotalIncomeAndPayDetail(wx.Panel):
    """详细收支表"""
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)
        #顶端客户区
        self.panelHeader = wx.Panel(self,size=(-1,25))

        self.startDate_l = wx.StaticText(self.panelHeader,-1,u"开始",size=(25,16))
        self.startDate_t = wx.GenericDatePickerCtrl(self.panelHeader, dt=wx.DateTime(), size=(120, 25), style=wx.DP_DROPDOWN|
                    wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)

        self.endDate_l = wx.StaticText(self.panelHeader,-1,u"结束",size=(25,16))
        self.endDate_t = wx.GenericDatePickerCtrl(self.panelHeader, dt=wx.DateTime(), size=(120, 25), style=wx.DP_DROPDOWN|
                    wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)

        self.btnSearch = wx.Button(self.panelHeader, label = u'查询', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnSearch_TIAPDetail,self.btnSearch)

        self.btnAllSearch = wx.Button(self.panelHeader, label = u'全部记录', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnAllSearch_TIAPDetail,self.btnAllSearch)

        self.btnEdit = wx.Button(self.panelHeader, label = u'编辑', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnEdit_TIAPDetail,self.btnEdit)

        self.btnDelete = wx.Button(self.panelHeader, label = u'删除', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnDelete_TIAPDetail,self.btnDelete)
        
        self.cbMonthSearch_l = wx.StaticText(self.panelHeader,-1,u"按月查看",size=(50,16))
        self.listMonthSearch = list(GlobalModule.dbOperate.GetDetailIAPExistMonth())
        self.cbMonthSearch = wx.ComboBox(self.panelHeader, -1, self.listMonthSearch[0], (100,25), choices=self.listMonthSearch, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX,self.OnMonthSearchDetail,self.cbMonthSearch)
        
        self.btnLoadTotalIAP = wx.Button(self.panelHeader, label = u'导入', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnLoadTotalIAPDetail,self.btnLoadTotalIAP)
        
        self.btnExportTotalIAP = wx.Button(self.panelHeader, label = u'导出', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnExportTotalIAPDetail,self.btnExportTotalIAP)

        self.pSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pSizer.Add(self.cbMonthSearch_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.cbMonthSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.startDate_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.startDate_t, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.endDate_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.endDate_t, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnAllSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnEdit, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnDelete, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnLoadTotalIAP, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.pSizer.Add(self.btnExportTotalIAP, 0, wx.ALIGN_LEFT|wx.ALL, 5)
                
        self.panelHeader.SetSizer(self.pSizer)
        self.pSizer.Fit(self.panelHeader)

        #顶端状态区
        self.pnHeaderStatus = wx.Panel(self,size=(-1,16))
        self.curIncomeText_l = wx.StaticText(self.pnHeaderStatus,-1,u"收入:",size=(40,16))
        self.curIncomeText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(120,16))
        self.curIncomeText_s.SetBackgroundColour(wx.LIGHT_GREY)
        self.curPayText_l = wx.StaticText(self.pnHeaderStatus,-1,u"支出:",size=(40,16))
        self.curPayText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(120,16))
        self.curPayText_s.SetBackgroundColour(wx.LIGHT_GREY)
        self.curBalanceText_l = wx.StaticText(self.pnHeaderStatus,-1,u"余额:",size=(40,16))
        self.curBalanceText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(120,16))
        self.curBalanceText_s.SetBackgroundColour(wx.LIGHT_GREY)

        self.cbAccountAliasSearch_l = wx.StaticText(self.pnHeaderStatus,-1,u"按账户查看",size=(50,16))
        self.listAccountAlias = list(GlobalModule.dbOperate.GetAccountAliasList())
        self.cbAccountAliasSearch = wx.ComboBox(self.pnHeaderStatus, -1, self.listAccountAlias[0], (100,25), choices=self.listAccountAlias, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX,self.OnAccountAliasSearch,self.cbAccountAliasSearch)

        self.pHStatusSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pHStatusSizer.Add(self.curIncomeText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curIncomeText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curPayText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curPayText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curBalanceText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curBalanceText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.cbAccountAliasSearch_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.cbAccountAliasSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.pnHeaderStatus.SetSizer(self.pHStatusSizer)
        self.pHStatusSizer.Fit(self.pnHeaderStatus)

        self.panelLC = wx.Panel(self, -1)
        #详细收支表
        self.lcIncomeAndPayDetail = wx.ListCtrl(self.panelLC, wx.NewId(),style=wx.LC_REPORT,size=(-1,-1))
        self.lcIncomeAndPayDetail.InsertColumn(0, u"ID",width=40,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPayDetail.InsertColumn(1, u"日期",width=100,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPayDetail.InsertColumn(2, u"金额",width=100,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPayDetail.InsertColumn(3, u"账户",width=115,format=wx.LIST_FORMAT_CENTER)
        self.lcIncomeAndPayDetail.InsertColumn(4, u"备注",width=570)

        self.hboxLC = wx.BoxSizer(wx.HORIZONTAL)
        self.hboxLC.Add(self.lcIncomeAndPayDetail, 1, wx.EXPAND)
        self.panelLC.SetSizer(self.hboxLC)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.panelHeader, 0, wx.EXPAND|wx.ALL, 1)
        self.sizer.Add(self.pnHeaderStatus, 0, wx.EXPAND|wx.ALL, 1)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self.panelLC, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        #导入文件路径
        self.loadPath = ""

        #导出文件路径
        self.exportPath = ""

        self.lcIncomeAndPayDetail.Bind(wx.EVT_SIZE, self.OnlcIncomeAndPayDetailResize)

        self.OnMonthSearchDetail(None)

    def OnRefreshTabEvent(self,event):
        """刷新界面"""
        self.cbMonthSearch.SetItems(list(GlobalModule.dbOperate.GetDetailIAPExistMonth()))
        self.OnAllSearch_TIAPDetail(None)

    def OnlcIncomeAndPayDetailResize(self,event):
         lcWidth,lcHeight = self.lcIncomeAndPayDetail.GetSize()

         if lcWidth <= 946:
             self.lcIncomeAndPayDetail.SetColumnWidth(4,570)
         else:
             self.lcIncomeAndPayDetail.SetColumnWidth(4,(lcWidth - 21 - 355))

    def OnLoadTotalIAPDetail(self,event):
        wildcard = "Text (*.txt)|*.txt|All files (*.*)|*.*"
        loadDlg = wx.FileDialog(None,u"请选择需要导入的详细收支表文本文件",os.getcwd(),"",wildcard,wx.OPEN)
        retCode = loadDlg.ShowModal()
        loadDlg.Destroy()
        self.loadPath = ""

        if  (wx.ID_OK == retCode):
            self.loadPath = loadDlg.GetPath()
            self.Enable = False
            self.LoadTotalIAPDetailDoWork()
            self.Enable = True

            messDlg = wx.MessageDialog(self, u"详细收支表导入完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

            self.OnAllSearch_TIAPDetail(None)

    def LoadTotalIAPDetailDoWork_Excel(self):
        """从Excel文件导入详细收支表到数据库，暂时未使用"""
        
        if len(self.loadPath) > 0:
            
            with open(self.loadPath,'rb') as txtfile:
                text = txtfile.readline()
                code = GlobalModule.GetStringCode(text)
                
                date = ""
                for line in txtfile.readlines():
                    line = line.decode(code)   #文件是一ASCII码保存的,但中间有中文,实际要按GBK来处理,所以要先用GBK解码
                    items = []
                    index = 0
                    lines = line.split('\t')
                    
                    if len(lines) >= 8:
                        bIsAdd = False
                        for item in lines:
                            if len(item) > 0:
                                bIsAdd = True
                            if (0 == index):
                                if (len(item) > 0):
                                    date = (((item.split(' '))[0]).replace(u'年','-').replace(u'月','-').replace(u'日','-')).split('-')
                                    date = "%04d-%02d-%02d" % (int(date[0]),int(date[1]),int(date[2]))
                                items.append(date)
                            elif (item.find("\"?") > -1) or (item.find("?") > -1):
                                item = item.replace("\"","")
                                item = item.replace("?","")
                                item = item.replace(",","")
                                items.append(str(item))
                            elif (0 == len(item)) and (1 <= index <= 6):
                                items.append("0")
                            else:
                                items.append(item)
                            if index == 7:
                                break
                            index += 1
                        #存入数据库
                        if (bIsAdd) and (9 <= len(items)):

                            sqlLine = []
                            sqlLine.append(items[0])
                            sqlLine.append(items[1])
                            if items[2] != '0':
                                continue
                            elif items[3] != '0':
                                sqlLine.append((str(items[3])).replace('(',"").replace(')',''))
                                sqlLine.append(u'')
                            elif items[4] != '0':
                                sqlLine.append((str(items[4])).replace('(',"").replace(')',''))
                                sqlLine.append(u'我交行信用卡')
                            elif items[5] != '0':
                                sqlLine.append((str(items[5])).replace('(',"").replace(')',''))
                                sqlLine.append(u'我中行信用卡')
                            elif items[6] != '0':
                                sqlLine.append((str(items[6])).replace('(',"").replace(')',''))
                                sqlLine.append(u'她中行信用卡')
                            elif items[7] != '0':
                                sqlLine.append((str(items[7])).replace('(',"").replace(')',''))
                                sqlLine.append(u'她交行信用卡')
                            
                            sqlLine.append(items[8])

                            if 4 == len(sqlLine):
                                GlobalModule.dbOperate.AddDetailIAPItem(sqlLine)
                            else:
                                print sqlLine
                        else:
                            print line

    def LoadTotalIAPDetailDoWork(self):
        """从文本文件导入详细收支表到数据库:将此文件内容追加到数据中，并不删除原来的数据，适合导入每月数据"""
        if len(self.loadPath) > 0:
            
            with open(self.loadPath,'rb') as txtfile:
                text = txtfile.readline()
                code = GlobalModule.GetStringCode(text)
                
                date = ""
                for line in txtfile.readlines():
                    line = line.decode(code)   #文件是一ASCII码保存的,但中间有中文,实际要按GBK来处理,所以要先用GBK解码
                    items = []
                    index = 0
                    lines = line.split('\t')
                    
                    if len(lines) >= 4:
                        bIsAdd = False
                        for item in lines:
                            if len(item) > 0:
                                bIsAdd = True
                            if (0 == index):
                                if (len(item) > 0):
                                    date = (((item.split(' '))[0]).replace('/','-').replace(u'年','-').replace(u'月','-').replace(u'日','-')).split('-')
                                    date = "%04d-%02d-%02d" % (int(date[0]),int(date[1]),int(date[2]))
                                items.append(date)
                            elif (item.find("\"?") > -1) or (item.find("?") > -1):
                                item = item.replace("\"","")
                                item = item.replace("?","")
                                item = item.replace(",","")
                                items.append(str(item))
                            elif (0 == len(item)) and (1 == index):
                                items.append("0")
                            else:
                                items.append(item)
                            if index == 3:
                                break
                            index += 1
                        #存入数据库
                        if (bIsAdd) and (4 == len(items)):
                            GlobalModule.dbOperate.AddDetailIAPItem(items)
                        else:
                            print line

    def OnExportTotalIAPDetail(self,event):
        file_wildcard = "Text (*.txt)|*.txt|All files(*.*)|*.*"
        curTime = tuple(time.localtime())
        name = 'totalIAPDetail_Backup[%04d%02d%02d%02d%02d%02d].txt' % (curTime[0],curTime[1],curTime[2],curTime[3],curTime[4],curTime[5])
        exportDlg = wx.FileDialog(self, 
                            u"文件保存到...",  
                            os.getcwd(), 
                            defaultFile = name,
                            style = wx.SAVE | wx.OVERWRITE_PROMPT,  
                            wildcard = file_wildcard)  
        retCode = exportDlg.ShowModal()
        exportDlg.Destroy();
        self.exportPath = ""

        if (retCode == wx.ID_OK):
            filename = exportDlg.GetPath()
            if not os.path.splitext(filename)[1]: #如果没有文件名后缀  
                filename = filename + '.txt'  
            self.exportPath = filename
            self.Enabled = False
            self.ExportTotalIAPDetailDoWork()
            self.Enabled = True

            messDlg = wx.MessageDialog(self, u"详细收支表数据导出完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

    def ExportTotalIAPDetailDoWork(self):
        """数据库详细收支表记录导出到文本文件"""
        if len(self.exportPath) > 0:
            result = GlobalModule.dbOperate.GetAllDetailIAPItems()

            content = ""
            if 0 == len(content):
                content = '%s\t%s\t%s\t%s\t' % (u'日期',u'金额',u'账户',u'备注')
                content += os.linesep
                
            for i in range(len(result)):
                content += ('%s\t%s\t%s\t%s\t' % (result[i][1],result[i][2],result[i][3],result[i][4]))
                content += os.linesep

            with codecs.open(self.exportPath,'w','utf-8') as backupfile:
                backupfile.write(content)

    def OnAccountAliasSearch(self,event):
        """详细收支表:按账户信息显示"""
        self.OnAllSearch_TIAPDetail(None)

    def OnMonthSearchDetail(self,event):

        self.OnAllSearch_TIAPDetail(None)

    def OnEdit_TIAPDetail(self,event):
        index = self.lcIncomeAndPayDetail.GetFirstSelected()
        old = []
        for i in range(0,self.lcIncomeAndPayDetail.ColumnCount):
            old.append((self.lcIncomeAndPayDetail.GetItem(index,i)).GetText())

        dlgItem = DetailIAPItemDialog(1,(self.Parent).Parent,old)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        self.OnRefreshTabEvent(None)

    def OnDelete_TIAPDetail(self,event):
        """删除当前选中记录"""

        #提示确认
        dlgDelete = wx.MessageDialog(None,u"你即将删除此条记录,是否继续?",u"删除警告",wx.YES_NO | wx.ICON_QUESTION)
        retCode = dlgDelete.ShowModal()
        dlgDelete.Destroy()

        if (wx.ID_YES == retCode):
            ids = []
            for i in range(0,self.lcIncomeAndPayDetail.ItemCount):
                index = self.lcIncomeAndPayDetail.GetFirstSelected()
                if index >= 0:
                    id = (self.lcIncomeAndPayDetail.GetItem(index,0)).GetText()
                    if len(id) > 0:
                        ids.append(id)

                    self.lcIncomeAndPayDetail.DeleteItem(index)

            GlobalModule.dbOperate.DeleteDetailIAPItems(ids)
            self.OnRefreshTabEvent(None)

    def Refresh_TIAPDetail(self,result):
        """更新ListCtrl中的数据"""
        #清空原来的
        self.lcIncomeAndPayDetail.DeleteAllItems()
        curBalance = 0.0
        for i in range(len(result)):
            index = self.lcIncomeAndPayDetail.InsertStringItem(0,str(result[i][0]))
            for j in range(1,len(result[i])):
                if j == 2:
                    self.lcIncomeAndPayDetail.SetStringItem(index,j,str(result[i][j]))
                else:
                    self.lcIncomeAndPayDetail.SetStringItem(index,j,(result[i][j]))

            if (0 == self.lcIncomeAndPayDetail.ItemCount % 2):
                self.lcIncomeAndPayDetail.SetItemBackgroundColour(index,wx.LIGHT_GREY)
            #计算当前余额
            curBalance = curBalance + float((str(result[i][2])).replace('(','').replace(')',''))

        self.curBalanceText_s.SetLabel(str(curBalance))

        if (curBalance < 0):
            self.curBalanceText_s.SetForegroundColour(wx.RED)
        else:
            self.curBalanceText_s.SetForegroundColour(wx.BLACK)

    def OnAllSearch_TIAPDetail(self,event):
        """详细收支表:显示全部记录"""

        month = self.cbMonthSearch.GetValue()
        alais = self.cbAccountAliasSearch.GetValue()

        result = GlobalModule.dbOperate.GetDetailIAPItemsForConditionMonth(month,alais)
        self.Refresh_TIAPDetail(result)

    def OnSearch_TIAPDetail(self,event):
        """详细收支表:查询按钮处理函数"""
        dtStart = "%4d-%02d-%02d" % (self.startDate_t.GetValue().GetYear(),self.startDate_t.GetValue().GetMonth() + 1,self.startDate_t.GetValue().GetDay())
        dtEnd = "%4d-%02d-%02d" % (self.endDate_t.GetValue().GetYear(),self.endDate_t.GetValue().GetMonth() + 1,self.endDate_t.GetValue().GetDay())

        alais = self.cbAccountAliasSearch.GetValue()
        result = GlobalModule.dbOperate.GetDetailIAPItemsForConditionDate(dtStart,dtEnd,alais)
        self.Refresh_TIAPDetail(result)

class cjCarExpenses(wx.Panel):
    """汽车费用记录"""
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)
        #顶端客户区
        self.panelHeader = wx.Panel(self,size=(-1,25))

        self.startDate_l = wx.StaticText(self.panelHeader,-1,u"开始",size=(25,16))
        self.startDate_t = wx.GenericDatePickerCtrl(self.panelHeader, dt=wx.DateTime(), size=(120, 25), style=wx.DP_DROPDOWN|
                    wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)

        self.endDate_l = wx.StaticText(self.panelHeader,-1,u"结束",size=(25,16))
        self.endDate_t = wx.GenericDatePickerCtrl(self.panelHeader, dt=wx.DateTime(), size=(120, 25), style=wx.DP_DROPDOWN|
                    wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)

        self.btnSearch = wx.Button(self.panelHeader, label = u'查询', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnSearch_CarExpensesDetail,self.btnSearch)

        self.btnAllSearch = wx.Button(self.panelHeader, label = u'全部记录', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnAllSearch_CarExpensesDetail,self.btnAllSearch)

        self.btnEdit = wx.Button(self.panelHeader, label = u'编辑', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnEdit_CarExpensesDetail,self.btnEdit)

        self.btnDelete = wx.Button(self.panelHeader, label = u'删除', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnDelete_CarExpensesDetail,self.btnDelete)
        
        self.cbMonthSearch_l = wx.StaticText(self.panelHeader,-1,u"按月查看",size=(50,16))
        self.listMonthSearch = list(GlobalModule.dbOperate.GetCarExpensesExistMonth())
        self.cbMonthSearch = wx.ComboBox(self.panelHeader, -1, self.listMonthSearch[0], (100,25), choices=self.listMonthSearch, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX,self.OnMonthSearchDetail,self.cbMonthSearch)
        
        self.btnLoadTotalIAP = wx.Button(self.panelHeader, label = u'导入', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnLoadCarExpensesDetail,self.btnLoadTotalIAP)
        
        self.btnExportTotalIAP = wx.Button(self.panelHeader, label = u'导出', size = (60, 25))
        self.Bind(wx.EVT_BUTTON,self.OnExportCarExpensesDetail,self.btnExportTotalIAP)

        self.pSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pSizer.Add(self.cbMonthSearch_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.cbMonthSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.startDate_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.startDate_t, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.endDate_l, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
        self.pSizer.Add(self.endDate_t, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnAllSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnEdit, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnDelete, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pSizer.Add(self.btnLoadTotalIAP, 0, wx.ALIGN_LEFT|wx.ALL, 5)
        self.pSizer.Add(self.btnExportTotalIAP, 0, wx.ALIGN_LEFT|wx.ALL, 5)
                
        self.panelHeader.SetSizer(self.pSizer)
        self.pSizer.Fit(self.panelHeader)

        #顶端状态区
        self.pnHeaderStatus = wx.Panel(self,size=(-1,16))
        self.curIncomeText_l = wx.StaticText(self.pnHeaderStatus,-1,u"收入:",size=(40,16))
        self.curIncomeText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(120,16))
        self.curIncomeText_s.SetBackgroundColour(wx.LIGHT_GREY)
        self.curPayText_l = wx.StaticText(self.pnHeaderStatus,-1,u"支出:",size=(40,16))
        self.curPayText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(120,16))
        self.curPayText_s.SetBackgroundColour(wx.LIGHT_GREY)
        self.curBalanceText_l = wx.StaticText(self.pnHeaderStatus,-1,u"余额:",size=(40,16))
        self.curBalanceText_s = wx.StaticText(self.pnHeaderStatus,-1,u"0",size=(120,16))
        self.curBalanceText_s.SetBackgroundColour(wx.LIGHT_GREY)

        self.cbCarExpensesTypeSearch_l = wx.StaticText(self.pnHeaderStatus,-1,u"按类型查看",size=(50,16))
        self.listCarExpensesType = list(GlobalModule.dbOperate.GetCarExpensesTypeList())
        self.cbCarExpensesTypeSearch = wx.ComboBox(self.pnHeaderStatus, -1, self.listCarExpensesType[0], (100,25), choices=self.listCarExpensesType, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX,self.OnCarExpensesTypeSearch,self.cbCarExpensesTypeSearch)

        self.pHStatusSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pHStatusSizer.Add(self.curIncomeText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curIncomeText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curPayText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curPayText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curBalanceText_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.curBalanceText_s, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.cbCarExpensesTypeSearch_l, 0, wx.ALIGN_RIGHT|wx.ALL, 5)
        self.pHStatusSizer.Add(self.cbCarExpensesTypeSearch, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        self.pnHeaderStatus.SetSizer(self.pHStatusSizer)
        self.pHStatusSizer.Fit(self.pnHeaderStatus)

        self.panelLC = wx.Panel(self, -1)
        #汽车费用
        self.lcCarExpensesDetail = wx.ListCtrl(self.panelLC, wx.NewId(),style=wx.LC_REPORT,size=(-1,-1))
        self.lcCarExpensesDetail.InsertColumn(0, u"ID",width=40,format=wx.LIST_FORMAT_CENTER)
        self.lcCarExpensesDetail.InsertColumn(1, u"日期",width=100,format=wx.LIST_FORMAT_CENTER)
        self.lcCarExpensesDetail.InsertColumn(2, u"金额",width=100,format=wx.LIST_FORMAT_CENTER)
        self.lcCarExpensesDetail.InsertColumn(3, u"类型",width=115,format=wx.LIST_FORMAT_CENTER)
        self.lcCarExpensesDetail.InsertColumn(4, u"备注",width=570)

        self.hboxLC = wx.BoxSizer(wx.HORIZONTAL)
        self.hboxLC.Add(self.lcCarExpensesDetail, 1, wx.EXPAND)
        self.panelLC.SetSizer(self.hboxLC)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.panelHeader, 0, wx.EXPAND|wx.ALL, 1)
        self.sizer.Add(self.pnHeaderStatus, 0, wx.EXPAND|wx.ALL, 1)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(self.panelLC, 1, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        #导入文件路径
        self.loadPath = ""

        #导出文件路径
        self.exportPath = ""

        self.lcCarExpensesDetail.Bind(wx.EVT_SIZE, self.OnlcCarExpensesDetailResize)
        #按月查询
        self.OnMonthSearchDetail(None)

    def OnRefreshTabEvent(self,event):
        """刷新界面"""
        self.cbMonthSearch.SetItems(list(GlobalModule.dbOperate.GetCarExpensesExistMonth()))
        self.OnAllSearch_CarExpensesDetail(None)

    def OnlcCarExpensesDetailResize(self,event):
         lcWidth,lcHeight = self.lcCarExpensesDetail.GetSize()
         if lcWidth <= 946:
             self.lcCarExpensesDetail.SetColumnWidth(4,570)
         else:
             self.lcCarExpensesDetail.SetColumnWidth(4,(lcWidth - 21 - 355))

    def OnLoadCarExpensesDetail(self,event):
        wildcard = "Text (*.txt)|*.txt|All files (*.*)|*.*"
        loadDlg = wx.FileDialog(None,u"请选择需要导入的汽车费用表文本文件",os.getcwd(),"",wildcard,wx.OPEN)
        retCode = loadDlg.ShowModal()
        loadDlg.Destroy()
        self.loadPath = ""

        if  (wx.ID_OK == retCode):
            self.loadPath = loadDlg.GetPath()
            self.Enable = False
            self.LoadCarExpensesDetailDoWork()
            self.Enable = True

            messDlg = wx.MessageDialog(self, u"汽车费用表导入完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

    def LoadCarExpensesDetailDoWork(self):
        """从文本文件导入汽车费用表到数据库"""
        if len(self.loadPath) > 0:
            
            with open(self.loadPath,'rb') as txtfile:
                text = txtfile.readline()
                code = GlobalModule.GetStringCode(text)
                
                date = ""
                for line in txtfile.readlines():
                    line = line.decode(code)   #文件是一ASCII码保存的,但中间有中文,实际要按GBK来处理,所以要先用GBK解码
                    items = []
                    index = 0
                    lines = line.split('\t')
                    
                    if len(lines) >= 4:
                        bIsAdd = False
                        for item in lines:
                            if len(item) > 0:
                                bIsAdd = True
                            if (0 == index):
                                if (len(item) > 0):
                                    date = (((item.split(' '))[0]).replace(u'年','-').replace(u'月','-').replace(u'日','-')).split('-')
                                    date = "%04d-%02d-%02d" % (int(date[0]),int(date[1]),int(date[2]))
                                items.append(date)
                            elif (item.find("\"?") > -1) or (item.find("?") > -1):
                                item = item.replace("\"","")
                                item = item.replace("?","")
                                item = item.replace(",","")
                                items.append(str(item))
                            elif (0 == len(item)) and (1 == index):
                                items.append("0")
                            else:
                                items.append(item)
                            if index == 3:
                                break
                            index += 1
                        #存入数据库
                        if (bIsAdd) and (4 == len(items)):
                            GlobalModule.dbOperate.AddCarExpensesItem(items)
                        else:
                            print line

    def OnExportCarExpensesDetail(self,event):
        file_wildcard = "Text (*.txt)|*.txt|All files(*.*)|*.*"
        curTime = tuple(time.localtime())
        name = 'carExpensesDetail_Backup[%04d%02d%02d%02d%02d%02d].txt' % (curTime[0],curTime[1],curTime[2],curTime[3],curTime[4],curTime[5])
        exportDlg = wx.FileDialog(self, 
                            u"文件保存到...",
                            os.getcwd(), 
                            defaultFile = name,
                            style = wx.SAVE | wx.OVERWRITE_PROMPT,
                            wildcard = file_wildcard)  
        retCode = exportDlg.ShowModal()
        exportDlg.Destroy();
        self.exportPath = ""

        if (retCode == wx.ID_OK):
            filename = exportDlg.GetPath()
            if not os.path.splitext(filename)[1]: #如果没有文件名后缀
                filename = filename + '.txt'
            self.exportPath = filename
            self.Enabled = False
            self.ExportCarExpensesDetailDoWork()
            self.Enabled = True

            messDlg = wx.MessageDialog(self, u"汽车费用表数据导出完成",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            messDlg.ShowModal()
            messDlg.Destroy()

    def ExportCarExpensesDetailDoWork(self):
        """数据库汽车费用表记录导出到文本文件"""
        if len(self.exportPath) > 0:
            result = GlobalModule.dbOperate.GetAllCarExpensesItems()

            content = ""
            if 0 == len(content):
                content = '%s\t%s\t%s\t%s\t' % (u'日期',u'金额',u'类型',u'备注')
                content += os.linesep
                
            for i in range(len(result)):
                content += ('%s\t%s\t%s\t%s\t' % (result[i][1],result[i][2],result[i][3],result[i][4]))
                content += os.linesep

            with codecs.open(self.exportPath,'w','utf-8') as backupfile:
                backupfile.write(content)

    def OnCarExpensesTypeSearch(self,event):
        """汽车费用:按支出类型显示"""
        self.OnAllSearch_CarExpensesDetail(None)

    def OnMonthSearchDetail(self,event):

        self.OnAllSearch_CarExpensesDetail(None)

    def OnEdit_CarExpensesDetail(self,event):
        index = self.lcCarExpensesDetail.GetFirstSelected()
        old = []
        for i in range(0,self.lcCarExpensesDetail.ColumnCount):
            old.append((self.lcCarExpensesDetail.GetItem(index,i)).GetText())

        dlgItem = CarExpensesItemDialog(1,(self.Parent).Parent,old)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        self.OnRefreshTabEvent(None)

    def OnDelete_CarExpensesDetail(self,event):
        """删除当前选中记录"""

        #提示确认
        dlgDelete = wx.MessageDialog(None,u"你即将删除此条记录,是否继续?",u"删除警告",wx.YES_NO | wx.ICON_QUESTION)
        retCode = dlgDelete.ShowModal()
        dlgDelete.Destroy()

        if (wx.ID_YES == retCode):
            ids = []
            for i in range(0,self.lcCarExpensesDetail.ItemCount):
                index = self.lcCarExpensesDetail.GetFirstSelected()
                if index >= 0:
                    id = (self.lcCarExpensesDetail.GetItem(index,0)).GetText()
                    if len(id) > 0:
                        ids.append(id)

                    self.lcCarExpensesDetail.DeleteItem(index)

            GlobalModule.dbOperate.DeleteCarExpensesItems(ids)

            self.OnRefreshTabEvent(None)

    def Refresh_CarExpensesDetail(self,result):
        """更新ListCtrl中的数据"""
        #清空原来的
        self.lcCarExpensesDetail.DeleteAllItems()
        curBalance = 0.0
        for i in range(len(result)):
            index = self.lcCarExpensesDetail.InsertStringItem(0,str(result[i][0]))
            for j in range(1,len(result[i])):
                if j == 2:
                    self.lcCarExpensesDetail.SetStringItem(index,j,str(result[i][j]))
                else:
                    self.lcCarExpensesDetail.SetStringItem(index,j,(result[i][j]))

            if (0 == self.lcCarExpensesDetail.ItemCount % 2):
                self.lcCarExpensesDetail.SetItemBackgroundColour(index,wx.LIGHT_GREY)
            #计算当前余额
            curBalance = curBalance + float((str(result[i][2])).replace('(','').replace(')',''))

        self.curPayText_s.SetLabel(str(curBalance))
        curBalance = 0 - curBalance
        self.curBalanceText_s.SetLabel(str(curBalance))

        if (curBalance < 0):
            self.curBalanceText_s.SetForegroundColour(wx.RED)
        else:
            self.curBalanceText_s.SetForegroundColour(wx.BLACK)

    def OnAllSearch_CarExpensesDetail(self,event):
        """详细收支表:显示全部记录"""

        month = self.cbMonthSearch.GetValue()
        type = self.cbCarExpensesTypeSearch.GetValue()

        result = GlobalModule.dbOperate.GetCarExpensesItemsForConditionMonth(month,type)
        self.Refresh_CarExpensesDetail(result)

    def OnSearch_CarExpensesDetail(self,event):
        """汽车费用表:日期查询按钮处理函数"""
        dtStart = "%4d-%02d-%02d" % (self.startDate_t.GetValue().GetYear(),self.startDate_t.GetValue().GetMonth() + 1,self.startDate_t.GetValue().GetDay())
        dtEnd = "%4d-%02d-%02d" % (self.endDate_t.GetValue().GetYear(),self.endDate_t.GetValue().GetMonth() + 1,self.endDate_t.GetValue().GetDay())

        type = self.cbCarExpensesTypeSearch.GetValue()
        result = GlobalModule.dbOperate.GetCarExpensesItemsForConditionDate(dtStart,dtEnd,type)
        self.Refresh_CarExpensesDetail(result)

class MainFrame(wx.Frame):
    """主框架"""

    def __init__(self, parent=None, id=-1,
                 pos=wx.DefaultPosition,
                 title=u'我的钱包'):

        wx.Frame.__init__(self, parent, id, title, pos,size = (980,600))

        self.SetMinSize((980,600))
        self.icon = wx.Icon(os.path.join(GlobalModule.home, 'images', 'wallet256.ico'), wx.BITMAP_TYPE_ICO)
        self.SetIcon(self.icon)
        
        #添加状态栏
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([-3, -2, -1])
        #给状态栏赋值
        #self.statusbar.SetStatusText("Pos: %s" % str(event.GetPositionTuple()), 0)

        #添加工具栏
        self.ID_AddAccountItem = wx.NewId()
        self.ID_AddIncomeItem = wx.NewId()
        self.ID_AddPayItem = wx.NewId()
        self.ID_AddDetailIAPItem = wx.NewId()
        self.ID_AddCarExpengsesItem = wx.NewId()
        self.ID_AddBackupItem = wx.NewId()
        self.ID_AddRecoveryItem = wx.NewId()
        self.createToolBar()

        #添加菜单栏
        self.menuBar = wx.MenuBar()
        self.fileMenu = wx.Menu()
        self.menuExit = self.fileMenu.Append(-1,u"退出",u"关闭程序")
        self.Bind(wx.EVT_MENU,self.Exit,self.menuExit)

        self.operateMenu = wx.Menu()
        self.menuAddAccount = self.operateMenu.Append(-1,u'添加账户',u'添加新的账户信息')
        self.operateMenu.AppendSeparator()
        self.menuAddIncome = self.operateMenu.Append(-1,u'添加收入',u'添加新的收入记录')
        self.menuAddPay = self.operateMenu.Append(-1,u'添加支出',u'添加新的支出记录')
        self.operateMenu.AppendSeparator()
        self.menuAddDetailIAP = self.operateMenu.Append(-1,u'添加详细收支',u'添加新的详细收支记录')
        self.operateMenu.AppendSeparator()
        self.menuAddCarExpenses = self.operateMenu.Append(-1,u'添加汽车费用',u'添加新的汽车费用记录')
        self.operateMenu.AppendSeparator()
        self.menuBackup = self.operateMenu.Append(-1,u'备份',u'将数据备份到磁盘')
        self.menuRecovery = self.operateMenu.Append(-1,u'恢复',u'从磁盘恢复数据')

        self.Bind(wx.EVT_MENU,self.OnAddAccountItem,self.menuAddAccount)

        self.Bind(wx.EVT_MENU,self.OnAddIncomeItem,self.menuAddIncome)
        self.Bind(wx.EVT_MENU,self.OnAddPayItem,self.menuAddPay)

        self.Bind(wx.EVT_MENU,self.OnAddDetailIAPItem,self.menuAddDetailIAP)

        self.Bind(wx.EVT_MENU,self.OnAddCarExpensesItem,self.menuAddCarExpenses)

        self.Bind(wx.EVT_MENU,self.OnBackupEvent,self.menuBackup)
        self.Bind(wx.EVT_MENU,self.OnRecoveryEvent,self.menuRecovery)

        self.operateMenu.Enable(self.menuAddAccount.GetId(), True)
        self.operateMenu.Enable(self.menuAddIncome.GetId(), False)
        self.operateMenu.Enable(self.menuAddPay.GetId(), False)
        self.operateMenu.Enable(self.menuAddDetailIAP.GetId(), False)

        self.aboutMenu = wx.Menu()
        self.menuAbout = self.aboutMenu.Append(-1,u"关于",u"关于本程序相关信息")
        self.Bind(wx.EVT_MENU,self.OnAbout,self.menuAbout)

        self.menuBar.Append(self.fileMenu,u'文件')
        self.menuBar.Append(self.operateMenu,u'操作')
        self.menuBar.Append(self.aboutMenu,u'关于')

        self.SetMenuBar(self.menuBar)

        self.Center()

        #按月备份数据库
        self.DB_Backup()
        #1 绑定框架关闭事件
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

    def OnAbout(self,event):
        dlg = MyWalletAbout(self)
        dlg.ShowModal()
        dlg.Destroy()

    def Exit(self,event):
        self.OnCloseWindow(None)
        wx.Exit()

    def OnBackupEvent(self,event):
        file_wildcard = "Sqlite3 (*.db)|*.db|All files (*.*)|*.*"
        curTime = tuple(time.localtime())
        name = 'myWalletMain[%04d%02d%02d%02d%02d%02d].db' % (curTime[0],curTime[1],curTime[2],curTime[3],curTime[4],curTime[5])
        saveDlg = wx.FileDialog(self, 
                            u"文件保存到...",
                            os.getcwd(), 
                            defaultFile = name,
                            style = wx.SAVE | wx.OVERWRITE_PROMPT,
                            wildcard = file_wildcard)  
        retCode = saveDlg.ShowModal()
        saveDlg.Destroy();

        if (retCode == wx.ID_OK):
            backupName = saveDlg.GetPath()
            if not os.path.splitext(backupName)[1]: #如果没有文件名后缀  
                backupName = backupName + '.db'
                
            cmd = r'copy %s %s' % (GlobalModule.dbOperate.dbDataPath,backupName)
            os.system(cmd.encode('gbk'))

        messDlg = wx.MessageDialog(self, u"数据备份完成",
                         u'信息提示',
                         wx.YES_DEFAULT | wx.ICON_INFORMATION)
        messDlg.ShowModal()
        messDlg.Destroy()

    def OnRecoveryEvent(self,event):

        wildcard = "Sqlite (*.db)|*.db"\
            "|All files (*.*)|*.*"
        openfileDlg = wx.FileDialog(None,u"请选择需要导入的数据库文件",os.getcwd(),"",wildcard,wx.OPEN)
        retCode = openfileDlg.ShowModal()
        openfileDlg.Destroy()

        if  (wx.ID_OK == retCode):
            recoveryName = openfileDlg.GetPath()

            messDlg = wx.MessageDialog(self, u"此操作将覆盖当前数据库全部内容,你确定要继续进行吗?",
                             u'信息提示',
                             wx.YES_NO | wx.ICON_INFORMATION)
            retCode = messDlg.ShowModal()
            messDlg.Destroy()

            if (wx.ID_YES == retCode):
                GlobalModule.dbOperate.DBClose()
                os.remove(GlobalModule.dbOperate.dbDataPath)
                cmd = r'copy %s %s' % (recoveryName,GlobalModule.dbOperate.dbDataPath)
                os.system(cmd.encode('gbk'))
        
        messDlg = wx.MessageDialog(self, u"数据恢复完成,请重新启动!",
                         u'信息提示',
                         wx.YES_DEFAULT | wx.ICON_INFORMATION)
        messDlg.ShowModal()
        messDlg.Destroy()

        self.Destroy()

    def DB_Backup(self):
        """按月备份数据库"""

        timeNow = tuple(time.localtime())
        curTime = "%04d-%02d" % (timeNow[0],timeNow[1])

        backupPath = os.path.join(GlobalModule.backupPath, GlobalModule.dbOperate.dbName + ("%04d-%02d" % (timeNow[0],timeNow[1])) + '.db')
        if not os.path.exists(backupPath):

            if os.path.exists(GlobalModule.dbOperate.dbDataPath):
                cmd = r'copy %s %s' % (GlobalModule.dbOperate.dbDataPath,backupPath)
                os.system(cmd.encode('gbk'))

    def OnCloseWindow(self,event):
        #关闭临时存储数据库
        self.Destroy()
    
    def createToolBar(self):
        #1创建工具栏
        self.toolbar = self.CreateToolBar()

        for each in self.toolbarData():
            if len(each[1]) > 0:
                self.createSimpleTool(self.toolbar, *each)
            else:
                self.toolbar.AddSeparator()
        
        #2 显现工具栏
        self.toolbar.Realize()

    def createSimpleTool(self, toolbar, id, label, filename,help, handler):
        #3 创建常规工具

        if not label:
            toolbar.AddSeparator()
            return

        bmp = wx.Image(filename,wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        tool = toolbar.AddSimpleTool(id, bmp, label, help)
        self.Bind(wx.EVT_MENU, handler, tool)

    def toolbarData(self):
        return ((self.ID_AddAccountItem,u"添加账户", os.path.join(GlobalModule.home, 'images', 'accountadd.png'), u"添加新的账户信息",self.OnAddAccountItem),
                (-1,"",),
                (self.ID_AddIncomeItem,u"添加收入", os.path.join(GlobalModule.home, 'images', 'cashin.png'), u"添加新的收入记录",self.OnAddIncomeItem),
                (self.ID_AddPayItem,u"添加支出", os.path.join(GlobalModule.home, 'images', 'cashout.png'), u"添加新的支出记录",self.OnAddPayItem),
                (-1,"",),
                (self.ID_AddDetailIAPItem,u"添加详细收支", os.path.join(GlobalModule.home, 'images', 'detailIAP.png'), u"添加新的详细收支记录",self.OnAddDetailIAPItem),
                (-1,"",),
                (self.ID_AddCarExpengsesItem,u"添加汽车费用", os.path.join(GlobalModule.home, 'images', 'carExpenses.png'), u"添加新的汽车费用记录",self.OnAddCarExpensesItem),
                (-1,"",),
                (self.ID_AddBackupItem,u"备份", os.path.join(GlobalModule.home, 'images', 'backup.png'), u"将数据备份到磁盘",self.OnBackupEvent),
                (self.ID_AddRecoveryItem,u"恢复", os.path.join(GlobalModule.home, 'images', 'recovery.png'), u"从磁盘恢复数据",self.OnRecoveryEvent))
    
    def OnAddCarExpensesItem(self,event):
        dlgItem = CarExpensesItemDialog(0,self,None)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        #7 创建自定义事件
        evt = RefreshTabEvent(myEVT_RefreshTab, self.GetId())
        # 添加数据到事件
        evt.SetIndex(3)
        #8 处理事件
        self.GetEventHandler().ProcessEvent(evt)

    def OnAddDetailIAPItem(self,event):
        dlgItem = DetailIAPItemDialog(0,self,None)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        #7 创建自定义事件
        evt = RefreshTabEvent(myEVT_RefreshTab, self.GetId())
        # 添加数据到事件
        evt.SetIndex(2)
        #8 处理事件
        self.GetEventHandler().ProcessEvent(evt)

    def OnAddAccountItem(self,event):
        dlgItem = AccountItemDialog(0,self,None)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        #7 创建自定义事件
        evt = RefreshTabEvent(myEVT_RefreshTab, self.GetId())
        # 添加数据到事件
        evt.SetIndex(0)
        #8 处理事件
        self.GetEventHandler().ProcessEvent(evt)

    def OnAddIncomeItem(self,event):
        dlgItem = IAPItemDialog(0,self,None,0)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        #7 创建自定义事件
        evt = RefreshTabEvent(myEVT_RefreshTab, self.GetId())
        # 添加数据到事件
        evt.SetIndex(1)
        #8 处理事件
        self.GetEventHandler().ProcessEvent(evt)

    def OnAddPayItem(self,event):
        dlgItem = IAPItemDialog(1,self,None,0)
        dlgItem.ShowModal()
        dlgItem.Destroy()

        #7 创建自定义事件
        evt = RefreshTabEvent(myEVT_RefreshTab, self.GetId())
        # 添加数据到事件
        evt.SetIndex(1)
        #8 处理事件
        self.GetEventHandler().ProcessEvent(evt)

class DetailIAPItemDialog(wx.Dialog):
    """添加详细收支对话框:type:0 - 添加,1 - 编辑[__init__(self,type,mainFrame,old)]"""
    def __init__(self,type,mainFrame,old):
        self.oldItem = old
        self.mainF = mainFrame
        self.itemType = type
        self.title = u"添加详细收支"
        if 1 == self.itemType:
            self.title = u"修改详细收支"

        self.itemAccountList = GlobalModule.dbOperate.GetAccountAliasList()

        wx.Dialog.__init__(self, None, -1, self.title)

        # Create the text controls
        self.date_l  = wx.StaticText(self, -1, u"日期:",size=(40,25))
        self.number_l = wx.StaticText(self, -1, u"金额:",size=(40,25))
        self.account_l = wx.StaticText(self, -1, u"账户:",size=(40,25))
        self.discrip_l = wx.StaticText(self, -1, u"说明:",size=(40,25))

        self.date_t = wx.GenericDatePickerCtrl(self, dt=wx.DateTime(), size=(200, 25), style=wx.DP_DROPDOWN|wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)
        self.number_t = wx.TextCtrl(self,size=(200,25))
        self.account_t = wx.ComboBox(self, -1, self.itemAccountList[0], (200,25), choices=self.itemAccountList, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.discrip_t = wx.TextCtrl(self,style=wx.TE_MULTILINE,size=(200,100))

        if (1 == self.itemType) and (len(old) >= 4):
            tm = wx.DateTime()
            date = (self.oldItem[1]).split('-')
            if 3 == len(date):
                tm.Set(int(date[2]),int(date[1]) - 1,int(date[0]))
            self.date_t.SetValue(tm)
            self.number_t.SetValue(old[2])
            self.account_t.SetValue(old[3])
            self.discrip_t.SetValue(old[4])

        self.btnSave = wx.Button(self,label=u"保存",size=(50,25))
        self.btnCancel = wx.Button(self,label=u"取消",size=(50,25))
        self.Bind(wx.EVT_BUTTON,self.OnSave,self.btnSave)
        self.Bind(wx.EVT_BUTTON,self.OnCancel,self.btnCancel)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
         
        fgs = wx.FlexGridSizer(4, 2, 5, 5)
        fgs.Add(self.date_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.date_t, 0, wx.EXPAND)
        fgs.Add(self.number_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.number_t, 0, wx.EXPAND)
        fgs.Add(self.account_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.account_t, 0, wx.EXPAND)
        fgs.Add(self.discrip_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.discrip_t, 0, wx.EXPAND)
        fgs.AddGrowableRow(3)
        self.sizer.Add(fgs, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)

        btnBox = wx.BoxSizer(orient=wx.HORIZONTAL)  
        btnBox.Add(self.btnSave, 1, wx.ALIGN_CENTER|wx.ALL, 5)
        btnBox.Add(self.btnCancel, 1, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(btnBox,0,wx.EXPAND | wx.ALL,5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def OnSave(self,event):
        valueList = []
        valueList.append("%4d-%02d-%02d" % (self.date_t.GetValue().GetYear(),self.date_t.GetValue().GetMonth() + 1,self.date_t.GetValue().GetDay()))

        num = self.number_t.GetValue()
        ret = re.search(u'^[+|-]*[0-9]+(\.[0-9]+)?', num)
        if not ret:
            ret = re.search(u'\.[0-9]+', num)
            if ret:
                numstr = '0' + num
            else:
                numstr = '0'
        else:
            numstr = ret.group()

        valueList.append(numstr)

        valueList.append(self.account_t.GetValue())
        valueList.append(self.discrip_t.GetValue())

        if 0 == self.itemType:
            GlobalModule.dbOperate.AddDetailIAPItem(valueList)
        else:
            valueList.append(self.oldItem[0])
            GlobalModule.dbOperate.ChangedDetailIAPItem(valueList)

        self.mainF.statusbar.SetStatusText(u"详细收支记录保存成功", 1)
        #清空界面
        self.number_t.SetValue("")
        self.account_t.SetValue("")
        self.discrip_t.SetValue("")

    def OnCancel(self,event):
        self.Close()

class CarExpensesItemDialog(wx.Dialog):
    """添加汽车费用记录对话框:type:0 - 添加,1 - 编辑[__init__(self,type,mainFrame,old)]"""
    def __init__(self,type,mainFrame,old):
        self.oldItem = old
        self.mainF = mainFrame
        self.itemType = type
        self.title = u"添加汽车费用"
        if 1 == self.itemType:
            self.title = u"修改汽车费用"

        self.itemTypeList = GlobalModule.dbOperate.GetExpensesTypeList()

        wx.Dialog.__init__(self, None, -1, self.title)

        # Create the text controls
        self.date_l  = wx.StaticText(self, -1, u"日期:",size=(40,25))
        self.number_l = wx.StaticText(self, -1, u"金额:",size=(40,25))
        self.type_l = wx.StaticText(self, -1, u"类型:",size=(40,25))
        self.discrip_l = wx.StaticText(self, -1, u"说明:",size=(40,25))

        self.date_t = wx.GenericDatePickerCtrl(self, dt=wx.DateTime(), size=(200, 25), style=wx.DP_DROPDOWN|wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)
        self.number_t = wx.TextCtrl(self,size=(200,25))
        self.type_t = wx.ComboBox(self, -1, self.itemTypeList[0], (200,25), choices=self.itemTypeList, style=wx.CB_DROPDOWN)
        self.discrip_t = wx.TextCtrl(self,style=wx.TE_MULTILINE,size=(200,100))

        if (1 == self.itemType) and (len(old) >= 4):
            tm = wx.DateTime()
            date = (self.oldItem[1]).split('-')
            if 3 == len(date):
                tm.Set(int(date[2]),int(date[1]) - 1,int(date[0]))
            self.date_t.SetValue(tm)
            self.number_t.SetValue(old[2])
            self.type_t.SetValue(old[3])
            self.discrip_t.SetValue(old[4])

        self.btnSave = wx.Button(self,label=u"保存",size=(50,25))
        self.btnCancel = wx.Button(self,label=u"取消",size=(50,25))
        self.Bind(wx.EVT_BUTTON,self.OnSave,self.btnSave)
        self.Bind(wx.EVT_BUTTON,self.OnCancel,self.btnCancel)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
         
        fgs = wx.FlexGridSizer(4, 2, 5, 5)
        fgs.Add(self.date_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.date_t, 0, wx.EXPAND)
        fgs.Add(self.number_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.number_t, 0, wx.EXPAND)
        fgs.Add(self.type_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.type_t, 0, wx.EXPAND)
        fgs.Add(self.discrip_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.discrip_t, 0, wx.EXPAND)
        fgs.AddGrowableRow(3)
        self.sizer.Add(fgs, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)

        btnBox = wx.BoxSizer(orient=wx.HORIZONTAL)  
        btnBox.Add(self.btnSave, 1, wx.ALIGN_CENTER|wx.ALL, 5)
        btnBox.Add(self.btnCancel, 1, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(btnBox,0,wx.EXPAND | wx.ALL,5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def OnSave(self,event):
        valueList = []
        valueList.append("%4d-%02d-%02d" % (self.date_t.GetValue().GetYear(),self.date_t.GetValue().GetMonth() + 1,self.date_t.GetValue().GetDay()))

        num = self.number_t.GetValue()
        ret = re.search(u'^[+|-]*[0-9]+(\.[0-9]+)?', num)
        if not ret:
            ret = re.search(u'\.[0-9]+', num)
            if ret:
                numstr = '0' + num
            else:
                numstr = '0'
        else:
            numstr = ret.group()

        valueList.append(numstr)

        valueList.append(self.type_t.GetValue())
        valueList.append(self.discrip_t.GetValue())

        if 0 == self.itemType:
            GlobalModule.dbOperate.AddCarExpensesItem(valueList)
        else:
            valueList.append(self.oldItem[0])
            GlobalModule.dbOperate.ChangedCarExpensesItem(valueList)

        self.mainF.statusbar.SetStatusText(u"汽车费用记录保存成功", 1)
        #清空界面
        self.number_t.SetValue("")
        self.type_t.SetValue("")
        self.discrip_t.SetValue("")

    def OnCancel(self,event):
        self.Close()

class AccountItemDialog(wx.Dialog):
    """添加账户信息对话框:type:0 - 添加,1 - 编辑"""
    def __init__(self,type,mainFrame,old):
        self.oldItem = old
        self.mainF = mainFrame
        self.itemType = type
        self.title = u"添加账户信息"
        if 1 == self.itemType:
            self.title = u"修改账户信息"

        wx.Dialog.__init__(self, None, -1, self.title)

        # Create the text controls
        self.number_l  = wx.StaticText(self, -1, u"帐号:",size=(40,25))
        self.alias_l = wx.StaticText(self, -1, u"别名:",size=(40,25))
        self.bankname_l = wx.StaticText(self, -1, u"银行:",size=(40,25))
        self.balance_l = wx.StaticText(self, -1, u"余额:",size=(40,25))
        self.discrip_l = wx.StaticText(self, -1, u"说明:",size=(40,25))
               
        self.number_t = wx.TextCtrl(self,size=(200,25))
        self.alias_t = wx.TextCtrl(self,size=(200,25))
        self.bankname_t = wx.TextCtrl(self,size=(200,25))
        self.balance_t = wx.TextCtrl(self,size=(200,25))
        self.discrip_t = wx.TextCtrl(self,style=wx.TE_MULTILINE,size=(200,100))

        if (1 == self.itemType) and (len(old) >= 6):
            self.number_t.SetValue(old[1])
            self.alias_t.SetValue(old[2])
            self.bankname_t.SetValue(old[3])
            self.balance_t.SetValue(old[4])
            self.discrip_t.SetValue(old[5])

        self.btnSave = wx.Button(self,label=u"保存",size=(50,25))
        self.btnCancel = wx.Button(self,label=u"取消",size=(50,25))
        self.Bind(wx.EVT_BUTTON,self.OnSave,self.btnSave)
        self.Bind(wx.EVT_BUTTON,self.OnCancel,self.btnCancel)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        fgs = wx.FlexGridSizer(5, 2, 5, 5)
        fgs.Add(self.number_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.number_t, 0, wx.EXPAND)
        fgs.Add(self.alias_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.alias_t, 0, wx.EXPAND)
        fgs.Add(self.bankname_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.bankname_t, 0, wx.EXPAND)
        fgs.Add(self.balance_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.balance_t, 0, wx.EXPAND)
        fgs.Add(self.discrip_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.discrip_t, 0, wx.EXPAND)
        fgs.AddGrowableRow(4)
        self.sizer.Add(fgs, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)

        btnBox = wx.BoxSizer(orient=wx.HORIZONTAL)  
        btnBox.Add(self.btnSave, 1, wx.ALIGN_CENTER|wx.ALL, 5)  
        btnBox.Add(self.btnCancel, 1, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(btnBox,0,wx.EXPAND | wx.ALL,5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def OnSave(self,event):
        valueList = []
        valueList.append(self.number_t.GetValue())
        valueList.append(self.alias_t.GetValue())
        valueList.append(self.bankname_t.GetValue())

        num = self.balance_t.GetValue()
        ret = re.search(u'^[+|-]*[0-9]+(\.[0-9]+)?', num)
        if not ret:
            ret = re.search(u'\.[0-9]+', num)
            if ret:
                numstr = '0' + num
            else:
                numstr = '0'
        else:
            numstr = ret.group()

        valueList.append(numstr)
        valueList.append(self.discrip_t.GetValue())

        if 0 == self.itemType:
            GlobalModule.dbOperate.AddAccountItem(valueList)
        else:
            valueList.append(self.oldItem[0])
            GlobalModule.dbOperate.ChangedAccountItem(valueList)

        self.mainF.statusbar.SetStatusText(u"账户信息保存成功", 1)
        #清空界面
        self.number_t.SetValue("")
        self.alias_t.SetValue("")
        self.bankname_t.SetValue("")
        self.balance_t.SetValue("")
        self.discrip_t.SetValue("")

    def OnCancel(self,event):
        self.Close()

class IAPItemDialog(wx.Dialog):
    """总收支表编辑框:type:0 - 收入,1 - 支出,status:0 - 添加,1 - 编辑"""
    def __init__(self,type,mainFrame,old,status):
        """type:0 - 收入,1 - 支出,status:0 - 添加,1 - 编辑"""
        self.oldItem = old
        self.curStatus = status
        self.mainF = mainFrame
        self.itemType = type
        if 0 == self.curStatus:
            self.title = u"添加"
        else:
            self.title = u"编辑"
        
        if 0 == self.itemType:
            self.title += u"收入"
        else:
            self.title += u"支出"

        self.itemTypeList = [u"实际收入",u"转账"]
        self.itemSubTypeList = GlobalModule.dbOperate.GetSubTypeList(type)
        self.itemAccountList = GlobalModule.dbOperate.GetAccountAliasList()
        if 1 == self.itemType:
            self.itemTypeList = [u"实际支出",u"转账"]

        wx.Dialog.__init__(self, None, -1, self.title)

        # Create the text controls
        self.date_l = wx.StaticText(self,-1,u"日期:",size=(40,25))
        self.itemType_l  = wx.StaticText(self, -1, u"类型:",size=(40,25))
        self.account_l = wx.StaticText(self, -1, u"账户:",size=(40,25))
        self.number_l = wx.StaticText(self, -1, u"金额:",size=(40,25))
        self.subType_l = wx.StaticText(self, -1, u"子类型:",size=(40,25))
        self.discrip_l = wx.StaticText(self, -1, u"说明:",size=(40,25))

        #tm = wx.DateTime()
        #tm.Set(readydata['day'], readydata['month']-1, readydata['year'])
        self.date_t = wx.GenericDatePickerCtrl(self, dt=wx.DateTime(), size=(200, 25), style=wx.DP_DROPDOWN|
                    wx.DP_SHOWCENTURY|wx.DP_ALLOWNONE)
        #self.date_t = wx.TextCtrl(self,value=time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())),size=(200,25))
        self.itemType_t = wx.ComboBox(self, -1, self.itemTypeList[0], (200,25), choices=self.itemTypeList, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        #self.itemType_t = wx.Choice(self,-1,size=(200,25),choices=self.itemTypeList)
        #self.itemType_t.SetSelection(0);
        self.account_t = wx.ComboBox(self, -1, self.itemAccountList[0], (200,25), choices=self.itemAccountList, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.number_t = wx.TextCtrl(self,size=(200,25))
        self.discrip_t = wx.TextCtrl(self,style=wx.TE_MULTILINE,size=(200,100))
        self.subType_t = wx.ComboBox(self, -1,self.itemSubTypeList[0], (-1, -1),
                         (160, -1), self.itemSubTypeList,
                         style=wx.CB_DROPDOWN
                         #| wx.TE_PROCESS_ENTER
                         #| wx.CB_SORT
                         )

        self.btnSave = wx.Button(self,label=u"保存",size=(50,25))
        self.btnCancel = wx.Button(self,label=u"取消",size=(50,25))
        self.Bind(wx.EVT_BUTTON,self.OnSave,self.btnSave)
        self.Bind(wx.EVT_BUTTON,self.OnCancel,self.btnCancel)

        if 1 == self.curStatus:
            tm = wx.DateTime()
            date = (self.oldItem[1]).split('-')
            if 3 == len(date):
                tm.Set(int(date[2]),int(date[1]) - 1,int(date[0]))
            self.date_t.SetValue(tm)

            if (self.oldItem[3] != '0.0') or (self.oldItem[4] != '0.0'):
                self.itemType_t.SetValue(self.itemTypeList[1])

            number = 0.0
            for i in range(2,6):
                if (self.oldItem[i] != '0.0'):
                    number = self.oldItem[i]
                    break

            self.number_t.SetValue(number)
            self.account_t.SetValue(self.oldItem[7])
            self.subType_t.SetValue(self.oldItem[8])
            self.discrip_t.SetValue(self.oldItem[9])

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
         
        fgs = wx.FlexGridSizer(6, 2, 5, 5)
        fgs.Add(self.date_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.date_t, 0, wx.EXPAND)
        fgs.Add(self.itemType_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.itemType_t, 0, wx.EXPAND)
        fgs.Add(self.account_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.account_t, 0, wx.EXPAND)
        fgs.Add(self.number_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.number_t, 0, wx.EXPAND)
        fgs.Add(self.subType_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.subType_t, 0, wx.EXPAND)
        fgs.Add(self.discrip_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.discrip_t, 0, wx.EXPAND)
        fgs.AddGrowableRow(5)
        self.sizer.Add(fgs, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)

        btnBox = wx.BoxSizer(orient=wx.HORIZONTAL)  
        btnBox.Add(self.btnSave, 1, wx.ALIGN_CENTER|wx.ALL, 5)  
        btnBox.Add(self.btnCancel, 1, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(btnBox,0,wx.EXPAND | wx.ALL,5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def OnSave(self,event):
        valueList = []
        valueList.append("%4d-%02d-%02d" % (self.date_t.GetValue().GetYear(),self.date_t.GetValue().GetMonth() + 1,self.date_t.GetValue().GetDay()))

        num = self.number_t.GetValue()
        ret = re.search(u'^[+|-]*[0-9]+(\.[0-9]+)?', num)
        if not ret:
            ret = re.search(u'\.[0-9]+', num)
            if ret:
                numstr = '0' + num
            else:
                numstr = '0'
        else:
            numstr = ret.group()

        #收入
        if 0 == self.itemType:
            #实际收入
            if 0 == self.itemType_t.Selection:
                valueList.append(numstr)
                valueList.append('0')
                valueList.append('0')
                valueList.append('0')
            else:
                valueList.append('0')
                valueList.append(numstr)
                valueList.append('0')
                valueList.append('0')
        else:
            #实际支出
            if 0 == self.itemType_t.Selection:
                valueList.append('0')
                valueList.append('0')
                valueList.append('0')
                valueList.append(numstr)
            else:
                valueList.append('0')
                valueList.append('0')
                valueList.append(numstr)
                valueList.append('0')

        valueList.append(self.account_t.GetValue())
        valueList.append(self.subType_t.GetValue())
        valueList.append(self.discrip_t.GetValue())

        if 0 == self.curStatus:
            GlobalModule.dbOperate.AddIAPItem(valueList)
        else:
            valueList.append(self.oldItem[0])
            GlobalModule.dbOperate.ChangedIAPItem(valueList)

        self.mainF.statusbar.SetStatusText(u"记录保存成功", 1)
        #清空界面
        self.itemType_t.SetSelection(0)
        self.number_t.SetValue("")
        self.discrip_t.SetValue("")

    def OnCancel(self,event):
        self.Close()

class MyWalletAbout(wx.Dialog):
    text = u'''
    <html>
    <body bgcolor="#ACAA60">
    <center><table bgcolor="#455481" width="100%" cellspacing="0" cellpadding="0" border="1">
    <tr>
    <td align="center"><h1>我的钱包</h1></td>
    </tr>
    </table>
    </center>
    <p><b>我的钱包</b> 是我第一个<b>wxPython In Action</b>
    练习程序,它是基于SuperDoodle来<br>
    演示wxPython的使用,参考:http://www.wxpython.org/ <br>
    </p>
    <p><b>SuperDoodle</b> and <b>wxPython</b> are brought to you by
    <b>Robin Dunn</b> and <b>Total Control Software</b>, Copyright
    &copy; 2013-2020.</p>

    <p>
    第二版:2013-11-22<br>
    第三版：2014-01-17<br>
    第四版：2014-03-04<br>
    第五版：2014-06-26<br>
    作者:风无痕<br>
    联系:jiangchaoplh@126.com
    </p>
    </body>
    </html>
    '''

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, u'关于 我的钱包',
                          size=(440, 400) )

        html = wx.html.HtmlWindow(self)
        html.SetPage(self.text)
        button = wx.Button(self, wx.ID_OK, u"确定")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(html, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(button, 0, wx.ALIGN_CENTER|wx.ALL, 5)

        self.SetSizer(sizer)
        self.Layout()

class DlgLogon(wx.Dialog):
    """登录对话框"""
    def __init__(self):

        wx.Dialog.__init__(self, None, -1, u'欢迎登陆我的钱包')

        # Create the text controls
        self.userid_l  = wx.StaticText(self, -1, u"用户名:",size=(50,25))
        self.password_l = wx.StaticText(self, -1, u"密码:",size=(50,25))

        self.userid_t = wx.TextCtrl(self,-1,"jiangxinyu",size=(200,25))
        self.password_t = wx.TextCtrl(self,style=wx.TE_PASSWORD,size=(200,25))

        self.btnSave = wx.Button(self,label=u"确定",size=(50,25))
        self.btnCancel = wx.Button(self,label=u"取消",size=(50,25))
        self.Bind(wx.EVT_BUTTON,self.OnSave,self.btnSave)
        self.Bind(wx.EVT_BUTTON,self.OnCancel,self.btnCancel)

        # Layout with sizers
        self.sizer = wx.BoxSizer(wx.VERTICAL)
         
        fgs = wx.FlexGridSizer(2, 2, 5, 5)
        fgs.Add(self.userid_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.userid_t, 0, wx.EXPAND)
        fgs.Add(self.password_l, 0, wx.ALIGN_RIGHT)
        fgs.Add(self.password_t, 0, wx.EXPAND)
        self.sizer.Add(fgs, 0, wx.EXPAND|wx.ALL, 5)
        self.sizer.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)

        btnBox = wx.BoxSizer(orient=wx.HORIZONTAL)  
        btnBox.Add(self.btnSave, 1, wx.ALIGN_CENTER|wx.ALL, 5)  
        btnBox.Add(self.btnCancel, 1, wx.ALIGN_CENTER | wx.ALL, 5)
        self.sizer.Add(btnBox,0,wx.EXPAND | wx.ALL,5)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

        self.count = 3

    def OnSave(self,event):
        """
        密码部分暂时直接写在代码中
        """

        userid = self.userid_t.GetValue()
        password = self.password_t.GetValue()

        if (0 == len(userid)) or (0 == len(password)):
            messDlg = wx.MessageDialog(self, u"用户名或密码不能为空",
                             u'信息提示',
                             wx.YES_DEFAULT | wx.ICON_INFORMATION)
            retCode = messDlg.ShowModal()
            messDlg.Destroy()
        else:
            if ('Admin' == userid) and ('Admin' == password):
                GlobalModule.isLogin = True
                self.Close()
            else:
                self.count -= 1
                messDlg = wx.MessageDialog(self, u"用户名或密码错误,连续三次输入错误,系统将自动关闭: 你还有[%s]次机会" % (self.count),
                                 u'信息提示',
                                 wx.YES_DEFAULT | wx.ICON_INFORMATION)
                retCode = messDlg.ShowModal()
                messDlg.Destroy()

                if 0 == self.count:
                    self.Close()

    def OnCancel(self,event):
        self.Close()

class MainApp(wx.App):
    """程序主框架"""

    def OnInit(self):

        GlobalModule.isLogin = False
        #用户登录检查
        dlgLogon = DlgLogon()
        dlgLogon.ShowModal()
        dlgLogon.Destroy()

        if GlobalModule.isLogin:

            self.frame = MainFrame()

            #主界面Tab页面
            self.nb = wx.Notebook(self.frame)
            self.cjaccountdetail = cjAccountDetail(self.nb)
            self.cjtotalincomeandpay = cjTotalIncomeAndPay(self.nb)
            self.cjtotalincomeandpaydetail = cjTotalIncomeAndPayDetail(self.nb)
            self.cjcarexpenses = cjCarExpenses(self.nb)

            self.nb.AddPage(self.cjaccountdetail,u"账户信息")
            self.nb.AddPage(self.cjtotalincomeandpay,u"总收支")
            self.nb.AddPage(self.cjtotalincomeandpaydetail,u"详细收支")
            self.nb.AddPage(self.cjcarexpenses,u"汽车费用")

            self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,self.OnNotebookPageChanged,self.nb)

            #9 绑定自定义事件,自动刷新
            self.Bind(EVT_RefreshTab, self.OnRefreshTabEvent, self.frame)

            self.OnNotebookPageChanged(None)
            self.SetTopWindow(self.frame)
            self.frame.Show()

        return True

    def OnRefreshTabEvent(self,event):
        if 0 == event.GetIndex():
            self.cjaccountdetail.OnRefreshTabEvent(event)
        elif 1 == event.GetIndex():
            self.cjtotalincomeandpay.OnRefreshTabEvent(event)
        elif 2 == event.GetIndex():
            self.cjtotalincomeandpaydetail.OnRefreshTabEvent(event)
        elif 3 == event.GetIndex():
            self.cjcarexpenses.OnRefreshTabEvent(event)

    def OnNotebookPageChanged(self,event):
        self.frame.toolbar.EnableTool(self.frame.ID_AddAccountItem,(0 == self.nb.GetSelection()))
        self.frame.toolbar.EnableTool(self.frame.ID_AddIncomeItem,(1 == self.nb.GetSelection()))
        self.frame.toolbar.EnableTool(self.frame.ID_AddPayItem,(1 == self.nb.GetSelection()))
        self.frame.toolbar.EnableTool(self.frame.ID_AddDetailIAPItem,(2 == self.nb.GetSelection()))
        self.frame.toolbar.EnableTool(self.frame.ID_AddCarExpengsesItem,(3 == self.nb.GetSelection()))

        self.frame.operateMenu.Enable(self.frame.menuAddAccount.GetId(), (0 == self.nb.GetSelection()))
        self.frame.operateMenu.Enable(self.frame.menuAddIncome.GetId(), (1 == self.nb.GetSelection()))
        self.frame.operateMenu.Enable(self.frame.menuAddPay.GetId(), (1 == self.nb.GetSelection()))
        self.frame.operateMenu.Enable(self.frame.menuAddDetailIAP.GetId(), (2 == self.nb.GetSelection()))
        self.frame.operateMenu.Enable(self.frame.menuAddCarExpenses.GetId(), (3 == self.nb.GetSelection()))

def main():
    app = MainApp()

    if not GlobalModule.isLogin:
        app.Exit()

    app.MainLoop()

if __name__ == '__main__':
    main()
