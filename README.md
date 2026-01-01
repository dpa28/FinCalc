## FinCalc

FinCalc is a desktop application that combines a market tracker with a financial calculator. I built this to bridge the gap between checking real-time market data and actually analyzing it. Whether you are a finance student needing to double-check TVM calculations or just tracking a portfolio, this tool handles the heavy lifting.

## What it does

* **Market Tracker:** Pulls real-time data for stocks and indices so you don't have to switch between browser tabs.
* **Financial Calculator:** Handles the core formulas used in finance courses and investment analysis (NPV, IRR, Time Value of Money).
* **Currency Converter:** accurate exchange rates that update when you have a connection and cache the last known rate for offline use.

## Tech Stack

I wrote the application in Python using the KivyMD framework to handle the UI. This allows it to use Material Design components and run on multiple platforms (Windows, macOS, etc.) without changing the codebase.

**Libraries used:**
* **KivyMD:** For the graphical user interface.
* **Requests:** Handles the HTTP calls to external APIs.

## APIs

To keep the data accurate, the app connects to the following external services:

1.  **Market Data API:** Used for fetching stock prices and daily time-series data.
2.  **Currency Exchange API:** Used to get the current conversion rates for major global currencies.

*Note: You will need your own API keys for these services if you plan on modifying the source code.*

## Setup and Installation

If you want to run this locally, you will need Python 3 installed.

1.  Clone this repository:
    git clone https://github.com/dpa28/fincalc.git

2.  Navigate to the folder:
    cd fincalc

3.  Install the required libraries:
    pip install -r requirements.txt

4.  Run the app:
    python main.py
