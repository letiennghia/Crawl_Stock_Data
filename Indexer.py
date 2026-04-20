from vnstock import Listing
from vnstock import Company
from vnstock.core.utils.auth import register_user
from vnstock.core.utils.auth import check_status
import pandas as pd

# Hoặc sử dụng VCI (dữ liệu đầy đủ hơn nhưng không chạy được trên Colab)
register_user()
status = check_status()
print(status)
listing = Listing(source='VCI')

df = listing.symbols_by_exchange(exchange='HOSE')
df2 = listing.symbols_by_group(group_name='VN100')
# Loc cac ma tren san HOSE va HNX
df = df[~df['exchange'].isin(['UPCOM', 'OTC', 'DELISTED', 'UNLISTED']) & df['type'].isin(['STOCK'])]
print(df.shape)
print(df.head())
print(df2.shape)
print(df2.head())
df2.to_csv('vn100.csv', index=False)