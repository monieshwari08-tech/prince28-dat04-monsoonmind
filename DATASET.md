# Dataset: MonsoonMind

Explains Tamil Nadu's monsoon and weather history from IMD reports (northeast monsoon statistics, district rainfall, cyclone reports) and sets it next to live forecasts.

- **Start target:** 10 years of NE monsoon reports + 20 cyclone reports
- **Full target:** All monsoon, cyclone and RMC reports since 2010 (4,000+ pages)
- **Collected by:** `scripts/fetch.py`; source URLs and download metadata are recorded in `data/manifest.jsonl`.

## Where the documents come from

- https://mausam.imd.gov.in/
- https://rsmcnewdelhi.imd.gov.in/
- https://open-meteo.com/

## Terms I follow

Public IMD publications; copyright applies unless a source states otherwise. Open-Meteo data is provided under CC BY 4.0.

- Every answer links to the original document.
- No personal data is collected.

<!-- generated:start -->

## Measured corpus

- **PDF files:** 23
- **Pages:** 2908
- **Local size:** 297.29 MB
- **Pages with extractable text:** 2900 / 2908
- **Estimated extracted text:** 3,885,308 characters
- **Estimated tokens per page:** 334 (characters ÷ 4)

### By source

| Source | Files | Pages | Size (MB) |
|---|---:|---:|---:|
| imd_chennai | 9 | 499 | 79.26 |
| imd_metnet | 2 | 286 | 52.13 |
| imd_rsmc | 12 | 2123 | 165.91 |

### Downloaded documents

| Document | Source | Pages | Size (MB) | Text pages |
|---|---|---:|---:|---:|
| Annual Cyclone Report 2005 | imd_rsmc | 66 | 2.16 | 66 |
| Annual Cyclone Report 2006 | imd_rsmc | 89 | 3.09 | 89 |
| Annual Cyclone Report 2009 | imd_rsmc | 122 | 4.02 | 122 |
| Annual Cyclone Report 2010 | imd_rsmc | 162 | 6.21 | 162 |
| Annual Cyclone Report 2011 | imd_rsmc | 186 | 14.82 | 186 |
| Annual Cyclone Report 2012 | imd_rsmc | 214 | 10.52 | 214 |
| Annual Cyclone Report 2014 | imd_rsmc | 241 | 26.98 | 241 |
| Annual Cyclone Report 2015 | imd_rsmc | 338 | 15.34 | 338 |
| Annual Cyclone Report 2017 | imd_rsmc | 328 | 19.86 | 323 |
| Annual Cyclone Report 2021 | imd_rsmc | 345 | 57.17 | 345 |
| Annual Cyclone Report 2024 | imd_rsmc | 22 | 3.58 | 22 |
| IMD Annual Report 2016 - Northeast Monsoon coverage | imd_metnet | 142 | 24.53 | 142 |
| IMD Annual Report 2017 - Northeast Monsoon coverage | imd_metnet | 144 | 27.59 | 141 |
| Northeast Monsoon 2018 | imd_chennai | 35 | 3.76 | 35 |
| Northeast Monsoon 2019 | imd_chennai | 38 | 6.80 | 38 |
| Northeast Monsoon 2020 | imd_chennai | 55 | 10.71 | 55 |
| Northeast Monsoon 2021 | imd_chennai | 63 | 11.08 | 63 |
| Northeast Monsoon 2022 | imd_chennai | 66 | 11.50 | 66 |
| Northeast Monsoon 2023 | imd_chennai | 85 | 12.78 | 85 |
| Northeast Monsoon 2024 | imd_chennai | 79 | 10.86 | 79 |
| Northeast Monsoon 2025 | imd_chennai | 56 | 9.97 | 56 |
| Salient Features of Cyclonic Disturbances 2022 | imd_rsmc | 10 | 2.15 | 10 |
| Salient Features of Northeast Monsoon 2016 | imd_chennai | 22 | 1.80 | 22 |

<!-- generated:end -->

## Known gaps

- Only 8 dedicated annual Northeast Monsoon reports (2018–2025) are confirmed in the current collection. 2016 and 2017 have supporting IMD annual reports, not confirmed dedicated annual NEM reports.
- Some reports may be scanned or have little extractable text; inspect the text-page counts above.
- IMD copyright and permission for displaying full report text require manual review.
