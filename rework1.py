# rework1.py
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from dash import Dash, dcc, html, Input, Output, dash_table
import dash_cytoscape as cyto

# Ініціалізація Dash-додатку
app = Dash(__name__)
app.title = "Czech Bank Financial Dashboard"


# Функція для завантаження та виведення назв колонок
def load_and_print_columns(file_path, df_name):
    try:
        df = pd.read_csv(file_path, sep=';', low_memory=False)
        print(f"Назви колонок у {df_name}:")
        print(df.columns.tolist())
        print(f"Кількість рядків у {df_name}: {len(df)}\n")
        return df
    except Exception as e:
        print(f"Помилка при завантаженні {file_path}: {e}")
        return pd.DataFrame()


# Завантаження DataFrame та вивід колонок
df_account = load_and_print_columns('account.csv', 'df_account')
df_trans = load_and_print_columns('trans.csv', 'df_trans')
df_order = load_and_print_columns('order.csv', 'df_order')
df_district = load_and_print_columns('district.csv', 'df_district')
df_disp = load_and_print_columns('disp.csv', 'df_disp')
df_loan = load_and_print_columns('loan.csv', 'df_loan')
df_card = load_and_print_columns('card.csv', 'df_card')
df_client = load_and_print_columns('client.csv', 'df_client')


# 1. Перевірка наявності необхідних колонок
def check_columns(df, required_columns, df_name):
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        print(f"У DataFrame '{df_name}' відсутні колонки: {missing}")
    else:
        print(f"У DataFrame '{df_name}' всі необхідні колонки присутні.")


# Визначте необхідні колонки для кожного DataFrame
check_columns(df_client, ['client_id', 'birth_number', 'district_id'], 'df_client')
check_columns(df_trans, ['trans_id', 'date', 'account_id', 'amount', 'balance'], 'df_trans')
check_columns(df_district, ['district_id', 'region', 'district_name'], 'df_district')
check_columns(df_disp, ['account_id', 'client_id', 'type'], 'df_disp')
check_columns(df_account, ['account_id', 'date', 'frequency'], 'df_account')

# 2. Перегляд Перших Рядків df_district для Визначення Вмісту
print("Перші 5 рядків df_district:")
print(df_district.head())

# 3. Переіменування Колонок у df_district, якщо можливо
alternative_columns = {}
if 'A1' in df_district.columns:
    alternative_columns['A1'] = 'district_id'
if 'A2' in df_district.columns:
    alternative_columns['A2'] = 'region'
if 'A3' in df_district.columns:
    alternative_columns['A3'] = 'district_name'

if alternative_columns:
    df_district = df_district.rename(columns=alternative_columns)
    print("Колонки df_district успішно переіменовано.")
else:
    print("Не знайдено відповідних колонок для переіменування.")

# Перевірка наявності колонок після переіменування
check_columns(df_district, ['district_id', 'region', 'district_name'], 'df_district')

# 4. Підготовка dim_date
if 'date' in df_trans.columns:
    # Перетворюємо колонку 'date' на рядки (щоб уникнути змішаних типів)
    df_trans['date'] = df_trans['date'].astype(str).str.zfill(6)  # Доповнюємо нулями до 6 символів
    # Конвертуємо YYMMDD у формат дати
    df_trans['date'] = pd.to_datetime(
        df_trans['date'],
        format='%y%m%d',
        errors='coerce'  # Некоректні значення стануть NaT
    )
    # Створимо date_id як YYYYMMDD (Int64)
    df_trans['date_id'] = df_trans['date'].dt.strftime('%Y%m%d').astype('Int64')
    print("Дата успішно конвертована у df_trans.")
else:
    print("У df_trans відсутня колонка 'date'. Перевірте назви колонок.")
    df_trans['date_id'] = np.nan  # Заповнюємо NaN, якщо колонки немає

