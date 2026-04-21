# 📊 Commodity Price Direction Dashboard

An interactive Streamlit dashboard for analysing commodity price movements using **historical data, news sentiment, and machine learning predictions**.


## 🚀 Overview

This dashboard combines:

- 📈 Historical price data  
- 📰 News sentiment signals  
- 🤖 Machine learning predictions  

to provide a unified view of:
- Market trends  
- Sentiment impact  
- Next-day price direction  


## 🧠 What It Does

The system:

1. Loads commodity-specific price data  
2. Filters sentiment data by matching topic  
3. Generates features (technical + sentiment)  
4. Predicts next-day price direction using a trained model  


## ⚙️ Features

### 📌 Commodity Selection
- Brent (Oil)
- Natural Gas
- Silver

Each selection dynamically updates:
- Price data  
- Sentiment signals  


### 📈 Price Analysis
- Displays historical price trends  
- Helps identify:
  - Trends  
  - Volatility  
  - Turning points  


### 📰 Sentiment Analysis
Daily aggregated sentiment includes:
- Average sentiment score  
- News volume  
- Sentiment variability  

All sentiment is **aligned to the selected commodity**.


### 🤖 Prediction Module
- Predicts **next-day direction**:
  - ⬆️ UP  
  - ⬇️ DOWN  

Based on:
- Price features  
- Technical indicators  
- Sentiment signals  


## 🖥️ How to Use

### 1. Select Commodity
Choose from:
- Brent  
- Natural Gas  
- Silver  


### 2. Navigate Dates
Use controls to:
- Move by **day or week**  
- Focus on specific periods  


### 3. Analyse Trends
Observe:
- Price movement  
- Sentiment patterns  


### 4. View Prediction
Check:
- Predicted direction  
- Model output  


## 📊 Interpreting Results

### Price vs Sentiment

| Scenario | Interpretation |
|--------|----------------|
| Positive sentiment + rising price | Bullish signal |
| Negative sentiment + falling price | Bearish signal |
| Mixed signals | Uncertainty |

---

### News Volume
- High → stronger signal  
- Low → weaker reliability  

---

### Prediction Output
- **UP** → expected price increase  
- **DOWN** → expected price decrease  



## ⚠️ Limitations

- Model performance depends on training data  
- Predictions may not generalize across all commodities  
- Sentiment may lag real-world events  
- This is **not financial advice**



## 🏗️ Project Structure
```
streamlit/
│
├── app.py # Main dashboard
├── config.py # Feature + mapping configs
├── loaders.py # Data loading functions
├── requirements.txt # Necessary libraries
├── tabs/ # (Optional) modular UI tabs
│
data/
├── brent_daily.csv
├── natural_gas_daily.csv
├── silver_daily.csv
├── daily_topic_sentiment.csv
│
models/
├── xgb_model.pkl
├── scaler.pkl
```
Run `streamlit run streamlit/app.py` from root folder in terminal.

## 🔮 Future Improvements

- Multi-model support per commodity  
- Real-time data integration  
- More advanced NLP sentiment models (e.g., DeBERTa)  
- Confidence scores and explainability  


## 📌 Summary

This dashboard enables:

- Exploration of **price + sentiment relationships**  
- Understanding of **market behaviour**  
- Generation of **data-driven predictions**  
