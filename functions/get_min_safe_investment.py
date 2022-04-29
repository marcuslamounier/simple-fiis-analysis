from urllib.request import urlopen
import json

from functions.read_csv import read_csv

def get_selic():
  url = "https://www.bcb.gov.br/api/servico/sitebcb/historicotaxasjuros"
  response = urlopen(url)
  data_json = json.loads(response.read())
  return data_json['conteudo'][0]['MetaSelic']

def get_market_params():
  selic = get_selic()

  input_params = read_csv('inputs/market_params.csv')
  best_liquid_rate = float(input_params[1][1])
  income_tax_rate = float(input_params[2][1])

  return {
    'selic': selic,
    'offer': best_liquid_rate,
    'tax': income_tax_rate
  }

def get_min_safe_investment():
  market_params = get_market_params()
  selic = market_params['selic']
  best_liquid_rate = market_params['offer']
  income_tax_rate = market_params['tax']

  cdi = selic - 0.1
  print('Taxa básica (SELIC):', selic, '%')
  print('CDI puro:', cdi, '%')
  print('Alíquota de IR:', income_tax_rate * 100, '%\n')

  benchmark_year = (best_liquid_rate * cdi) * (1 - income_tax_rate)
  benchmark_month = pow(1 + benchmark_year / 100, 1/12) - 1

  print('Melhor oferta com baixa liquidez:', best_liquid_rate * 100, '%', 'do CDI')
  print(round(benchmark_year, 5), '%', 'a.a.; ou')
  print(round(benchmark_month * 100, 5), '%', 'a.m.\n')

  return benchmark_month