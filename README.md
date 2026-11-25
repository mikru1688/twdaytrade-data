# twdaytrade-data

Daily after-hours open data snapshots used by the TWDayTrade iOS app.

A scheduled GitHub Actions workflow fetches public open-data endpoints on weekdays (Taipei 14:43 for the TAIFEX day session, 17:47, 21:13, next-morning 07:13 check incl. TAIFEX night session, and 09:17 backup) and stores the raw JSON (compact, gzip-compressed) under `data/raw/<source>/<YYYY-MM-DD>.json.gz`. Files are written only when the content changes. Company-profile sources are fetched weekly (Mondays).

## Data sources and license

All data comes from Taiwan Stock Exchange and Taipei Exchange OpenAPI endpoints and Taiwan Futures Exchange data.gov.tw CSV downloads, published as government open data under the [Open Government Data License, version 1.0](https://data.gov.tw/license) (政府資料開放授權條款－第1版). TAIFEX CSV files are converted to JSON rows before storage. Provider: Securities and Futures Bureau, Financial Supervisory Commission (金融監督管理委員會證券期貨局). Per-dataset license entries on data.gov.tw are being verified; sources that do not qualify will be removed.

| Source | Endpoint |
|---|---|
| 上櫃股票三大法人買賣明細資訊 | `https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading` |
| 上櫃股票投信買賣超彙總表 | `https://www.tpex.org.tw/openapi/v1/tpex_3insti_trading` |
| 上市公司基本資料 | `https://openapi.twse.com.tw/v1/opendata/t187ap03_L` |
| 上櫃股票基本資料 | `https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O` |
| 上市個股日成交資訊 | `https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL` |
| 上櫃股票收盤行情 | `https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes` |
| 集中市場漲跌證券數統計表（追蹤是否恢復更新） | `https://openapi.twse.com.tw/v1/opendata/twtazu_od` |
| 臺指選擇權Put/Call比（data.gov.tw 11322） | `https://www.taifex.com.tw/data_gov/taifex_open_data.asp?data_name=PutCallRatio` |
| 期貨市場三大法人-區分各期貨契約-依日期（11596） | `…?data_name=MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate` |
| 期貨大額交易人未沖銷部位資料（11337） | `…?data_name=OpenInterestOfLargeTradersFutures` |
| 期貨每日交易行情（11319，含一般／盤後交易時段） | `…?data_name=DailyMarketReportFut` |

The data is for reference only. Announcements by the Taiwan Stock Exchange, the Taipei Exchange and the Taiwan Futures Exchange prevail. Nothing here is investment advice.
