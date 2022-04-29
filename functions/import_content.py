import requests
import pandas as pd

headers = {
    'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    ' (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36'
}

def import_content(url, **kwargs):
  response = requests.get(url, headers=headers)

  if response.status_code == 200:
    if 'encoding' in kwargs.keys():
      df = pd.read_html(response.content, encoding=kwargs['encoding'])
    else:
      df = pd.read_html(response.content)
    return df
  else:
    return list(pd.DataFrame([]))