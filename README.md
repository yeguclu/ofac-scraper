# OFAC Tracker

A Python script that scrapes OFAC sanctions list updates, extracts Ethereum addresses from sanctioned entities and individuals, and tracks additions and deletions.

## Overview

This script monitors OFAC sanctions list updates and identifies:
- **Additions**: Individuals and entities added to the sanctions list that have Ethereum addresses
- **Deletions**: Names removed from the sanctions list

The script automatically updates `data.csv` with changes and tracks the last processed date in `log.txt` for continuous operation.

## Main Flow

1. **Collect Content Pages**: Scrapes the OFAC recent actions page (`https://ofac.treasury.gov/recent-actions/sanctions-list-updates`) and collects all update pages within the specified date range.

2. **Extract Names**: For each content page, extracts:
   - Individuals added to the SDN List
   - Entities added to the SDN List
   - Deletions from the SDN List

3. **Query OFAC Search**: For each added individual/entity, queries the OFAC sanctions search database (`https://sanctionssearch.ofac.treas.gov/`) to find their detail page.

4. **Extract Ethereum Addresses**: Fetches the detail page and extracts Ethereum addresses from the identification section (looks for "Digital Currency Address - ETH" type).

5. **Update data.csv**: Applies all changes chronologically to `data.csv`:
   - **Additions**: Adds new rows with `(date_added, address, name)`
   - **Deletions**: Removes all rows with matching names

6. **Save Last Processed Date**: Saves the end date to `log.txt` for the next run.

## Requirements

```bash
pip install -r requirements.txt
```

## Usage

### Default (Continue from Last Processed Date)

Run without arguments to continue from the last processed date:

```bash
python main.py
```

The script will:
1. Read the last processed date from `log.txt` (or fall back to the latest date in `data.csv` if `log.txt` doesn't exist)
2. Process all updates from that date until today
3. Update `data.csv` with changes
4. Save today's date to `log.txt`

### Single Date (from date to now)

Parse all updates from a specific date until today:

```bash
python main.py START_DATE
```

Example:
```bash
python main.py 2024-01-01
```

This will collect all OFAC updates from January 1, 2024 to today.

### Date Range (start and end dates)

Parse updates within a specific date range:

```bash
python main.py START_DATE END_DATE
```

Example:
```bash
python main.py 2024-01-01 2024-12-31
```

This will collect all OFAC updates from January 1, 2024 to December 31, 2024.

### Test Mode

Test the Ethereum address extraction functionality:

```bash
python main.py --test
```

## Date Format

All dates must be in `YYYY-MM-DD` format (e.g., `2024-01-15`).

## Output Format

The script outputs to stdout:

- **Additions**: `Addition: YYYY-MM-DD HH:MM:SS - Name - 0x...`
- **Deletions**: `Deletion: YYYY-MM-DD HH:MM:SS - Name`

Example output:
```
Addition: 2024-12-03 00:00:00 - MUNOZ UCROS, Monica - 0xd5ed34b52ac4ab84d8fa8a231a3218bbf01ed510
Deletion: 2024-12-03 00:00:00 - SOBOLEV, Nikita Aleksandrovich
```