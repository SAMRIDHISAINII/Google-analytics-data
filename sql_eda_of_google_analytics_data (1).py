# -*- coding: utf-8 -*-
"""sql-eda-of-google-analytics-data.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1WdGYAPT1f7u8zPnXiTPRb0oreRkOPhe4
"""

# Commented out IPython magic to ensure Python compatibility.
# Import necessary libraries
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
sns.set()

from plotly.offline import init_notebook_mode, iplot
init_notebook_mode(connected=True)
import plotly.graph_objs as go
import plotly.express as px

# %matplotlib inline

from google.cloud import bigquery

# Create client object
client = bigquery.Client()

# Create dataset reference
dataset_ref = client.dataset('google_analytics_sample', project='bigquery-public-data')

# Retrieve dataset from reference
dataset = client.get_dataset(dataset_ref)

# View tables in dataset
[x.table_id for x in client.list_tables(dataset)][:5]

# Create table reference
table_ref_20160801 = dataset_ref.table('ga_sessions_20160801')

# Retrieve table from reference
table_20160801 = client.get_table(table_ref_20160801)

# View columns
client.list_rows(table_20160801, max_results=5).to_dataframe()

"""It looks like the totals, trafficSource, device, geoNetwork, customDimensions, and hits columns contain nested data.

Let's check the schema for these columns and see what kind of data they contain.
"""

def format_schema_field(schema_field, indent=0):
    indent_str = "  " * indent
    field_info = f"{indent_str}{schema_field.name} ({schema_field.field_type})"

    if schema_field.mode != "NULLABLE":
        field_info += f" - {schema_field.mode}"

    if schema_field.description:
        field_info += f" - {schema_field.description}"

    nested_indent = indent + 2
    if schema_field.field_type == "RECORD":
        for sub_field in schema_field.fields:
            field_info += "\n" + format_schema_field(sub_field, nested_indent)

    return field_info

# Display schemas
print("SCHEMA field for the 'totals' column:\n")
print(format_schema_field(table_20160801.schema[5]))
print()

print("\nSCHEMA field for the 'trafficSource' column:\n")
print(format_schema_field(table_20160801.schema[6]))
print()

print("\nSCHEMA field for the 'device' column:\n")
print(format_schema_field(table_20160801.schema[7]))
print()

print("\nSCHEMA field for the 'geoNetwork' column:\n")
print(format_schema_field(table_20160801.schema[8]))
print()

print("\nSCHEMA field for the 'customDimensions' column:\n")
print(format_schema_field(table_20160801.schema[9]))
print()

print("\nSCHEMA field for the 'hits' column:\n")
print(format_schema_field(table_20160801.schema[10]))

# 「ｈitＮumber=1」Indicates the first hit of a session
query = """
        SELECT
            hits.page.pagePath AS landing_page,
            COUNT(*) AS views,
            SUM(totals.bounces)/COUNT(*) AS bounce_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            hits.type='PAGE'
        AND
            hits.hitNumber=1
        GROUP BY
            landing_page
        ORDER BY
            views DESC
        LIMIT 10
        """

result = client.query(query).result().to_dataframe()
result.head(10)

query = """
        SELECT
            hits.page.pagePath AS page,
            COUNT(*) AS views,
            SUM(totals.bounces)/COUNT(*) AS exit_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            hits.type='PAGE'
        GROUP BY
            page
        ORDER BY
            views DESC
        LIMIT 10
        """

result = client.query(query).result().to_dataframe()
result.head(10)

query = """
        SELECT
            device.Browser AS browser,
            COUNT(*) AS sessions,
            SUM(totals.bounces)/COUNT(*) AS exit_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        GROUP BY
            browser
        ORDER BY
            sessions DESC
        LIMIT 10
        """

result = client.query(query).result().to_dataframe()
result.head(10)

query = """
        SELECT
            device.deviceCategory AS device,
            COUNT(*) AS sessions,
            SUM(totals.bounces)/COUNT(*) AS exit_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        GROUP BY
            device
        ORDER BY
            sessions DESC
        """

result = client.query(query).result().to_dataframe()
result.head(10)

query = """
        SELECT
            trafficSource.medium AS medium,
            COUNT(*) AS sessions,
            SUM(totals.bounces)/COUNT(*) AS exit_rate,
            SUM(totals.transactions) AS transactions,
            SUM(totals.totalTransactionRevenue)/1000000 AS total_revenue,
            SUM(totals.transactions)/COUNT(*) AS conversion_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        GROUP BY
            medium
        ORDER BY
            sessions DESC
        """

