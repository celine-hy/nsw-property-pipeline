# Data notes

Sources: the official fact sheet "Current Property Sales Data File (Format 2001 - current)", May 2020
(`data/reference/Current_Property_Sales_Data_File_Format_2001_to_Current.pdf`), and my own exploration of
the 20261019 weekly file. Where the guide and the real files disagree, both are written down. Do not guess.

## File layout
- Download source: https://www.valuergeneral.nsw.gov.au/__psi/weekly/YYYYMMDD.zip, opened in a browser.
  The official page (https://valuation.property.nsw.gov.au/embed/propertySalesInformation) shows
  "Content cannot be accessed" for its file list (Cloudflare bot protection, ~June 2026).
  URL pattern from github.com/jameselks/nsw-property-sales-data-cleaner, confirmed by downloading 4 files.
- Zip naming: YYYYMMDD.zip, the Monday of the reporting week.
- Zip contents: creative_commons.txt (CC Attribution, Australian port, no version, dated 2015-09-21)
  plus one .DAT per district (~130 files in 20261019.zip).
- .DAT naming: `<district code>_SALES_DATA_NNME_<DDMMYYYY>.DAT`
  - The 3-digit prefix matches the District Code in the A record (checked on file 043).
  - Date in the .DAT name is DDMMYYYY; the zip name is YYYYMMDD.
  - "NNME": not explained in the guide. TBC.
- File structure: delimited flat ASCII (guide), confirmed by `file` ("ASCII text").
- Delimiter: semicolon `;`. Empty fields appear as `;;`. Every record ends with a trailing `;`,
  so splitting a line gives one extra empty field at the end.
- Line ending: LF.
- Multi-record-type file: the first field is the record type. A is first, Z is last.

## Record types
| Record type | What it represents | Key fields |
| --- | --- | --- |
| A | Header, first record. File type, district code, download date/time | district_code |
| B | One sale: property address and sale details | district_code, property_id, sale_counter |
| C | Property legal description. **There can be several C records per property**; join their text without a space, in file order | district_code, property_id, sale_counter |
| D | Purchaser / vendor marker. Owner details are suppressed, only P or V is given | district_code, property_id, sale_counter |
| Z | Trailer, last record. Total records (incl. A and Z) and counts of B, C, D | — |

`sale_counter` is "unique for file" (guide), so it is **not** a global id. B, C and D link on
(district_code, property_id, sale_counter) within one file only.

## Field notes
Type in the guide: A = alphanumeric, N = numeric, Date. Size = maximum length. Req = required (Y/N).

### A — Header
| # | Field | Type | Size | Req | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Record type | A | 1 | Y | `A` |
| 2 | File type | A | 12 | Y | `RTSALEDATA` |
| 3 | District code | A | 3 | Y | e.g. `077`; keep as string (leading zeros) |
| 4 | Download date/time | Date | 16 | Y | `CCYYMMDD HH24:MI` |
| 5 | Submitter's user id | A | 35 | N | |

### B — Sale
| # | Field | Type | Size | Req | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Record type | — | 1 | Y | `B` |
| 2 | District code | A | 3 | Y | |
| 3 | Property id | A | 10 | Y | Guide says A here but N in C/D. Keep as string |
| 4 | Sale counter | A | 7 | Y | Unique within the file only |
| 5 | Download date/time | A | 16 | Y | `CCYYMMDD HH24:MI` |
| 6 | Property name | N | 40 | N | Guide says N, but it is a name. Treat as string |
| 7 | Unit number | A | 10 | N | Unit number + suffix, space separated |
| 8 | House number | A | 10 | N | Prefix + number + suffix, e.g. `A125B` |
| 9 | Street name | A | 38 | N | Name + type + suffix + locality descriptor, e.g. `Green Lane NW` |
| 10 | Locality (suburb) | A | 40 | N | Guide comment for this field is a copy-paste error (describes a date) |
| 11 | Post code | N | 4 | N | Keep as string |
| 12 | Area | N | 7.3 | N | e.g. `7777777.333` |
| 13 | Area type | A | 1 | N | `M` = square metres, `H` = hectares. Needed to convert units |
| 14 | Contract date | Date | 8 | Y | `CCYYMMDD` |
| 15 | Settlement date | Date | 8 | Y | `CCYYMMDD` |
| 16 | Purchase price | N | 12 | Y | Whole dollars (TBC: check for cents/zero) |
| 17 | Zoning | A | 4 | N | Codes in the Zone Codes guide |
| 18 | Nature of property | A | 1 | N | `V` = vacant, `R` = residence, `3` = other |
| 19 | Primary purpose | A | 20 | N | Guide: filled when nature = 3. Seen filled when nature = R too |
| 20 | Strata lot number | A | 5 | N | Strata properties only |
| 21 | Component code | A | 3 | N | Not explained in this guide. TBC |
| 22 | Sale code | A | 3 | N | Not explained in this guide. TBC |
| 23 | % interest of sale | A | 3 | N | Empty means 100% |
| 24 | Dealing number | A | 10 | Y | Candidate for a cross-file sale id. TBC in phase 1 |

Observed: a real B record has exactly 24 fields plus the trailing empty one, matching the guide.

### C — Legal description
| # | Field | Type | Size | Req | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Record type | A | 1 | Y | `C` |
| 2 | District code | A | 3 | Y | |
| 3 | Property id | N | 10 | Y | |
| 4 | Sale counter | N | 7 | Y | |
| 5 | Download date/time | Date | 16 | Y | |
| 6 | Property legal description | A | 70 | Y | Cut at 70 chars; multiple C records are joined without a space |

### D — Purchaser / vendor
| # | Field | Type | Size | Req | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Record type | A | 1 | Y | `D` |
| 2 | District code | A | 3 | Y | |
| 3 | Property id | N | 10 | Y | |
| 4 | Sale counter | N | 7 | Y | |
| 5 | Download date/time | Date | 16 | Y | |
| 6 | Purchaser / vendor | A | 1 | Y | `P` = purchaser, `V` = vendor |

Observed: real D records have **5 extra empty fields** after field 6 (suppressed owner details).
The parser must not assume the field count in the guide.

### Z — Trailer
| # | Field | Type | Size | Req | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | Record type | A | 1 | Y | `Z` |
| 2 | Total records | N | 12 | Y | Includes A and Z |
| 3 | Total B records | N | 12 | Y | |
| 4 | Total C records | N | 12 | Y | |
| 5 | Total D records | N | 12 | N | |

The Z counts give a free quality check: counted rows must equal the trailer.

## Data problems found during exploration
Sample: 4 weekly files (20260928, 20261005, 20261012, 20261019), 14,069 B records.
### Found while building silver (2026-10-30, 4 weeks)
- [x] Strata lots sold in one dealing share one property_id (the strata plan's parent property) and
      differ by strata_lot_number and legal_description, e.g. 7 lots of SP96758 in one dealing.
      unit_number can repeat across lots, so it cannot identify a lot.
- [x] 8 sales appear twice inside the same file, identical except for sale_counter.
- [x] 37 B records have no property_id (required field); they are quarantined.
- [x] 2 contract dates are before 2001 (1926, 1976); quarantined as errors.

### Structure
- [x] The 3-digit file name prefix is the district code (matches the A record).
- [x] B, C, D link on (district_code, property_id, sale_counter) within one file.
- [x] One sale can have several D records (e.g. 1 P + 2 V).
- [x] Z trailer counts reconcile with parsed rows (week 20261019: 3,199 = 3,199).
- [ ] Z trailer present in every file of every week (checked on one week only).
- [ ] D records have 5 more empty fields than the guide lists.

### Volume
- B records per week: 3,621 / 4,297 / 2,952 / 3,199. Weekly volume varies by ~±20%.

### Missing values (week 20261019; empty or whitespace = missing)
- sale_code 100% empty: field not populated.
- pct_interest 99.2% empty (= 100% interest); ~0.8% are partial-interest sales.
- unit_number 66.3%, strata_lot_number 60.3%: expected, strata/unit only.
- zoning and component_code both 45.6%: same rate, check if always missing together.
- area and area_type both 20.8%: missing as a pair.
- post_code 1.5%, locality 0.1%.
- property_id 0.1% missing although required.
- contract_date: 3 of 14,069 empty although required.

### Multi-property sales
- [x] One dealing can cover several properties. Week 20261019: 96 dealing_numbers span 220 B rows.
- [x] In all 96, every row repeats the **total** sale price. Counting rows overstates volume
      (3,199 rows vs 3,075 dealings) and per-row prices are not per-property prices.

### Duplicates across weeks
- [x] 13,698 distinct dealing_numbers; 35 (0.26%) appear in two weeks, none in three or more.
- [x] The repeated records are identical (no field differs apart from download_datetime,
      sale_counter and file/week). They are re-publications, not corrections.

### Prices (week 20261019)
- No zero, negative or unparseable prices.
- Median $921,000 vs mean $1,497,955: right-skewed, so use the median.
- 6 below $10,000: 5 are rural vacant land (plausible), 1 residence (likely nominal transfer).
- 40 above $10,000,000: mostly nature_of_property = 3 (commercial, farm); residences are in
  high-value suburbs.

### Dates (4 weeks)
- Contract → settlement gap: median 42 days, IQR 35–79 days. No settlement before contract.
- 987 records (7%) have a gap over 365 days.
- Contract year: 2026 = 12,417 (88%), 2025 = 871, 2024 = 328, 2023 = 182, 2022 = 147,
  2021 = 103, a handful 2006–2020, and 1926 and 1976 (almost certainly errors).
- Weekly files contain sales contracted months or years earlier: **late-arriving data**.

### Formats
- house_number can contain a space (e.g. "52 A"), unlike the guide's example "A125B".
- primary_purpose is almost always filled, not only when nature_of_property = 3.
- Dealing numbers in this sample start with a letter prefix (e.g. "AV"). Meaning: TBC.
- area_type mixes M (square metres) and H (hectares); convert before comparing areas.

### Still unknown
- [ ] Meaning of NNME, component_code, sale_code, the dealing number prefix.