# Створюємо dim_date
dim_date = df_trans[['date_id', 'date']].drop_duplicates().dropna(subset=['date_id'])
dim_date['year'] = dim_date['date'].dt.year
dim_date['quarter'] = dim_date['date'].dt.quarter
dim_date['month'] = dim_date['date'].dt.month
dim_date['day'] = dim_date['date'].dt.day

print(f"dim_date має {len(dim_date)} рядків.")

# 5. Підготовка dim_client
required_client_columns = ['client_id', 'birth_number', 'district_id']
available_client_columns = [col for col in required_client_columns if col in df_client.columns]
dim_client = df_client[available_client_columns].drop_duplicates()

print(f"dim_client має {len(dim_client)} рядків.")

# 6. Підготовка dim_district
required_district_columns = ['district_id', 'region', 'district_name']
available_district_columns = [col for col in required_district_columns if col in df_district.columns]

if available_district_columns:
    dim_district = df_district[available_district_columns].drop_duplicates()
    print(f"dim_district має {len(dim_district)} рядків.")
else:
    print("У df_district відсутні всі необхідні колонки. Спробуємо знайти альтернативні назви.")
    alternative_columns = {}
    if 'district_id' not in df_district.columns and 'districtID' in df_district.columns:
        alternative_columns['districtID'] = 'district_id'
    if 'region' not in df_district.columns and 'RegionName' in df_district.columns:
        alternative_columns['RegionName'] = 'region'
    if 'district_name' not in df_district.columns and 'DistrictName' in df_district.columns:
        alternative_columns['DistrictName'] = 'district_name'

    if alternative_columns:
        df_district_renamed = df_district.rename(columns=alternative_columns)
        # Перевіряємо, чи всі необхідні колонки присутні після переіменування
        if all(col in df_district_renamed.columns for col in ['district_id', 'region', 'district_name']):
            dim_district = df_district_renamed[['district_id', 'region', 'district_name']].drop_duplicates()
            print(f"dim_district (з альтернативними назвами) має {len(dim_district)} рядків.")
        else:
            print("Не вдалося знайти всі необхідні колонки навіть після переіменування.")
            dim_district = pd.DataFrame()
    else:
        print("Не знайдено альтернативних назв колонок для dim_district.")
        dim_district = pd.DataFrame()

# 7. Підготовка dim_account
if 'date' in df_account.columns:
    # Перейменуємо колонку 'date' у 'date_created'
    df_account = df_account.rename(columns={'date': 'date_created'})
    # Доповнюємо нулями до 6 символів, якщо необхідно
    df_account['date_created'] = df_account['date_created'].astype(str).str.zfill(6)
    # Конвертуємо 'date_created' з формату 'YYMMDD' у datetime
    df_account['date_created'] = pd.to_datetime(
        df_account['date_created'],
        format='%y%m%d',
        errors='coerce'
    )
    print("Дата успішно конвертована у df_account.")
else:
    print("У df_account відсутня колонка 'date'. Перевірте назви колонок.")
    df_account['date_created'] = pd.NaT  # Заповнюємо NaT, якщо колонки немає

# Вибираємо наявні колонки
required_account_columns = ['account_id', 'date_created', 'frequency']
available_account_columns = [col for col in required_account_columns if col in df_account.columns]
dim_account = df_account[available_account_columns].drop_duplicates()

print(f"dim_account має {len(dim_account)} рядків.")

# 8. Створення Fact Table (fact_trans)
# Перейменування колонок, якщо необхідно
rename_trans_columns = {}
if 'amount' in df_trans.columns:
    rename_trans_columns['amount'] = 'trans_amount'
if 'balance' in df_trans.columns:
    rename_trans_columns['balance'] = 'balance_after_trans'

df_trans = df_trans.rename(columns=rename_trans_columns)

