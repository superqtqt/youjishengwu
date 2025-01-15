# 爬去网站数据存储在mongodb中
接口来源：https://akshare.akfamily.xyz/data/stock/stock.html#id10

爬去步骤如下
1、使用接口stock_zh_a_spot_em获取所有股票的列表
2、通过接口stock_individual_info_em获取每个股票的上市日志
3、通过接口stock_zh_a_hist获取每个股票的日线数据，分为不复权、前复权和后复权数据存储到mongodb中