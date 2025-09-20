# bo-nalog-client

Async client for accessing financial reports (BFO) from the Russian tax service (bo.nalog.gov.ru).

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/yourusername/bo-nalog-client.git
```

Or clone and install locally:

```bash
git clone https://github.com/yourusername/bo-nalog-client.git
cd bo-nalog-client
pip install -e .
```

## Usage

```python
from bo_nalog_client import NalogClient

client = NalogClient()
async with client:
    year, revenue, profit = await client.get_last_year_revenue_profit(9392519)
    print(f"Year: {year}, Revenue: {revenue}, Profit: {profit}")
```

## Features

- Async HTTP client using httpx
- Structured data models with Pydantic
- Easy access to financial reports (BFO)
- Revenue and profit extraction
- Support for multiple report formats

## Requirements

- Python 3.8+
- httpx
- pydantic

## License

MIT License