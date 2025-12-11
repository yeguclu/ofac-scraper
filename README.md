# OFAC Tracker

Scrapes OFAC sanctions list updates and collects content page URLs.

## Usage

```bash
pip install -r requirements.txt
python main.py YYYY-MM-DD
```

Example:
```bash
python main.py 2025-01-01
```

This will collect all content page URLs from OFAC updates until the specified deadline date.
