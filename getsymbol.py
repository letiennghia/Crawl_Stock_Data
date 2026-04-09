
import pandas as pd
symbols = ["HOSE:VIC","HOSE:VCB","HOSE:VHM","HOSE:BID","HOSE:CTG","HOSE:TCB","HOSE:MBB","HOSE:VPB","HOSE:HPG","HOSE:GAS","HOSE:VPL","HOSE:BSR","HOSE:GVR","HOSE:HDB","HOSE:VNM","HOSE:FPT","HOSE:LPB","HOSE:ACB","HOSE:MWG","HOSE:STB","HOSE:MSN","HOSE:VJC","HOSE:GEE","HOSE:SHB","HOSE:SSI","HOSE:VRE","HOSE:BVH","HOSE:VIB","HOSE:SAB","HOSE:BCM","HOSE:PLX","HOSE:SSB","HOSE:TPB","HOSE:EIB","HOSE:VIX","HOSE:POW","HOSE:PNJ","HOSE:REE","HOSE:MSB","HOSE:GEX","HOSE:GMD","HOSE:NVL","HOSE:VCI","HOSE:KBC","HOSE:OCB","HOSE:KDH","HOSE:FRT","HOSE:HCM","HOSE:VND","HOSE:DCM","HOSE:NAB","HOSE:VGC","HOSE:HAG","HOSE:DPM","HOSE:PVD","HOSE:DGC","HOSE:SBT","HOSE:VPI","HOSE:PDR","HOSE:DXG","HOSE:TCH","HOSE:SIP","HOSE:SJS","HOSE:VCG","HOSE:NLG","HOSE:KDC","HOSE:VHC","HOSE:CII","HOSE:VTP","HOSE:DIG","HOSE:PC1","HOSE:BMP","HOSE:HDG","HOSE:EVF","HOSE:PVT","HOSE:DGW","HOSE:DSE","HOSE:CTR","HOSE:FTS","HOSE:BWE","HOSE:HSG","HOSE:BSI","HOSE:VSC","HOSE:DBC","HOSE:CTD","HOSE:IMP","HOSE:KOS","HOSE:PHR","HOSE:NT2","HOSE:CMG","HOSE:HHV","HOSE:PAN","HOSE:NKG","HOSE:ANV","HOSE:CTS","HOSE:HT1","HOSE:SZC","HOSE:SCS","HOSE:DXS","HOSE:HDC"]
symbols_without_exchange = []
for symbol_with_exchange in symbols:
    split_symbol_exchange = symbol_with_exchange.split(":")
    symbol = split_symbol_exchange[1]
    symbols_without_exchange.append(symbol)
pd_symbol = pd.DataFrame(symbols_without_exchange,columns=['symbol'])
pd_symbol.to_csv('vn100.csv', index=False)