# З'єднуємо df_trans з df_disp, щоб отримати 'client_id' через 'account_id'
required_disp_columns = ['account_id', 'client_id', 'type']
if all(col in df_disp.columns for col in required_disp_columns):
    # Фільтруємо тільки власників рахунків
    df_disp_owners = df_disp[df_disp['type'] == 'OWNER']
    # З'єднуємо df_trans з df_disp_owners по 'account_id'
    fact_trans = pd.merge(df_trans, df_disp_owners[['account_id', 'client_id']], on='account_id', how='left')
    print("З'єднання df_trans з df_disp успішне.")
else:
    print("У df_disp відсутні необхідні колонки для з'єднання. Створюємо fact_trans без 'client_id'.")
    fact_trans = df_trans.copy()

# Приєднуємо 'district_id' з dim_client
if 'client_id' in fact_trans.columns and 'district_id' in dim_client.columns:
    fact_trans = pd.merge(fact_trans, dim_client[['client_id', 'district_id']], on='client_id', how='left')
    print("Приєднання 'district_id' з dim_client успішне.")
else:
    print("Неможливо приєднати 'district_id' з dim_client. Перевірте наявність колонок.")
    fact_trans['district_id'] = np.nan  # Заповнюємо NaN, якщо неможливо приєднати

# Вибираємо необхідні колонки для fact_trans
required_fact_columns = ['trans_id', 'date_id', 'client_id', 'district_id', 'account_id', 'trans_amount',
                         'balance_after_trans']
available_fact_columns = [col for col in required_fact_columns if col in fact_trans.columns]
fact_trans = fact_trans[available_fact_columns]

print(f"fact_trans має {len(fact_trans)} рядків та колонки: {fact_trans.columns.tolist()}")

# 9. Об'єднання Fact Table з Dimensions
fact_dims = fact_trans.copy()

# Приєднуємо 'year' з dim_date
if 'date_id' in fact_dims.columns and 'year' in dim_date.columns:
    fact_dims = pd.merge(fact_dims, dim_date[['date_id', 'year']], on='date_id', how='left')
    print("Приєднано 'year' з dim_date.")
else:
    print("Неможливо приєднати 'year' з dim_date.")

# Приєднуємо 'region' з dim_district, якщо dim_district не порожній
if not dim_district.empty and 'district_id' in fact_dims.columns and 'region' in dim_district.columns:
    fact_dims = pd.merge(fact_dims, dim_district[['district_id', 'region', 'district_name']], on='district_id',
                         how='left')
    print("Приєднано 'region' з dim_district.")
else:
    print("Неможливо приєднати 'region' з dim_district. Перевірте наявність колонок та даних.")

# 10. Створення Pivot Table
if all(col in fact_dims.columns for col in ['trans_amount', 'region', 'year']):
    pivot_table = fact_dims.pivot_table(
        values='trans_amount',
        index='region',
        columns='year',
        aggfunc='sum',
        fill_value=0
    )
    print("\nПриклад Pivot Table (Сума транзакцій за регіонами та роками):")
    print(pivot_table.head())
else:
    print("Неможливо створити Pivot Table. Перевірте наявність колонок 'trans_amount', 'region', 'year'.")

# 11. Підготовка Даних для Візуалізації
if 'year' in fact_dims.columns and 'trans_amount' in fact_dims.columns:
    df_plot_year = fact_dims.groupby(['year'])['trans_amount'].sum().reset_index()
else:
    df_plot_year = pd.DataFrame()
    print("Неможливо створити дані для графіка суми транзакцій по роках.")

if 'region' in fact_dims.columns and 'trans_amount' in fact_dims.columns:
    df_plot_region = fact_dims.groupby(['region'])['trans_amount'].sum().reset_index()
else:
    df_plot_region = pd.DataFrame()
    print("Неможливо створити дані для графіка суми транзакцій за регіонами.")

