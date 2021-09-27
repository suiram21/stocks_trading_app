# Stocks Trading App

Trading app that simulates buying and selling US stocks

---
### File .env_sample
When you load the application, you should change the filename of **.env_sample** to **.env**.
This file uses dotenv package to load environment variable to be used for the application.
You should put your API key in the file: <br />
**API_KEY=YOUR_API_KEY_HERE** <br />
<br />
API key came from [IEX](https://iexcloud.io/). You can get your API key by signing up on their website. <br /> 
IEX lets you download stock quotes via their API using URLs like <code>https<nolink>://cloud.iexapis.com/stable/stock/nflx/quote?token=YOUR_API_KEY</code>. Notice how Netflix’s symbol (NFLX) is embedded in this URL; that’s how IEX knows whose stock data to return. When the request is made, the response will be in JSON (JavaScript Object Notation) format.

