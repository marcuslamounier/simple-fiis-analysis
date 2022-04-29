import csv

def read_csv(path):
  file = open(path, encoding='utf-8')
  type(file)

  rows = []
  for row in csv.reader(file):
    rows.append(row)
  file.close()

  return rows