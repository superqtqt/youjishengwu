# 生成跳空缺口的代码   

import requests
import pandas as pd
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import akshare as ak

def get_yjyg_data(page=1, date='2024-12-31'):
    """
    获取同花顺业绩预告数据
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # 添加更多浏览器配置
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    # 设置 User-Agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    
    try:
        print(f"开始获取第{page}页数据...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 设置页面加载超时时间
        driver.set_page_load_timeout(30)
        driver.set_script_timeout(30)
        
        # 访问页面
        url = f'http://data.10jqka.com.cn/ajax/yjyg/date/{date}/board/ALL/field/jlrbl/order/desc/page/{page}/ajax/1/free/1/'
        print(f"正在访问URL: {url}")
        driver.get(url)
        
        # 等待表格加载
        print("等待表格加载...")
        wait = WebDriverWait(driver, 20)  # 增加等待时间到20秒
        table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'm-table')))
        
        # 获取页面内容
        print("获取页面内容...")
        html = driver.page_source
        
        # 打印页面内容的一部分，用于调试
        print("页面内容预览:", html[:200])
        
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='m-table')
        
        if not table:
            print("未找到数据表格")
            return None
            
        # 提取数据
        data = []
        rows = table.find('tbody').find_all('tr')
        print(f"找到 {len(rows)} 行数据")
        
        for row in rows:
            try:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    stock_code = cols[1].find('a').text.strip()
                    stock_name = cols[2].find('a').text.strip()
                    change_rate = cols[5].text.strip()
                    announce_date = cols[7].text.strip()
                    
                    data.append({
                        '股票代码': stock_code,
                        '股票简称': stock_name,
                        '净利润变动幅度': float(change_rate),
                        '公告日期': announce_date
                    })
            except Exception as e:
                print(f"处理行数据时出错: {e}")
                continue
        
        if not data:
            print("未提取到任何数据")
            return None
            
        print(f"成功提取 {len(data)} 条数据")
        return pd.DataFrame(data)
        
    except Exception as e:
        print(f"获取数据失败: {e}")
        # 打印详细的错误信息
        import traceback
        print(traceback.format_exc())
        return None
        
    finally:
        if 'driver' in locals():
            print("关闭浏览器...")
            driver.quit()

def analyze_data(df):
    """
    分析业绩预告数据
    
    Args:
        df: 包含业绩预告数据的DataFrame
    """
    try:
        # 筛选净利润变动幅度大于50的股票
        high_growth_df = df[df['净利润变动幅度'] > 50].copy()
        print(f"筛选出 {len(high_growth_df)} 条净利润变动幅度大于50的股票")
        for _, row in high_growth_df.iterrows():
            try:
                stock_code = row['股票代码']
                announce_date = row['公告日期']
                stock_name = row['股票简称']
                
                
                # print(f"\n正在获取 {stock_code} {stock_name} 的行情数据...")
                
                # 获取行情数据（获取前后10天的数据，以确保能覆盖3个交易日）
                stock_data = ak.stock_zh_a_hist(symbol=stock_code, 
                                              period="daily", 
                                              start_date=(pd.to_datetime(announce_date) - pd.Timedelta(days=3)).strftime('%Y%m%d'),
                                              end_date=(pd.to_datetime(announce_date) + pd.Timedelta(days=3)).strftime('%Y%m%d'),
                                              adjust="")
                
                if not stock_data.empty:
                     for i in range(1, len(stock_data)):
                        today_open = stock_data['开盘'].iloc[i]
                        yesterday_high = stock_data['最高'].iloc[i-1]
                        yesterday_low = stock_data['最低'].iloc[i-1]
                        gap_ratio = (today_open - yesterday_high)/yesterday_high

                        # 如果今天开盘价高于昨天最高价，则发生跳空高开
                        if today_open > yesterday_high and gap_ratio > 0.01:
                            print(f"股票代码: {stock_code}, 股票简称: {stock_name}, 公告日期: {announce_date}, 跳空高开幅度: {gap_ratio}")
                            break
                
                time.sleep(1)  # 添加延时避免请求过快
                
            except Exception as e:
                print(f"获取 {stock_code} 行情数据时出错: {e}")
                continue
       
        
    except Exception as e:
        print(f"分析数据时出错: {e}")
        return None


def main():
    """主函数"""
    all_data = []
    page = 1
    date = '2024-12-31'
    
    while True:
        try:
            print(f"\n尝试爬取第 {page} 页...")
            df = get_yjyg_data(page, date)
            if df is not None and not df.empty:
                all_data.append(df)
                if (df['净利润变动幅度'] < 50).any():
                    break
        except Exception as e:
            print(f"爬取出错: {e}")
            
        page += 1
        print(f"等待 3 秒后继续...")
        time.sleep(3)
        # 测试
        # break
    
    if all_data:
        final_df = pd.concat(all_data, ignore_index=True)
        # final_df.to_excel('业绩预告数据.xlsx', index=False)
        print(f"数据爬取完成，共{len(final_df)}条记录")
        
        # 分析数据
        analyze_data(final_df)
        
      
    else:
        print("未获取到任何数据")

if __name__ == "__main__":
    main()
