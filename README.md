# Calculating VIX

This notebook allows calculation of VIX, given a .dat file downloaded from:

> http://www.cboe.com/delayedquote/quote-table-download

Get the VIX white paper at:
> http://www.cboe.com/framed/pdfframed?content=/micro/vix/vixwhite.pdf&section=SEC_INSTITUTIONAL_PRODUCTS&title=Cboe%20Volatility%20Index%20-%20VIX%20White%20Paper%0D%0A

Rate retrieved from:
> https://www.treasury.gov/resource-center/data-chart-center/interest-rates/Pages/TextView.aspx?data=yield

A sample dat file is provided to recreate my calculation of VIX.

If you know how to use this notebook & download new quotes, make sure you update variable 'NOW' accordingly in cell 6 to accurately reflect CBOE quote time, which is U.S. Central Time. Some knowledge of using timedeltas is needed in order to account for your offset from CST/CDT (UTC/GMT -6 hours ).

Please also note, the dat file used in developing this notebook was downloaded from CBOE on Sunday 22 March; making SPX historical quotes valid for Friday 20 March. The final quote for VIX, from CBOE, at 16:10 on Friday 20 March was 66.39, 0.13392 greater than the VIX calculated in the notebook.


Package requirements:
pandas
numpy
beautifulsoup4
