import log_init
import logging
from stock_data_collector import BlockingScheduler
from stock_data_scheduler import update_daily_stock_data

if __name__=="__main__":
    try:
        scheduler = BlockingScheduler()
        
        # 添加定时任务，每天4点执行
        scheduler.add_job(
            update_daily_stock_data,
            trigger='cron',
            hour=16,
            minute=0,
            id='daily_stock_update'
        )
        
        logging.info("调度器已启动，等待执行定时任务...")
        scheduler.start()
        
    except Exception as e:
        logging.error(f"调度器启动失败: {e}")