# 12. Визначення Структури Зіркової Схеми за Допомогою Dash Cytoscape
# Визначення вузлів (nodes) та ребер (edges)
nodes = [
    # Fact Table
    {'data': {'id': 'fact_trans', 'label': 'Fact Transactions'}, 'classes': 'fact'},

    # Dimension Tables
    {'data': {'id': 'dim_date', 'label': 'Dimension Date'}, 'classes': 'dimension'},
    {'data': {'id': 'dim_client', 'label': 'Dimension Client'}, 'classes': 'dimension'},
    {'data': {'id': 'dim_district', 'label': 'Dimension District'}, 'classes': 'dimension'},
    {'data': {'id': 'dim_account', 'label': 'Dimension Account'}, 'classes': 'dimension'}
]

edges = [
    {'data': {'source': 'fact_trans', 'target': 'dim_date'}},
    {'data': {'source': 'fact_trans', 'target': 'dim_client'}},
    {'data': {'source': 'fact_trans', 'target': 'dim_district'}},
    {'data': {'source': 'fact_trans', 'target': 'dim_account'}}
]

elements = nodes + edges

# Стилізація графу
stylesheet = [
    {
        'selector': 'node',
        'style': {
            'label': 'data(label)',
            'text-valign': 'center',
            'color': 'white',
            'text-outline-width': 2,
            'text-outline-color': '#888',
            'font-size': '12px'
        }
    },
    {
        'selector': 'node.fact',
        'style': {
            'background-color': '#FF4136',
            'shape': 'ellipse',
            'width': '60px',
            'height': '60px'
        }
    },
    {
        'selector': 'node.dimension',
        'style': {
            'background-color': '#0074D9',
            'shape': 'roundrectangle',
            'width': '50px',
            'height': '50px'
        }
    },
    {
        'selector': 'edge',
        'style': {
            'width': 2,
            'line-color': '#ccc',
            'target-arrow-color': '#ccc',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
        }
    }
]

# 13. Визначення Layout Dash-додатку
app.layout = html.Div([
    html.H1("Czech Bank Financial Dashboard", style={'textAlign': 'center'}),

    # Таблиця зіркової схеми (генерована за допомогою Dash Cytoscape)
    html.H2("Star Schema Structure"),
    html.Div([
        cyto.Cytoscape(
            id='star-schema',
            elements=elements,
            stylesheet=stylesheet,
            layout={'name': 'circle'},
            # Можна змінити на інший макет, наприклад, 'breadthfirst', 'cose', 'grid', 'circle', etc.
            style={'width': '100%', 'height': '400px'}
        )
    ]),

    html.Hr(),

    # Інтерактивна таблиця Pivot Table
    html.H2("Pivot Table: Сума транзакцій за регіонами та роками"),
    dash_table.DataTable(
        id='pivot-table',
        columns=[
            {"name": str(i) if not pd.isna(i) else "Undefined", "id": str(i) if not pd.isna(i) else "Undefined"}
            for i in pivot_table.reset_index().columns
        ] if 'pivot_table' in locals() else [],
        data=pivot_table.reset_index().to_dict('records') if 'pivot_table' in locals() else [],
        style_table={'overflowX': 'auto'},
        style_cell={
            'minWidth': '100px', 'width': '150px', 'maxWidth': '180px',
            'whiteSpace': 'normal',
            'textAlign': 'center'
        },
        page_size=20
    ),

    html.Hr(),

    # Графік суми транзакцій по роках
    html.H2("Сума транзакцій по роках"),
    dcc.Graph(
        id='bar-chart-year',
        figure=px.bar(
            df_plot_year,
            x='year',
            y='trans_amount',
            title='Сума транзакцій по роках',
            labels={'year': 'Рік', 'trans_amount': 'Сума транзакцій'},
            template='plotly_white'
        ) if not df_plot_year.empty else {}
    ),

    html.Hr(),

    # Графік суми транзакцій за регіонами
    html.H2("Сума транзакцій за регіонами"),
    dcc.Graph(
        id='bar-chart-region',
        figure=px.bar(
            df_plot_region,
            x='region',
            y='trans_amount',
            title='Сума транзакцій за регіонами',
            labels={'region': 'Регіон', 'trans_amount': 'Сума транзакцій'},
            template='plotly_white'
        ) if not df_plot_region.empty else {}
    ),

    html.Hr(),

    # Інтерактивні фільтри (опційно)
    html.H2("Фільтри"),
    html.Div([
        html.Label("Виберіть рік:"),
        dcc.Dropdown(
            id='year-dropdown',
            options=[{'label': year, 'value': year} for year in sorted(df_plot_year['year'].dropna().unique())],
            value=sorted(df_plot_year['year'].dropna().unique())[0] if not df_plot_year.empty else None
        )
    ], style={'width': '200px', 'display': 'inline-block', 'padding': '10px'}),

    html.Div([
        html.Label("Виберіть регіон:"),
        dcc.Dropdown(
            id='region-dropdown',
            options=[{'label': region, 'value': region} for region in
                     sorted(df_plot_region['region'].dropna().unique())],
            value=sorted(df_plot_region['region'].dropna().unique())[0] if not df_plot_region.empty else None
        )
    ], style={'width': '200px', 'display': 'inline-block', 'padding': '10px'}),

    # Графік з фільтрацією
    html.H2("Сума транзакцій по роках з фільтрацією"),
    dcc.Graph(id='filtered-bar-chart-year'),

    html.H2("Сума транзакцій за регіонами з фільтрацією"),
    dcc.Graph(id='filtered-bar-chart-region'),

    html.Hr(),

    # Відображення метаданих
    html.H2("Метадані"),
    html.Div([
        html.H4("Dimension Tables:"),
        html.Ul([
            html.Li("dim_date: date_id, date, year, quarter, month, day"),
            html.Li("dim_client: client_id, birth_number, district_id"),
            html.Li("dim_district: district_id, region, district_name"),
            html.Li("dim_account: account_id, date_created, frequency")
        ]),
        html.H4("Fact Table:"),
        html.Ul([
            html.Li("trans_id"),
            html.Li("date_id"),
            html.Li("client_id"),
            html.Li("district_id"),
            html.Li("account_id"),
            html.Li("trans_amount"),
            html.Li("balance_after_trans")
        ])
    ], style={'padding': '20px'})
])


