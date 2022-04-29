import pandas as pd
import numpy as np
from datetime import date
import os

from functions.get_min_safe_investment import get_min_safe_investment
from functions.import_content import import_content
from functions.read_csv import read_csv

month_weight = [
    0.6,   # 3  meses
    0.3,  # 6  meses
    0.1   # 12 meses
]

max_unit_price = 200

min_liquidez = 300
min_rentab = 0.9 * get_min_safe_investment() * 100

df = import_content(
    'https://www.fundsexplorer.com.br/ranking',
    encoding='utf-8'
)[0]

df = df.rename(columns={
    "Códigodo fundo": "Código",
    "PatrimônioLíq.": "PL"
})
df.sort_values('Código', inplace=True)

reclassified_fiis = read_csv('inputs/reclassification.csv')
for fii in reclassified_fiis:
    df.loc[df['Código'] == fii[0], ['Setor']] = [fii[1]]

reclassified_sectors = read_csv('inputs/reclassification_sectors.csv')
for i in range(1, len(reclassified_sectors)):
    df.loc[df['Setor'] == reclassified_sectors[i][0], ['Setor']] = [reclassified_sectors[i][1]]

categorical_columns = ['Código', 'Setor']
df['Setor'] = df['Setor'].fillna('Outros')
df[categorical_columns] = df[categorical_columns].astype('category')

float_columns = list(df.iloc[:, 2:-1].columns)
df[float_columns] = df[float_columns].fillna(0)
df = df.loc[df['Preço Atual'] != 0]

df[float_columns] = df[float_columns].applymap(lambda x: str(x).replace(
    'R$', '').replace('.0', '').replace('.', '').replace('%', '').replace(',', '.'))
df[float_columns] = df[float_columns].astype('float')

idx = df[np.isinf(df[float_columns]).any(1)].index
df.drop(idx, inplace=True)

df['P/VPA'] = df['P/VPA']/100
    
df['Expectativa'] = month_weight[0] * df['DY (3M)Média'] + month_weight[1] * df['DY (6M)Média'] + month_weight[2] * df['DY (12M)Média']

indicators = [
    'Código',
    'Setor',
    'Expectativa',
    'P/VPA',
    'Preço Atual',
    'VPA',
    'PL',
    'DY (3M)Média',
    'DY (6M)Média',
    'DY (12M)Média',
    'Liquidez Diária',
    'VacânciaFísica',
    'VacânciaFinanceira',
    'QuantidadeAtivos'
]
df_aux = df[indicators]

indicators = [
    'Setor',
    'Expectativa',
    'P/VPA',
    'DY (3M)Média',
    'DY (6M)Média',
    'DY (12M)Média',
    'Liquidez Diária',
    'VacânciaFísica',
    'VacânciaFinanceira',
    'QuantidadeAtivos'
]
media_setor = df_aux[indicators].groupby('Setor').agg(['mean','std'])

df_aux = df_aux.loc[(df_aux['Expectativa'] > min_rentab)]
df_aux = df_aux.loc[(df_aux['Preço Atual'] <= max_unit_price)]
df_aux = df_aux.loc[(df_aux['Liquidez Diária'] >= min_liquidez)]
sectors = list(df_aux['Setor'].unique())

print ('Gerando arquivo...')

t = date.today().strftime("%Y-%m-%d")
filename = 'outputs/fiis_analysis_'+t+'.xlsx'

if os.path.exists(filename):
    os.remove(filename)

with pd.ExcelWriter(filename) as writer:
    media_setor.to_excel(writer, sheet_name='GENERAL', encoding='utf8')
    for s in sectors:
        df_setor = df_aux[df_aux['Setor'].isin([s])].sort_values(by=['Expectativa', 'P/VPA'], ascending=False)
        if df_setor.size > 0:
            df_setor.to_excel(writer, sheet_name=s, encoding='utf8')

print ('Finalizado.')