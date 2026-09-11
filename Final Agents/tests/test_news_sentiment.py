import pytest
from unittest.mock import patch
from src.agents.news_sentiment import news_sentiment_agent

@patch('src.agents.news_sentiment.get_company_news')
@patch('src.agents.news_sentiment.call_llm')
@patch('src.agents.news_sentiment.get_api_key_from_state')
def test_news_sentiment_agent_empty_news(mock_get_api_key, mock_call_llm, mock_get_company_news):
    # Setup mocks
    mock_get_company_news.return_value = []
    mock_get_api_key.return_value = 'dummy_key'
    
    # Setup state
    state = {
        'data': {
            'tickers': ['NVDA'],
            'end_date': '2024-03-24',
            'analyst_signals': {}
        },
        'metadata': {
            'show_reasoning': False
        }
    }
    
    # Run agent
    result = news_sentiment_agent(state)
    
    # Assert it returns successfully
    assert result is not None
    assert 'messages' in result
    assert 'data' in result
    assert 'analyst_signals' in result['data']
    assert 'news_sentiment_agent' in result['data']['analyst_signals']

    # The analysis should report neutral due to 0 articles
    analysis = result['data']['analyst_signals']['news_sentiment_agent']['NVDA']
    assert analysis['signal'] == 'neutral'
    assert analysis['confidence'] == 12