result = client.query(query).result().to_dataframe()
result.head(10)

# Aggregate hits by action type
query = """
        SELECT
            CASE WHEN hits.eCommerceAction.action_type = '1' THEN 'Click through of product lists'
                 WHEN hits.eCommerceAction.action_type = '2' THEN 'Product detail views'
                 WHEN hits.eCommerceAction.action_type = '5' THEN 'Check out'
                 WHEN hits.eCommerceAction.action_type = '6' THEN 'Completed purchase'
            END AS action,
            COUNT(fullVisitorID) AS users,
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            (
            hits.eCommerceAction.action_type != '0'
            AND
            hits.eCommerceAction.action_type != '3'
            AND
            hits.eCommerceAction.action_type != '4'
            )
        GROUP BY
            action
        ORDER BY
            users DESC
        """

result = client.query(query).result().to_dataframe()
result.head(10)

# Create funnel graph
funnel_graph = go.Figure(go.Funnel(y = result['action'],
                          x = result['users'],
                          textposition = 'inside',
                          textinfo = 'value+percent initial'),
                layout=go.Layout(height=400, width=800)
               )
funnel_graph.update_layout(title_text = 'Google Merchandise Store Conversion Path')

funnel_graph.show()

query = """
        SELECT
            product.v2ProductCategory AS category,
            SUM(totals.transactions) AS transactions,
            SUM(totals.totalTransactionRevenue)/1000000 AS total_revenue
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        GROUP BY
            category
        ORDER BY
            total_revenue DESC
        LIMIT 10
        """

cat_result = client.query(query).result().to_dataframe()
cat_result.head(10)

query = """
        WITH daily_mens_tshirt_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Apparel/Men's/Men's-T-Shirts/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_mens_tshirt_transactions
        """

result = client.query(query).result().to_dataframe()
result['date'] = pd.to_datetime(result['date'])
result.plot(y='avg_transactions', x='date', kind='line',
            title='Men\'s T-Shirts Conversions 7-Day Moving Average', figsize=(12,6))
plt.show()

query = """
        WITH daily_drinkware_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Drinkware/Water Bottles and Tumblers/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_drinkware_transactions
        """

result = client.query(query).result().to_dataframe()
result['date'] = pd.to_datetime(result['date'])
result.plot(y='avg_transactions', x='date', kind='line',
            title='Drinkware Conversions 7-Day Moving Average', figsize=(12,6))
plt.show()

query = """
        WITH daily_electronics_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Electronics/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_electronics_transactions
        """

result = client.query(query).result().to_dataframe()
result['date'] = pd.to_datetime(result['date'])
result.plot(y='avg_transactions', x='date', kind='line',
            title='Electronics Conversions 7-Day Moving Average', figsize=(12,6))
plt.show()

query = """
        WITH daily_office_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Office/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_office_transactions
        """

result = client.query(query).result().to_dataframe()
result['date'] = pd.to_datetime(result['date'])
result.plot(y='avg_transactions', x='date', kind='line',
            title='Office Conversions 7-Day Moving Average', figsize=(12,6))
plt.show()

"""The average transactions for August 2016 are very high compared to later periods, but since we don't know the cause of this we will ignore it for now.

Office and Electronics products seem to have steady demand year-round, Drinkware seems to see a spike in demand in December and March, and demand for Men's T-Shirts seem to increase in September, March, and August.

# 4. Visualize Insights and Interpret Results

## Most Popular Landing Pages and Bounce Rates
The following are the most visited landing pages and their respective bounce rates:
"""

query = """
        SELECT
            hits.page.pagePath AS landing_page,
            COUNT(*) AS views,
            SUM(totals.bounces)/COUNT(*) AS bounce_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            hits.type='PAGE'
        AND
            hits.hitNumber=1
        GROUP BY
            landing_page
        ORDER BY
            views DESC
        LIMIT 10
        """

result = client.query(query).result().to_dataframe().sort_values(by='bounce_rate', axis=0)
fig, ax = plt.subplots(figsize=(10,6))
result.plot(y=['bounce_rate'], x='landing_page', kind='barh', legend=False,
            title='Bounce Rates for Top 10 Landing Pages', ax=ax)
ax.set_ylabel('')

plt.show()

query = """
        SELECT
            device.Browser AS browser,
            COUNT(*) AS sessions,
            SUM(totals.bounces)/COUNT(*) AS exit_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        GROUP BY
            browser
        ORDER BY
            sessions DESC
        LIMIT 7
        """

