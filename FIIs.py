import pandas as pd
from datetime import date
import os

from functions.get_min_safe_investment import get_min_safe_investment
from functions.read_csv import read_csv

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

month_weight = [
    0.5,   # 3  meses
    0.35,  # 6  meses
    0.15   # 12 meses
]

max_unit_price = 500
min_liquidez = 300
min_rentab = 0.8 * get_min_safe_investment() * 100

DRIVER_PATH = "C:\chromedriver.exe"

options = webdriver.ChromeOptions()
options.add_argument("headless")

browser = webdriver.Chrome(
    service=Service(executable_path=DRIVER_PATH),
    options=options
)

URL_MAIN_BASE = "https://www.fundsexplorer.com.br/ranking"
URL_COMP_BASE = "https://fiis.com.br/lupa-de-fiis/"


def get_base_from_url(url, browser):
    browser.get(url)
    res = browser.page_source
    df = pd.read_html(res)[0]
    return df


main_base = get_base_from_url(URL_MAIN_BASE, browser)
comp_base = get_base_from_url(URL_COMP_BASE, browser)
browser.close()


def format_float_val(v):
    if (str(v).endswith('.0')):
        v = str(v)[:-2]
    return str(v).replace(".", "").replace(",", "").replace("%", "").strip()


def create_suffix(el, suffix, duplicate=False):
    def format_suffix(v):
        if (str(v).endswith(suffix) and not duplicate):
            return str(v)
        return str(v) + suffix

    if (type(el) == "str"):
        return format_suffix(el)

    obj = {}
    for i in range(len(el)):
        obj[el[i]] = format_suffix(el[i])
    return obj


df = main_base.copy()

percent_cols = [
    "Dividend Yield",
    "DY (3M) Acumulado",
    "DY (6M) Acumulado",
    "DY (12M) Acumulado",
    "DY (3M) média",
    "DY (6M) média",
    "DY (12M) média",
    "DY Ano",
    "Variação Preço",
    "Rentab. Período",
    "Rentab. Acumulada",
    "DY Patrimonial",
    "Variação Patrimonial",
    "Rentab. Patr. Período",
    "Rentab. Patr. Acumulada"
]

float_cols = [
    "Liquidez Diária (R$)",
    "Patrimônio Líquido",
    "Preço Atual (R$)",
    "P/VP",
    "P/VPA",
    "Último Dividendo",
    "VPA"
] + percent_cols

for col in float_cols:
    df[col] = df[col].apply(lambda v: format_float_val(v))
    df[col] = df[col].astype("float64") / 100
    # df[col] = df[col].astype("float64") / (10000 if col in percent_cols else 100)

percent_cols_names = create_suffix(percent_cols, " (%)")
df = df.rename(columns=percent_cols_names)

main_df = df.copy()

df = comp_base.copy()

percent_cols = [
    "Último Rend. (%)",
    "Rend. Méd. 12m (%)",
    "Partic. IFIX",
]

for col in percent_cols:
    df[col] = df[col].astype("float64") / 100

float_cols = [
    "Partic. IFIX",
    "Último Rend. (R$)",
    "Rend. Méd. 12m (R$)",
    "Patrimônio/Cota",
    "Cotação/VP",
    "Patrimônio",
    "Cota base",
]

for col in float_cols:
    df[col] = df[col].apply(lambda v: format_float_val(v))
    df[col] = df[col].astype("float64") / 100

df["Número Cotistas"] = df["Número Cotistas"] * 1000

percent_cols_names = create_suffix(percent_cols, " (%)")
df = df.rename(columns=percent_cols_names)

comp_df = df.copy()

df = pd.merge(
    left=main_df,
    right=comp_df,
    left_on="Fundos",
    right_on="Ticker"
)

duplicated_columns = [
    "Último Rend. (R$)",
    "Dividend Yield (%)",
    "Patrimônio",
    "Fundos",
    "Rend. Méd. 12m (%)",
    "Cotação/VP"
]

for col in duplicated_columns:
    del df[col]

reclass_sectors = read_csv('inputs/reclassification_sectors.csv')
subsectors = read_csv('inputs/subsectors.csv')
reclass_fiis = read_csv('inputs/reclassification_fiis.csv')

class_fiss = {}
for i in range(1, len(reclass_fiis)):
    class_fiss[reclass_fiis[i][0]] = {
        'sector': reclass_fiis[i][1],
        'subsector': reclass_fiis[i][2]
    }

types_strategy_obj = {}
for i in range(1, len(reclass_sectors)):
    types_strategy_obj[reclass_sectors[i][0]] = reclass_sectors[i][1]

subsectors_obj = {}
for i in range(1, len(subsectors)):
    subsectors_obj[subsectors[i][0]] = subsectors[i][1]

