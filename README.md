# twdaytrade-data

Daily after-hours open data snapshots used by the TWDayTrade iOS app.

A scheduled GitHub Actions workflow fetches public open-data endpoints on weekday evenings (Taipei time) and stores the raw JSON (compact, gzip-compressed) under `data/raw/<source>/<YYYY-MM-DD>.json.gz`. Files are written only when the content changes. Company-profile sources are fetched weekly (Mondays).

## Data sources and license

All data comes from Taiwan Stock Exchange and Taipei Exchange OpenAPI endpoints published as government open data under the [Open Government Data License, version 1.0](https://data.gov.tw/license) (政府資料開放授權條款－第1版). Provider: Securities and Futures Bureau, Financial Supervisory Commission (金融監督管理委員會證券期貨局). Per-dataset license entries on data.gov.tw are being verified; sources that do not qualify will be removed.

| Source | Endpoint |
|---|---|
| 上櫃股票三大法人買賣明細資訊 | `https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading` |
| 上櫃股票投信買賣超彙總表 | `https://www.tpex.org.tw/openapi/v1/tpex_3insti_trading` |
| 上市公司基本資料 | `https://openapi.twse.com.tw/v1/opendata/t187ap03_L` |
| 上櫃股票基本資料 | `https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O` |
| 上市個股日成交資訊 | `https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL` |
| 上櫃股票收盤行情 | `https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes` |
| 集中市場漲跌證券數統計表（追蹤是否恢復更新） | `https://openapi.twse.com.tw/v1/opendata/twtazu_od` |

The data is for reference only. Announcements by the Taiwan Stock Exchange and the Taipei Exchange prevail. Nothing here is investment advice.