result = client.query(query).result().to_dataframe()
fig, ax = plt.subplots(figsize=(12,7))
result.plot(y=['sessions', 'exit_rate'], x='browser', kind='bar', secondary_y='exit_rate',
            ax=ax, mark_right=False, title='Sessions and Exit Rates by Browser')

ax.set_xticklabels(labels=result['browser'], rotation=45)
ax.set_xlabel('')
ax.legend(loc=(1.1, 0.55))
plt.legend(loc=(1.1, 0.5))

plt.show()

query = """
        SELECT
            device.deviceCategory AS device,
            COUNT(*) AS sessions,
            SUM(totals.bounces)/COUNT(*) AS exit_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        GROUP BY
            device
        ORDER BY
            sessions DESC
        """

result = client.query(query).result().to_dataframe()
fig, ax = plt.subplots(figsize=(10,6))
result.plot(y=['sessions','exit_rate'], x='device', kind='bar',
            title='Exit Rate by Device', secondary_y='exit_rate', ax=ax)
ax.set_xlabel('')
ax.set_xticklabels(labels=result['device'], rotation=45)
plt.show()

query = """
        SELECT
            trafficSource.medium AS medium,
            COUNT(*) AS sessions,
            SUM(totals.bounces)/COUNT(*) AS exit_rate,
            SUM(totals.transactions) AS transactions,
            SUM(totals.totalTransactionRevenue)/1000000 AS total_revenue,
            SUM(totals.transactions)/COUNT(*) AS conversion_rate
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        GROUP BY
            medium
        ORDER BY
            sessions DESC
        LIMIT 10
        """

result = client.query(query).result().to_dataframe()
fig, ax = plt.subplots(figsize=(10,7))
result.plot(y=['total_revenue', 'conversion_rate'], x='medium', kind='bar',
            secondary_y='conversion_rate', ax=ax)
ax.set_xticklabels(labels=result['medium'], rotation=45)
plt.show()

funnel_graph.show()

fig, ax = plt.subplots(figsize=(10,6))
cat_result.sort_values(by='total_revenue', axis=0).plot(y='total_revenue', x='category',
                                                        kind='barh', title='Revenue by Category', ax=ax)
ax.set_ylabel('')
plt.show()

fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(20,14))

# Men's T-shirts
query1 = """
        WITH daily_mens_tshirt_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Apparel/Men's/Men's-T-Shirts/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_mens_tshirt_transactions
        """

result1 = client.query(query1).result().to_dataframe()
result1['date'] = pd.to_datetime(result1['date'])
ax1 = result1.plot(y='avg_transactions', x='date', kind='line',
                   title='Men\'s T-Shirts Conversions 7-Day Moving Average', ax=axes[0,0])

# Drinkware
query2 = """
        WITH daily_drinkware_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Drinkware/Water Bottles and Tumblers/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_drinkware_transactions
        """

result2 = client.query(query2).result().to_dataframe()
result2['date'] = pd.to_datetime(result2['date'])
result2.plot(y='avg_transactions', x='date', kind='line',
             title='Drinkware Conversions 7-Day Moving Average', ax=axes[0,1])

# Office Supplies
query3 = """
        WITH daily_office_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Office/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_office_transactions
        """

result3 = client.query(query3).result().to_dataframe()
result3['date'] = pd.to_datetime(result3['date'])
result3.plot(y='avg_transactions', x='date', kind='line',
             title='Office Conversions 7-Day Moving Average', ax=axes[1,0])

# Electronics
query4 = """
        WITH daily_electronics_transactions AS
        (
        SELECT
            date,
            SUM(totals.transactions) AS transactions
        FROM
            `bigquery-public-data.google_analytics_sample.ga_sessions_*`,
            UNNEST(hits) AS hits,
            UNNEST(hits.product) AS product
        WHERE
            _TABLE_SUFFIX BETWEEN '20160801' AND '20170801'
        AND
            product.v2ProductCategory = "Home/Electronics/"
        GROUP BY
            date
        ORDER BY
            date
        )

        SELECT
            date,
            AVG(transactions)
            OVER (
                  ORDER BY date
                  ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
                 ) AS avg_transactions
        FROM
            daily_electronics_transactions
        """

result4 = client.query(query4).result().to_dataframe()
result4['date'] = pd.to_datetime(result4['date'])
result4.plot(y='avg_transactions', x='date', kind='line',
             title='Electronics Conversions 7-Day Moving Average', ax=axes[1,1])
plt.show()