from apscheduler.schedulers.blocking import BlockingScheduler
from stock_data_collector import StockDataCollector
from datetime import datetime, timedelta
import logging


def update_daily_stock_data():
    """每日更新股票数据"""
    try:
        logging.info("开始更新每日股票数据")
        
        # 创建数据采集器实例
        collector = StockDataCollector()
        
        # 获取昨天的日期作为查询起点
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
        
        # 获取所有股票列表
        stocks = collector.get_stock_list()
        
        for stock_code, stock_name in stocks:
            try:
                logging.info(f"正在更新股票: {stock_code} {stock_name}")
                collector.save_to_mongodb(yesterday)
                    history_data = collector.get_stock_history(stock_code, yesterday, adjust)
                    if history_data:
                        # 设置集合名称
                        collection_name = "stock_history"
                        if adjust:
                            collection_name = f"stock_history_{adjust}"
                        
                        # 批量更新操作列表
                        bulk_operations = []
                        current_time = datetime.now().strftime('%Y%m%d%H%M%S')
                        
                        for daily_data in history_data:
                            trade_date = daily_data.get('日期')
                            if trade_date:
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
                                
                                bulk_operations.append(
                                    collector.db[collection_name].update_one(
                                        {
                                            "stock_code": stock_code,
                                            "trade_date": formatted_date
                                        },
                                        {"$set": doc},
                                        upsert=True
                                    )
                                )
                        
                        # 执行批量更新
                        if bulk_operations:
                            collector.db[collection_name].bulk_write(bulk_operations)
                            
            except Exception as e:
                logging.error(f"更新股票 {stock_code} 数据时出错: {e}")
                continue
                
        logging.info("每日股票数据更新完成")
        
    except Exception as e:
        logging.error(f"更新过程中发生错误: {e}")