# 13. Callback для Фільтрації Графіків
@app.callback(
    [Output('filtered-bar-chart-year', 'figure'),
     Output('filtered-bar-chart-region', 'figure')],
    [Input('year-dropdown', 'value'),
     Input('region-dropdown', 'value')]
)
def update_filtered_charts(selected_year, selected_region):
    # Фільтрування даних
    if not df_plot_year.empty:
        if selected_year:
            filtered_year = df_plot_year[df_plot_year['year'] == selected_year]
        else:
            filtered_year = df_plot_year
    else:
        filtered_year = pd.DataFrame()

    if not df_plot_region.empty:
        if selected_region:
            filtered_region = df_plot_region[df_plot_region['region'] == selected_region]
        else:
            filtered_region = df_plot_region
    else:
        filtered_region = pd.DataFrame()

    # Створення графіків
    if not filtered_year.empty:
        fig_year = px.bar(
            filtered_year,
            x='year',
            y='trans_amount',
            title=f'Сума транзакцій у {selected_year} році' if selected_year else 'Сума транзакцій по роках',
            labels={'year': 'Рік', 'trans_amount': 'Сума транзакцій'},
            template='plotly_white'
        )
    else:
        fig_year = go.Figure()
        fig_year.update_layout(title='Немає даних для відображення')

    if not filtered_region.empty:
        fig_region = px.bar(
            filtered_region,
            x='region',
            y='trans_amount',
            title=f'Сума транзакцій у регіоні: {selected_region}' if selected_region else 'Сума транзакцій за регіонами',
            labels={'region': 'Регіон', 'trans_amount': 'Сума транзакцій'},
            template='plotly_white'
        )
    else:
        fig_region = go.Figure()
        fig_region.update_layout(title='Немає даних для відображення')

    return fig_year, fig_region


# Запуск Dash-додатку
if __name__ == '__main__':
    app.run_server(debug=True, port=8050)
