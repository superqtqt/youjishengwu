import akshare as ak
import pymongo
from datetime import datetime
import time
import yaml
from pymongo import UpdateOne
from db_base import MongoDBBase

class StockDataCollector(MongoDBBase):
    def __init__(self):
        super().__init__()
        self.field_mapping = {
            '总市值': 'total_market_value',
            '流通市值': 'circulating_market_value',
            '行业': 'industry',
            '上市时间': 'listing_date',
            '股票代码': 'stock_code',
            '股票简称': 'stock_name',
            '总股本': 'total_shares',
            '流通股': 'circulating_shares',
            '代码': 'stock_code',  # 股票列表中的字段
            '名称': 'stock_name',  # 股票列表中的字段
        }

         # 为所有历史数据集合创建索引
        for adjust in ["", "qfq", "hfq"]:
            collection_name = "stock_history" if not adjust else f"stock_history_{adjust}"
            self.db[collection_name].create_index([
                ("stock_code", 1),
                ("trade_date", 1)
            ], unique=True)
        
    def get_stock_list(self):
        """获取所有A股股票列表"""
        try:
            df = ak.stock_zh_a_spot_em()
            # 重命名列
            df = df.rename(columns={
                '代码': 'stock_code',
                '名称': 'stock_name'
            })
            return df[['stock_code', 'stock_name']].values.tolist()
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return []

    def get_stock_info(self, stock_code):
        """获取单个股票的基本信息"""
        try:
            info = ak.stock_individual_info_em(symbol=stock_code)
            # 转换为字典并重命名字段
            info_dict = {}
            for _, row in info.iterrows():
                if row['item'] == '上市时间':
                    info_dict['listing_date'] = row['value']
                elif row['item'] == '行业':
                    info_dict['industry'] = row['value']
                # 可以添加其他字段的映射
            return info_dict
        except Exception as e:
            print(f"获取股票 {stock_code} 信息失败: {e}")
            return None
    # def get_stock_market_info(self, stock_code):
        """获取股票的市值等信息"""
        try:
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == stock_code].iloc[0]
            
            # 提取并转换所需字段
            market_info = {
                'total_market_value': stock_data.get('总市值', None),
                'circulating_market_value': stock_data.get('流通市值', None),
                'total_shares': stock_data.get('总股本', None),
                'circulating_shares': stock_data.get('流通股', None),
            }
            return market_info
        except Exception as e:
            print(f"获取股票 {stock_code} 市值信息失败: {e}")
            return None
        
    def get_stock_history(self, stock_code, start_date, adjust=""):
        """
        获取股票历史数据
        :param stock_code: 股票代码
        :param start_date: 开始日期，格式：YYYYMMDD
        :param adjust: 复权类型：空串-不复权 qfq-前复权 hfq-后复权
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            df = ak.stock_zh_a_hist(symbol=stock_code, start_date=start_date, 
                                  end_date=end_date, adjust=adjust)
            return df.to_dict('records')
        except Exception as e:
            print(f"获取股票 {stock_code} 历史数据失败: {e}")
            return []

    def save_to_mongodb(self,begin_time=""):
        """保存所有数据到MongoDB"""
        stocks = self.get_stock_list()
        
        for stock_code, stock_name in stocks:
            print(f"正在处理: {stock_code} {stock_name}")
            
            # 获取股票基本信息
            stock_info = self.get_stock_info(stock_code)
            # market_info = self.get_stock_market_info(stock_code)
            
            if stock_info is not None:
                # 合并基本信息和市值信息
                stock_data = {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    **stock_info,
                    # **(market_info or {})
                }
                
                # 保存股票信息
                self.db.stock_info.update_one(
                    {"stock_code": stock_code},
                    {
                        "$set": {
                            **stock_data,
                            "update_time": datetime.now()
                        }
                    },
                    upsert=True
                )
                
                # 获取上市日期
                start_date=begin_time
                if not start_date:
                    start_date = stock_info.get('listing_date')
                    
                # 保存三种复权方式的历史数据
                for adjust in ["", "qfq", "hfq"]:
                    history_data = self.get_stock_history(stock_code, start_date, adjust)
                    if history_data:
                        # 设置集合名称，空值时不添加下划线
                        collection_name = "stock_history"
                        if adjust:
                            collection_name = f"stock_history_{adjust}"
                        
                        # 批量更新操作列表
                        bulk_operations = []
                        current_time = datetime.now().strftime('%Y%m%d %H%M%S')
                        for daily_data in history_data:
                            # 确保日期字段存在
                            trade_date = daily_data.get('日期')
                            if trade_date:
                                # 构建文档
                                formatted_date = trade_date.strftime('%Y%m%d')
                                doc = {
                                    "stock_code": stock_code,
                                    "stock_name": stock_name,
                                    "trade_date": formatted_date,
                                    "open": daily_data.get('开盘'),
                                    "close": daily_data.get('收盘'),
                                    "high": daily_data.get('最高'),
                                    "low": daily_data.get('最低'),
                                    "volume": daily_data.get('成交量'),
                                    "amount": daily_data.get('成交额'),
                                    "amplitude": daily_data.get('振幅'),
                                    "change_percent": daily_data.get('涨跌幅'),
                                    "change_amount": daily_data.get('涨跌额'),
                                    "turnover": daily_data.get('换手率'),
                                    "update_time": current_time
                                }
                                
                                # 创建更新操作
                                bulk_operations.append(
                                    UpdateOne(
                                        {
                                            "stock_code": stock_code,
                                            "trade_date": formatted_date
                                        },
                                        {"$set": doc},
                                        upsert=True
                                    )
                                )
                        
                        # 如果有数据要更新，执行批量操作
                        if bulk_operations:
                            try:
                                self.db[collection_name].bulk_write(bulk_operations)
                            except Exception as e:
                                print(f"批量更新 {stock_code} 的历史数据时出错: {e}")
            
            time.sleep(1)

if __name__ == "__main__":
    collector = StockDataCollector()
    collector.save_to_mongodb() 