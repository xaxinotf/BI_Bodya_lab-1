import pandas as pd

# Читаємо CSV, вимикаємо "low_memory", щоб уникнути DtypeWarning
df_trans = pd.read_csv('trans.csv', sep=';', low_memory=False)

# Перетворюємо колонку 'date' на рядки (щоб гарантовано не було змішаних типів)
df_trans['date'] = df_trans['date'].astype(str)

# Конвертуємо YYMMDD у формат дати
df_trans['date'] = pd.to_datetime(
    df_trans['date'],
    format='%y%m%d',   # двозначний рік, місяць, день
    errors='coerce'    # некоректні значення стануть NaT, щоб уникнути помилок
)

print(df_trans[['date']].head())