df = df.rename(columns={
    'Setor': 'Setor_previous'
})


def get_sector(row):
    if (row["Ticker"] in class_fiss):
        sector = class_fiss[row["Ticker"]]['sector']
        subsector = class_fiss[row["Ticker"]]['subsector']
    else:
        subsector = row["Setor_previous"]

        if (pd.isnull(row["Tipo de Fii"])):
            sector = subsectors_obj[subsector]
            if (not sector):
                sector = "Indefinido"
        else:
            aux = str(row["Tipo de Fii"]).split(":")
            if (aux[1]):
                subsector = aux[1]
            sector = aux[0]

    type_str = (types_strategy_obj[subsector] if (
        subsector in types_strategy_obj) else subsector)

    return [sector, subsector, type_str]


df[["Setor", "Subsetor", "Tipo Estratégia"]] = df.apply(
    get_sector, result_type='expand', axis="columns")

del df["Setor_previous"]
del df["Tipo de Fii"]

category_cols = [
    "Setor",
    "Subsetor",
    "Tipo Estratégia",
    "Público Alvo"
]

for cat in category_cols:
    df[cat] = df[cat].astype("category")


df = df[~df["Preço Atual (R$)"].isna()]
df = df[~df["P/VP"].isna()]


def calc_expect(row):
    expect = month_weight[0] * row['DY (3M) média (%)'] + month_weight[1] * \
        row['DY (6M) média (%)'] + month_weight[2] * row['DY (12M) média (%)']
    return [
        expect,
        expect / row["P/VP"]
    ]


df[["Expect", "Expect P/VP"]] = df.apply(
    calc_expect, result_type='expand', axis="columns")

df = df[df['Expect P/VP'] > min_rentab]
df = df[df['P/VP'].between(0.7, 1.15)]
df = df[df["Preço Atual (R$)"] <= max_unit_price]
df = df[df["Liquidez Diária (R$)"] >= min_liquidez]

cols_order = [
    'Ticker',
    'Tipo Estratégia',
    'Setor',
    'Subsetor',
    'Preço Atual (R$)',
    'P/VP',
    "Expect",
    "Expect P/VP",
    'VPA',
    'P/VPA',
    'DY (3M) Acumulado (%)',
    'DY (6M) Acumulado (%)',
    'DY (12M) Acumulado (%)',
    'DY (3M) média (%)',
    'DY (6M) média (%)',
    'DY (12M) média (%)',
    'DY Ano (%)',
    'Variação Preço (%)',
    'Rentab. Período (%)',
    'Rentab. Acumulada (%)',
    'DY Patrimonial (%)',
    'Variação Patrimonial (%)',
    'Rentab. Patr. Período (%)',
    'Rentab. Patr. Acumulada (%)',
    'Último Dividendo',
    'Último Rend. (%)',
    'Cota base',
    'Rend. Méd. 12m (R$)',
    'Data Base',
    'Data Pagamento',
    'Vacância Física',
    'Vacância Financeira',
    'Quant. Ativos',
    'Liquidez Diária (R$)',
    'Público Alvo',
    'Administrador',
    'Partic. IFIX (%)',
    'N° negócios/mês',
    'Número Cotistas',
    'Patrimônio Líquido',
    'Patrimônio/Cota'
]

indicators = [
    'Tipo Estratégia',
    'Último Rend. (%)',
    'DY (12M) média (%)',
    'DY (3M) média (%)',
    'DY (6M) média (%)',
    'Expect',
    'Expect P/VP',
    'Liquidez Diária (R$)',
    'P/VP',
    'Variação Preço (%)',
]

not_interesting_sectors = [
    'Educação',
    'Ag Bancárias',
    'Shoppings',
    'Hotéis',
    'Hospitais'
]

sectors = list(df['Tipo Estratégia'].unique())
for s in not_interesting_sectors:
    sectors.remove(s)
sector_aggs = df[indicators].groupby('Tipo Estratégia').agg(['mean', 'std'])

print('Gerando arquivo...')

t = date.today().strftime("%Y-%m-%d")
filename = 'outputs/fiis_analysis_'+t+'.xlsx'

if os.path.exists(filename):
    os.remove(filename)

with pd.ExcelWriter(filename) as writer:
    sector_aggs.to_excel(writer, sheet_name='GENERAL')
    for s in sectors:
        df_sector = pd.DataFrame(df[df["Tipo Estratégia"] == s].sort_values(
            by=['Expect P/VP', 'P/VP'], ascending=False))
        if len(df_sector) > 0:
            df_sector[cols_order].to_excel(writer, sheet_name=s)

print('Finalizado.')
