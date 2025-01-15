import pymongo
import yaml
from datetime import datetime
import pandas as pd
import logging
from db_base import MongoDBBase


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class StockIndicators(MongoDBBase):
    def __init__(self):
        super().__init__()
        
        # 创建索引
        self.db.stock_index.create_index([
            ("stock_code", 1),
            ("trade_date", 1),
            ("period", 1)
        ], unique=True)

    def calculate_momentum(self, period=5, stock_code=None, calc_date=None):
        """
        计算股票的动量指标（使用前复权数据）
        :param period: 计算周期（1为日动量，5为周动量，22为月动量）
        :param stock_code: 股票代码（可选），为None时计算所有股票
        :param calc_date: 计算日期（可选），为None时使用最新交易日，格式：YYYYMMDD
        """
        try:
            # 获取需要计算的股票代码列表
            if stock_code:
                stock_codes = [stock_code]
            else:
                stock_codes = self.db.stock_info.distinct("stock_code")

            for code in stock_codes:
                try:
                    # 从前复权数据集合获取数据
                    cursor = self.db.stock_history_qfq.find(
                        {"stock_code": code},
                        {"_id": 0, "trade_date": 1, "close": 1, "open": 1}
                    ).sort("trade_date", -1).limit(period)  # 倒序获取指定数量的数据

                    # 转换为DataFrame并正序排列
                    df = pd.DataFrame(list(cursor))
                    if df.empty:
                        logging.warning(f"股票 {code} 没有历史数据")
                        continue

                    # 确保数据按日期排序（正序）
                    df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                    df = df.sort_values('trade_date')

                    # 检查数据是否足够计算动量
                    if len(df) >= period:
                        # 计算动量值：(最后一天收盘价 - 第一天开盘价) / 第一天开盘价 + 1
                        momentum = {
                            "stock_code": code,
                            "trade_date": df.iloc[-1]['trade_date'].strftime('%Y%m%d'),
                            "momentum": ((df.iloc[-1]['close'] - df.iloc[0]['open']) / df.iloc[0]['open']) + 1,
                            "period": period,
                            "update_time": datetime.now().strftime('%Y%m%d%H%M%S')
                        }

                        # 保存到MongoDB
                        self.db.stock_momentum.update_one(
                            {
                                "stock_code": code,
                                "trade_date": momentum["trade_date"],
                                "period": period
                            },
                            {"$set": momentum},
                            upsert=True
                        )
                        logging.info(f"股票 {code} 的 {period}日动量指标计算完成")

                except Exception as e:
                    logging.error(f"计算股票 {code} 的动量指标时出错: {e}")
                    continue

        except Exception as e:
            logging.error(f"计算动量指标时出错: {e}")
